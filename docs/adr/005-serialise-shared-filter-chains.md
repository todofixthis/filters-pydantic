---
status: Accepted
date: 2026-08-30
scope: [src/filters_pydantic/_filter_field.py, README.rst, docs/index.rst]
summary: FilterField serialises access to a shared, pre-built filter-chain instance with a per-field lock — safe only where no filter instance in the chain is used outside that field, including through `|` or nesting in another filter — rather than requiring callers to pass a factory, which is safe only where it builds every filter on each call.
revisit-when: Profiling shows the lock is a real throughput bottleneck under concurrent load; free-threaded Python (3.13t/3.14t, already admitted by this project's `requires-python`) changes the interleaving this fix relies on; phx-filters copies filters when chains combine or nest, which retires the README's composition warning but not the lock; phx-filters keeps per-run state (`parent`, `key`, `handler`, `_has_errors`) off filter instances, in `apply` and `FilterRunner` alike, which retires the lock; or a wrong validation result is traced to a filter instance shared outside one `FilterField`.
---

# 005: Serialise Shared Filter Chains

## Context

[`FilterField`][] stores whatever `filter_chain` it's constructed with and passes
it, unchanged, to a fresh [`FilterRunner`][] on every validation. When that
argument is a pre-built chain instance — `FilterField(f.Required | f.Unicode |
f.NotEmpty)`, the only form this project's docs and tests showed when this was
decided — every validation of that field, across every instance of the model,
shares the same [`BaseFilter`][] object.

`FilterRunner.full_clean` mutates that shared object to route errors (simplified;
phx-filters 4 moves this into `_full_clean`, with the same effect):

```python
def full_clean(self):
    if self._handler is None:
        self._handler = MemoryHandler(self.capture_exc_info)
        prev_handler = self.filter_chain.handler
        self.filter_chain.handler = self._handler
        try:
            self._cleaned_data = self.filter_chain.apply(self.data)
        finally:
            self.filter_chain.handler = prev_handler
```

`prev_handler` is read through `BaseFilter.handler`'s getter, which — for a chain
that has never had one set — returns a fresh `ExceptionHandler()` without storing
it. The `finally` block's assignment goes through the *setter* instead, which does
store it. So the very first validation of a shared chain permanently gives it a
real handler where it had none, and every validation after that restores that same
object rather than the "no handler" state the chain started in. A child filter's
own failure looks up its handler by walking `parent.handler` up to the chain,
resolving whatever `chain._handler` holds *at that moment* — not necessarily the
handler the failing call started with.

Reproduced directly, without threads, by manipulating the handler mid-flight:

```python
import filters as f
from filters.handlers import MemoryHandler

chain = f.Required | f.Unicode | f.NotEmpty
handlerA, handlerB = MemoryHandler(), MemoryHandler()

chain.handler = handlerA   # call A starts …
chain.handler = handlerB   # … call B clobbers it before A's apply() runs
chain.apply("")            # A's failure lands in handlerB, not handlerA
```

`handlerA.messages` comes back empty — the caller reading `handlerA` sees no error
at all. Concurrently validating the same field from multiple threads reproduces
the same corruption: enough threads split between valid and invalid input, run
against a chain with an artificially slow filter *ahead of* the check that fails,
reliably produce some wrong results — a valid input rejected because another
thread's failure landed in its handler, or an invalid input silently accepted
because its own failure landed in someone else's. (The slow filter has to run
before the failing one: [`FilterChain`][]`._apply` stops at the first filter that
records an error, so a slow filter placed after a failure never gets the chance to
widen the race window.) `BaseFilter._has_errors` is subject to the identical race,
being reset at the start of every `apply()` call on the same shared instance.
Nor does the damage end with the race: two overlapping runners restore in the
wrong order, leaving the chain holding the first runner's finished handler, so any
chain that later nests it accepts invalid input even on one thread. A per-field
lock stops one field's runners overlapping, but not a chain shared beyond the
field.

This isn't a contrived scenario: pydantic validation runs from request-handling
code, and frameworks built on it commonly run synchronous validation in a thread
pool under concurrent load — precisely where a field's chain gets `apply()`-ed on
the same shared instance from multiple threads at once.

phx-filters' own `FilterCompatible` type already includes `Callable[[], BaseFilter]`
— a zero-argument factory that `resolve_filter` invokes fresh on every call, which
sidesteps this where the factory builds every filter itself;
`FilterField(lambda: f.Required | f.Unicode | f.NotEmpty)` is unaffected by it.
But `resolve_filter`'s other branch — an already-built instance — is returned
as-is, which is what every usage passed when this was decided.

### A chain instance shared across fields is the same hazard, not a narrower one

The scenario above already covers two `FilterField`s built from the *same* chain
object — nothing distinguishes that from "every instance of the model", since a
`FilterField`'s own identity plays no part in the race; only the shared
`BaseFilter` object does. A per-field lock does not close this: two fields hold
two separate locks over one shared chain, so a validation on one field is
unserialised against a concurrent validation on the other.

The same hazard extends one level deeper. `BaseFilter._filter` — how a chain
applies each of its own children — calls `resolve_filter(child, parent=self, ...)`
on *every* `apply()`, not just once at construction, which reassigns `child.parent`
to whichever chain is currently applying it:

```python
BASE = f.Unicode | f.NotEmpty
chain_a = f.Required | BASE        # BASE.parent -> chain_a
chain_b = f.MaxLength(5) | BASE    # BASE.parent -> chain_b, clobbering the above
```

Run sequentially, this self-heals — `chain_a.apply()` reassigns `BASE.parent` back
to `chain_a` immediately before using it, so a single-threaded caller never
observes the clobber from `chain_b`'s construction. Concurrently, it doesn't:
`chain_a` and `chain_b` can each hold their own field's lock while both apply the
shared `BASE`, and the reassign-then-use step of one can interleave with the
other's, corrupting `BASE`'s parent for whichever thread reads it second.

`key`, which names the field an error is filed under, doesn't self-heal even
sequentially: `resolve_filter` sets it only when the parent passes one, as
`FilterMapper` and `FilterRepeater` do, and a plain chain never clears it. Merely
constructing a `FilterMapper` around a filter, before or after the chain that also
holds it, files that filter's errors under the mapper's key wherever else it runs,
with one thread and the lock held.

Extending a chain with `|` shares its filters without nesting it.
`FilterChain.__or__` returns a shallow copy: the new chain gets its own list, but
the list holds the original filter instances:

```python
Text = f.Unicode | f.Strip
title = Text | f.MaxLength(50)     # holds Text's own Unicode and Strip
body = Text | f.MaxLength(2000)    # holds the same two instances
```

`title` and `body` both reassign the shared filters' `parent` on every `apply()`,
though neither chain contains the other. A factory is no escape from this:
`lambda: Text | f.MaxLength(50)` builds a new chain on every call around filters
that every call shares, and `lambda: f.Required | Text` nests one.

A lock keyed to one `FilterField` is therefore safe only when no filter instance in
that field's chain is also reachable from another field, caller or filter,
whether directly, nested in another filter (a chain, `FilterMapper` or
`FilterRepeater`), or through a chain combined with it by `|`. No test in this
project shares a filter instance across more than one `FilterField`; the README and
the docs index show one only as an example of the unsafe pattern.

## Options

### Option 1: Do nothing — document the risk

Note in the docstring and README that a chain built inline is unsafe under
concurrent validation, and recommend the factory form for anyone who needs it.

**Pros:** No code or behavioural change — nothing to test or maintain beyond a
paragraph of documentation.
**Cons:** Leaves the default construction pattern, the only one documented when
this was decided (`FilterField(f.Required | ...)`), silently unsafe; a caller has
to already know about this specific hazard, in a library whose main audience is
concurrent request-handling code, to avoid it.
**Risks:** Silent data corruption under load is the worst class of bug to leave
behind a documentation footnote — it passes every test that doesn't specifically
provoke concurrency, and surfaces in production under exactly the load pattern
users deploy this library for.

### Option 2: Serialise access to a shared instance with a per-field lock (Accepted)

Keep accepting a pre-built instance unchanged, but hold an `RLock` around chain
resolution and application whenever `filter_chain` is a `BaseFilter` instance
(skipped entirely for a factory or class, which gets a new top-level chain per
call, independent wherever the factory builds every filter itself).

**Pros:** Every current construction pattern keeps working unchanged — no caller
needs to touch their code to become safe.
**Cons:** Under concurrent load, every validation of that field now waits for any
other in-flight validation of the same field to finish — a bottleneck that scales
with how expensive the chain is, worst for exactly the slow-filter case that
exposes the underlying race most easily. Doesn't close the shared-chain-across-fields
hazard described in Context.
**Risks:** A filter that recurses back into validating the same field on the same
thread would deadlock on a plain `Lock`; using `RLock` avoids that class of bug
even though no current filter does this. Two fields whose chains validate into
each other (e.g. nested models, one holding the other via `PydanticModel`) could
still deadlock across threads on lock-ordering, the same as any two-mutex
program — no current filter in this project does that either, but the risk is
inherent to locking, not specific to this implementation.

Keying the lock to the chain object itself (a `WeakKeyDictionary`) rather than to
the `FilterField` would close the shared-chain-across-fields case too, at similar
implementation cost. Rejected in favour of the simpler per-field lock: it still
wouldn't close the nested-sub-chain or `|`-extended cases (a lock on `chain_a` and
one on `chain_b` still don't serialise against each other over the filters they
share), so the residual gap doesn't shrink enough to justify a shared,
weakref-keyed registry. One process-wide lock would close every route through
`FilterField`, though not code running the chain outside it, and the cross-field
deadlock named under Risks, but would serialise every `FilterField` validation in
the process against every other.

### Option 3: Require a factory, reject a pre-built instance

Accept only a zero-argument callable or filter class in `__init__`, raising
`TypeError` for an already-built `BaseFilter` instance.

**Pros:** Makes the unsafe pattern impossible rather than merely discouraged;
resolves the chain fresh every time via phx-filters' own existing mechanism, with
no new code in this package, and closes the shared-chain-across-fields hazard too
— a chain the factory builds whole is never shared with anything. It can't stop a
factory from embedding a shared filter instance, so the `|`-extended case stays
open.
**Cons:** Breaking change to the only construction pattern this project had
documented — every existing example, in this repo and presumably in any adopter's
code, needs rewriting to wrap its chain in a `lambda`.
**Risks:** None to correctness; the cost is entirely migration effort landing on
every current caller for a defect most will never have hit.

### Option 4: Lock per field, and deep-copy a pre-built chain at construction

Option 2, plus `FilterField.__init__` taking a `copy.deepcopy` of a pre-built
chain, so the field owns every filter instance in it and its lock covers every
sharing route through `FilterField`.

**Pros:** Closes the residual gap at a one-off construction cost, with no change to
how callers declare fields.
**Cons:** Silently copies state a filter may mean to share, such as a connection or
a cache. Treats in this package a phx-filters defect that every phx-filters caller
sharing a filter instance across threads meets too.
**Risks:** `deepcopy` raises on a filter holding something it can't copy, such as a
lock or an open connection, and does so when the model class is defined, so a
model that imported cleanly before fails to import.

## Decision

Adopt Option 2. Every example this project documented when this was decided
constructed `FilterField` from a pre-built chain, and shipping 1.0 with that exact
pattern silently unsafe is a worse outcome than a bottleneck under load a caller
can opt out of. Locking closes
the hole for the code every current user has already written, with no migration;
Option 3's safety is real, and wider (it also closes the shared-chain-across-fields
gap), but only for callers who rewrite their field declarations, which is not the
population most exposed to this bug today. This weighs Option 3's migration cost
against a population that, pre-1.0, didn't yet exist — this project was then at
`0.1.0`, so "every adopter's code" was speculative, not a real breaking-change
bill. The choice stands anyway: a breaking change to the only construction pattern
this project had documented, on the strength of a bug class most callers will
never hit, isn't proportionate when the non-breaking option already covers that
same population. A caller who profiles their way to this lock as a bottleneck, or
who shares a filter instance across more than one field, already has the fix
available without a package change: pass a callable that builds every filter on
each call, which skips the lock and validates independently.

Option 4 is rejected because it silently copies state a filter may mean to share,
and can break a model's import. The residual gap's cause lies in phx-filters,
which keeps per-run state on filter instances, so it is fixed there instead
([todofixthis/filters#175][]), during the v4 pre-release cycle while a change to
`BaseFilter` can still ship. Until then, the README and the docs index warn about
the residual case.

## Consequences

- A `FilterField` built from a pre-built chain instance now serialises concurrent
  validation of that field across every instance of the model — safe by default,
  at the cost of throughput under concurrent load proportional to chain cost.
- A `FilterField` built from a callable or filter class is unaffected: no lock, no
  behaviour change, and safe wherever the callable builds every filter itself.
- The README names the callable form as the recommended pattern both for a chain
  with an expensive filter (I/O, a slow computation) under concurrent load, and
  for a filter instance shared outside one `FilterField` — the one pattern the lock
  doesn't cover. It says the callable must build every filter on each call, since
  one returning or extending an existing chain shares its filters just the same.
  It also says reusing one `Annotated` alias is safe, since its uses share one
  `FilterField` and so one lock, and that a filter a `FilterMapper` or
  `FilterRepeater` also holds reports its errors under the holder's key. Leaving
  the shared case to documentation carries the weakness Option 1 was rejected for,
  since `|` makes sharing easy to do without noticing. It is accepted only as an
  interim measure until todofixthis/filters#175 lands.
- This is the first and only synchronisation primitive in the package; nothing
  else here holds a lock.

[`BaseFilter`]: https://github.com/todofixthis/filters/blob/develop/src/filters/base.py
[`FilterChain`]: https://github.com/todofixthis/filters/blob/develop/src/filters/base.py
[`FilterField`]: ../../src/filters_pydantic/_filter_field.py
[`FilterRunner`]: https://github.com/todofixthis/filters/blob/develop/src/filters/handlers.py
[todofixthis/filters#175]: https://github.com/todofixthis/filters/issues/175
