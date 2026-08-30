---
status: Accepted
date: 2026-08-30
scope: [pyproject.toml, README.rst, docs/index.rst, test/test_entry_points.py]
summary: Register PydanticModel, not FilterField, as a filters.extensions entry point, making it reachable as f.ext.PydanticModel; FilterField stays a plain import.
revisit-when: FilterField becomes a BaseFilter subclass, or filters.extensions' is_filter_type check changes upstream to admit non-BaseFilter classes.
---

# 006: Register PydanticModel as a filters.extensions Entry Point

## Context

[`filters`][] discovers third-party filters through a `filters.extensions`
entry-point group, exposing each one on its `f.ext` namespace ([`extensions.py`][]).
`phx-filters-django` and `phx-filters-iso` both register this way, so a `filters`
docs PR ([todofixthis/filters#114][]) originally documented this package under a
new "Integrations" section instead, since neither of this package's two public
symbols had been registered into `f.ext`. Reviewing that PR, the `filters`
maintainer asked to close the gap instead: register whichever part of this
package can be a real filter, so this package counts as an ordinary Extension
alongside Django/ISO Filters, and "Integrations" goes away as a separate
category.

This package exports two symbols. [`PydanticModel`][] already subclasses
`filters.base.BaseFilter` — `extensions.py`'s `is_filter_type` check, which
`FilterExtensionRegistry` runs against every entry point it loads, accepts it
unchanged. [`FilterField`][] is pydantic-side `Annotated` metadata implementing
`__get_pydantic_core_schema__`; it is not a `BaseFilter` and cannot chain with
`|` the way `f.ext` entries are meant to.

## Options

### Option 1: Do nothing — keep both symbols as plain imports

**Pros:** No change; `docs/index.rst` keeps describing both symbols under a
single "Validating a Model Inside a Filter Chain" section without splitting
usage by registration status.
**Cons:** Leaves the gap the `filters` maintainer asked to close;
`PydanticModel` stays undiscoverable via `f.ext` even though nothing about it
prevents that.
**Risks:** Blocks todofixthis/filters#114, which is waiting on this decision.

### Option 2: Register PydanticModel only (Accepted)

Add `PydanticModel = "filters_pydantic:PydanticModel"` under
`[project.entry-points."filters.extensions"]` in `pyproject.toml`. Leave
`FilterField` a plain import, documented as before.

**Pros:** Matches how Django/ISO Filters register today; needs no change to
`PydanticModel` itself, since it already satisfies `is_filter_type`.
**Cons:** The two symbols this package exports are now reached two different
ways — `f.ext.PydanticModel` versus `from filters_pydantic import
FilterField` — which the docs must call out rather than presenting one
uniform usage pattern.
**Risks:** None beyond the standard entry-point conflict risk `extensions.rst`
already documents: another package registering its own `PydanticModel` name
would non-deterministically shadow one or the other.

### Option 3: Wrap FilterField in a BaseFilter adapter so both symbols register

Give `FilterField` a companion `BaseFilter` subclass whose sole job is to
satisfy `is_filter_type`, so both symbols can sit under
`[project.entry-points."filters.extensions"]`.

**Pros:** Every public symbol reachable the same way.
**Cons:** `FilterField` isn't a validation step a chain runs — it's metadata
pydantic reads before any chain exists — so a `BaseFilter` wrapper would have
no `_apply` behaviour of its own and exist only to pass a registry check;
callers would have no reason to reach it via `f.ext` instead of importing it,
since it isn't used inside a chain the way `f.ext` entries are.
**Risks:** A wrapper with no real filtering behaviour would confuse readers of
`f.ext`'s contents into expecting it to work like the other entries there.

## Decision

Option 2. `PydanticModel` already satisfies `filters.extensions`' registration
contract with no code changes; `FilterField` fundamentally can't, since it
isn't a `BaseFilter` and Option 3's only way to force it there adds a fake
filter with no behaviour. Registering the one symbol that genuinely fits
closes the gap the `filters` maintainer raised without stretching the
extensions mechanism to cover a symbol it wasn't designed for — and it gives
`filters` users a direct benefit beyond satisfying that request: a chain
built entirely from `f.ext` entries can use `PydanticModel` without adding an
explicit import of this package.

## Consequences

- `README.rst` and `docs/index.rst` gain a mention of `f.ext.PydanticModel`
  alongside the existing `from filters_pydantic import PydanticModel` form.
- `FilterExtensionRegistry._get_cache` loads every registered entry point at
  once, so the first attribute access on `f.ext` — for any extension, not
  just this one — now eagerly imports `filters_pydantic`, and transitively
  `pydantic`, for every `filters` user who has this package installed,
  whether or not they use `PydanticModel`.
- `test/test_entry_points.py` asserts `PydanticModel` is discoverable via the
  `filters.extensions` entry-point group, so a `pyproject.toml` edit that
  drops or renames the entry point fails a test rather than surfacing only as
  a runtime gap in `f.ext`.
- Once this ships, todofixthis/filters#114 folds this package into `filters`'
  README/docs "Extensions" section (matching the Django/ISO Filters bullets)
  and drops the standalone "Integrations" section, since `PydanticModel` no
  longer needs a category of its own.

[`extensions.py`]: https://github.com/todofixthis/filters/blob/develop/src/filters/extensions.py
[`FilterField`]: ../../src/filters_pydantic/_filter_field.py
[`filters`]: https://github.com/todofixthis/filters
[`PydanticModel`]: ../../src/filters_pydantic/_pydantic_model.py
[todofixthis/filters#114]: https://github.com/todofixthis/filters/pull/114
