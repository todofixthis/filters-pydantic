---
status: Accepted
date: 2026-08-29
scope: [src/filters_pydantic/_pydantic_model.py]
summary: PydanticModel reports each pydantic error individually, keyed by its dot-joined loc path, rather than joining them into one message.
---

# 002: PydanticModel Error Translation

## Context

[001][] gave `filters_pydantic` a way to run a phx-filters chain as a
pydantic field's validator. The reverse direction is also useful: running a
pydantic model's validation as a step inside a phx-filters chain, e.g.
nested inside a [`FilterMapper`][] or [`FilterRepeater`][], so a sub-document
can be validated against a full model instead of field-by-field filters.

`pydantic.ValidationError.errors()` returns a list of per-field error
dicts, each carrying a `loc` tuple locating the failing field (nested for
sub-models) and a rendered `msg`. phx-filters' own [`BaseFilter._invalid_value`][]
takes a `sub_key` argument for exactly this — reporting one error per
offending key, which `FilterMapper` already does for its own multi-key
failures. Something has to decide how pydantic's list of errors becomes
phx-filters' key-scoped error reporting.

## Options

### Option 1: Do nothing

Ship `PydanticModel` without translating individual errors — surface only
the caught exception's `str()`, or require callers to catch
`pydantic.ValidationError` themselves outside the filter chain.

**Pros:** No translation code to write or maintain.
**Cons:** Breaks filter chain composition — a `PydanticModel` nested in a
`FilterMapper` couldn't report failures the way every other nested filter
does, and `str(ValidationError)` is a multi-line human-readable block, not
a phx-filters error entry.
**Risks:** Callers reach for `try`/`except` around the whole chain instead
of `FilterRunner.get_errors()`, defeating the point of using a filter here.

### Option 2: One `_invalid_value` call per pydantic error, keyed by `loc` (Accepted)

Catch `pydantic.ValidationError`, iterate `.errors()`, and call
`self._invalid_value(..., sub_key=".".join(str(p) for p in error["loc"]))`
once per entry, each with its own rendered message.

**Cons:** A `loc` entry can be a list index (an `int`), which reads oddly
dot-joined into a string key (e.g. `tags.0`) — but `FilterMapper` already
produces the same shape for its own keys, so this isn't a new inconsistency.
**Risks:** None significant — `_invalid_value`'s `sub_key` and the
filter's key chain already handle nesting.

### Option 3: Join every pydantic error into one message, single `_invalid_value` call

Catch `pydantic.ValidationError` and raise one combined message (mirroring
how [`FilterField`][] joins every phx-filters message into a single
pydantic `ValueError`).

**Cons:** Collapses each error's field location into prose instead of a
structured key, so a `PydanticModel` nested in a `FilterMapper` reports one
opaque blob at the parent key instead of scoped entries at the actual
failing fields — inconsistent with how `FilterMapper` and `FilterRepeater`
already report their own multi-key failures.
**Risks:** A caller inspecting `FilterRunner.get_errors()` for a specific
field would need to parse the joined string instead of reading a key.

## Decision

Adopt Option 2. Reporting one `_invalid_value` call per pydantic error,
keyed by its `loc` path, keeps `PydanticModel`'s failures structurally
consistent with every other multi-key filter in this codebase and in
phx-filters itself, and composes correctly when nested inside a
`FilterMapper` or `FilterRepeater` — each failing field lands at its own
key rather than folded into one message.

This is the opposite tradeoff from 001's `FilterField`, which joins
phx-filters' errors into a single pydantic `ValueError` because pydantic
has no per-field slot to scope a nested filter chain's own multi-key
failures into — the two ADRs choose translations suited to their target
error models, not one style applied in both directions.

## Consequences

- `PydanticModel`'s errors are accessible via `FilterRunner.get_errors()`
  scoped by field path, matching `FilterMapper`'s error shape rather than
  `FilterField`'s single joined message.
- A `loc` path through a list produces a dotted numeric segment (e.g.
  `tags.0`), consistent with how `FilterMapper`/`FilterRepeater` key their
  own list and dict entries.
- Every pydantic error code and message reaches phx-filters as
  `PydanticModel.CODE_INVALID` with the field's own rendered message —
  pydantic's finer-grained error types (`missing`, `int_parsing`, etc.)
  aren't preserved as distinct phx-filters codes.
- A model-level error (e.g. from `model_validator(mode="after")`, or the
  input not being a mapping at all) has an empty `loc` tuple, which joins
  to `""`. `BaseFilter._make_key` drops empty key parts, so this lands at
  `PydanticModel`'s own key rather than a sub-key — the same place a
  non-nested filter already reports its own failures — and multiple such
  errors still accumulate correctly under that one key.

[001]: 001-filterfield-as-annotated-metadata.md
[`BaseFilter._invalid_value`]: https://github.com/todofixthis/filters/blob/develop/src/filters/base.py
[`FilterField`]: ../../src/filters_pydantic/_filter_field.py
[`FilterMapper`]: https://github.com/todofixthis/filters/blob/develop/src/filters/complex.py
[`FilterRepeater`]: https://github.com/todofixthis/filters/blob/develop/src/filters/complex.py
