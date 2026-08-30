---
status: Accepted
date: 2026-08-30
scope: [src/filters_pydantic/_filter_field.py, README.rst, docs/index.rst]
summary: FilterField serialises access to a shared, pre-built filter-chain instance with a per-field lock — safe only where the chain is exclusively owned by that field — rather than requiring callers to pass a factory for concurrent safety.
revisit-when: Profiling shows the lock is a real throughput bottleneck under concurrent load, or free-threaded Python (3.13t/3.14t, already admitted by this project's `requires-python`) changes the interleaving this fix relies on.
---

# 005: Serialise Shared Filter Chains

## Context

[`FilterField`][] stores whatever `filter_chain` it's constructed with and passes
it, unchanged, to a fresh [`FilterRunner`][] on every validation. When that
argument is a pre-built chain instance — `FilterField(f.Required | f.Unicode |
f.NotEmpty)`, the only form shown anywhere in this project's own docs and tests —
every validation of that field, across every instance of the model, shares the
same [`BaseFilter`][] object.

`FilterRunner.full_clean` mutates that shared object to route errors:

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

This isn't a contrived scenario: pydantic validation runs from request-handling
code, and frameworks built on it commonly run synchronous validation in a thread
pool under concurrent load — precisely where a field's chain gets `apply()`-ed on
the same shared instance from multiple threads at once.

phx-filters' own `FilterCompatible` type already includes `Callable[[], BaseFilter]`
— a zero-argument factory that `resolve_filter` invokes fresh on every call, which
already sidesteps this entirely; `FilterField(lambda: f.Required | f.Unicode |
f.NotEmpty)` is unaffected by it. But `resolve_filter`'s other branch — an
already-built instance — is returned as-is, which is what every current usage
passes.

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

A lock keyed to one `FilterField` is therefore safe only when that field's chain,
and everything nested in it, is not also reachable from any other field or
concurrent caller. No test or doc in this project shares a chain, or a sub-chain,
across more than one `FilterField`.

## Options

### Option 1: Do nothing — document the risk

Note in the docstring and README that a chain built inline is unsafe under
concurrent validation, and recommend the factory form for anyone who needs it.

**Pros:** No code or behavioural change — nothing to test or maintain beyond a
paragraph of documentation.
**Cons:** Leaves the default, only-documented construction pattern
(`FilterField(f.Required | ...)`) silently unsafe; a caller has to already know
about this specific hazard, in a library whose main audience is concurrent
request-handling code, to avoid it.
**Risks:** Silent data corruption under load is the worst class of bug to leave
behind a documentation footnote — it passes every test that doesn't specifically
provoke concurrency, and surfaces in production under exactly the load pattern
users deploy this library for.

### Option 2: Serialise access to a shared instance with a per-field lock (Accepted)

Keep accepting a pre-built instance unchanged, but hold an `RLock` around chain
resolution and application whenever `filter_chain` is a `BaseFilter` instance
(skipped entirely for a factory or class, which already gets an independent chain
per call and needs no serialising).

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
wouldn't close the nested-sub-chain case (a lock on `chain_a` and one on `chain_b`
still don't serialise against each other over the `BASE` they share), so the
residual gap doesn't shrink enough to justify a shared, weakref-keyed registry.

### Option 3: Require a factory, reject a pre-built instance

Accept only a zero-argument callable or filter class in `__init__`, raising
`TypeError` for an already-built `BaseFilter` instance.

**Pros:** Makes the unsafe pattern impossible rather than merely discouraged;
resolves the chain fresh every time via phx-filters' own existing mechanism, with
no new code in this package, and closes the shared-chain-across-fields hazard too
— a fresh instance is never shared with anything.
**Cons:** Breaking change to the only construction pattern this project has ever
documented — every existing example, in this repo and presumably in any adopter's
code, needs rewriting to wrap its chain in a `lambda`.
**Risks:** None to correctness; the cost is entirely migration effort landing on
every current caller for a defect most will never have hit.

## Decision

Adopt Option 2. Every example this project documents constructs `FilterField` from
a pre-built chain, and shipping 1.0 with that exact pattern silently unsafe is a
worse outcome than a bottleneck under load a caller can opt out of. Locking closes
the hole for the code every current user has already written, with no migration;
Option 3's safety is real, and wider (it also closes the shared-chain-across-fields
gap), but only for callers who rewrite their field declarations, which is not the
population most exposed to this bug today. This weighs Option 3's migration cost
against a population that, pre-1.0, doesn't yet exist — this project is still at
`0.1.0`, so "every adopter's code" is speculative, not a real breaking-change bill
being sent today. The choice stands anyway: a breaking change to the only
construction pattern this project has ever documented, on the strength of a bug
class most callers will never hit, isn't proportionate when the non-breaking
option already covers that same population. A caller who profiles their way to
this lock as a bottleneck, or who deliberately shares a chain across more than one
field, already has the fix available without a package change: pass a callable
instead, which skips the lock entirely and validates independently on every call.

## Consequences

- A `FilterField` built from a pre-built chain instance now serialises concurrent
  validation of that field across every instance of the model — safe by default,
  at the cost of throughput under concurrent load proportional to chain cost.
- A `FilterField` built from a callable or filter class is unaffected: no lock, no
  behaviour change, already safe because each call resolves an independent chain.
- The docstring and README now name the callable form as the recommended pattern
  both for a chain with an expensive filter (I/O, a slow computation) under
  concurrent load, and for a chain or sub-chain deliberately shared across more
  than one `FilterField` — the one pattern the lock doesn't cover. Leaving that
  case to documentation isn't the same tradeoff Option 1 was rejected for: Option 1
  would have left the only pattern this project documents unsafe by default; this
  leaves a pattern nothing here uses unsafe, opt-in only to a caller who already
  chose to share a chain instance across fields.
- This is the first and only synchronisation primitive in the package; nothing
  else here holds a lock.

[`BaseFilter`]: https://github.com/todofixthis/filters/blob/develop/src/filters/base.py
[`FilterChain`]: https://github.com/todofixthis/filters/blob/develop/src/filters/base.py
[`FilterField`]: ../../src/filters_pydantic/_filter_field.py
[`FilterRunner`]: https://github.com/todofixthis/filters/blob/develop/src/filters/handlers.py
