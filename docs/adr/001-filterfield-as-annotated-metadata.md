---
status: Accepted
date: 2026-08-29
tags: [pydantic, filters, core-schema, api-design]
summary: FilterField is attached via typing.Annotated metadata and implements __get_pydantic_core_schema__ as a before-validator, translating filters errors into a single ValueError per field.
---

# 001: FilterField as Annotated Metadata

## Context

`phx-filters` chains (e.g. `f.Required | f.Unicode | f.NotEmpty`) carry no generic
typing — a chain's declared input and output types aren't expressible in Python's
type system, so pydantic can't infer a field's type from a chain alone. This
project needs a way to run a filter chain as a pydantic field's validation logic
while still giving pydantic (and static type checkers) an accurate type for that
field.

pydantic v2 exposes several extension points for custom validation logic:
`Annotated` metadata implementing `__get_pydantic_core_schema__`, a `FieldInfo`
subclass assigned as the field's default, and per-field validators registered via
`@field_validator`. Whichever one is chosen becomes the template every future
filter-chain integration in this package follows, so it needs deciding up front.

## Options

### Option 1: `FieldInfo` subclass assigned as the field default

```python
name: str = FilterField(f.Required | f.Unicode | f.NotEmpty)
```

Subclass `pydantic.fields.FieldInfo` and assign an instance as the class
attribute's default, the same way `pydantic.Field(...)` is used.

**Pros:** Reads like ordinary `Field(...)` usage; the type hint stays a plain
`str`.
**Cons:** `FieldInfo`'s constructor and internal attributes are pydantic-version
-sensitive and not part of its stable public API for subclassing; there's no
documented hook on `FieldInfo` for attaching a validator function, so the filter
chain would have to be wired in via a separate `@field_validator` the metaclass
installs — extra indirection for no real benefit over Option 2.
**Risks:** Breaks silently on a pydantic minor version bump if internal
`FieldInfo` attributes change.

### Option 2: `Annotated` metadata via `__get_pydantic_core_schema__` (Accepted)

```python
name: Annotated[str, FilterField(f.Required | f.Unicode | f.NotEmpty)]
```

Implement `__get_pydantic_core_schema__` on `FilterField` — pydantic's documented
mechanism for custom `Annotated` validators (the same one `BeforeValidator`,
`AfterValidator`, etc. use internally).

**Pros:** Officially documented, version-stable extension point; composes with
other `Annotated` metadata (`Field(...)`, `BeforeValidator`, etc.) in the same
annotation; the plain type hint (`str`) is exactly the type-checker-visible
annotation, so this is the natural answer to "filters has no typing — supply the
type yourself."
**Cons:** Slightly more verbose at the call site than a bare `Field(...)`
assignment.
**Risks:** None significant — this is pydantic's recommended pattern for exactly
this use case.

### Option 3: Decorator that installs `@field_validator`s

```python
@filter_fields(name=f.Required | f.Unicode | f.NotEmpty)
class Person(BaseModel):
    name: str
```

A class decorator that inspects a mapping of field names to chains and installs
a `field_validator` for each.

**Pros:** Keeps the type hint completely bare.
**Cons:** Splits a field's type and its validation chain across two places in
the class body, which is exactly the coupling `Annotated` exists to avoid;
duplicates field names as decorator keyword arguments, which the linter and the
type checker can't cross-check against the class body.
**Risks:** Field renamed in one place but not the other silently stops applying
the filter chain — decorator keys aren't statically checked.

## Decision

Adopt Option 2. `FilterField.__get_pydantic_core_schema__` returns
`core_schema.no_info_before_validator_function`, so the filter chain runs first
and produces a value that pydantic's own schema for the annotated type then
validates or coerces — the annotated type acts as a safety net and drives
JSON-schema generation, while the filter chain does the real work.

On failure, `FilterField` collects every message from
`FilterRunner.get_errors()` (chains can report more than one error, e.g. via a
nested `FilterMapper`), prefixes each with its filters sub-key when one is
present, and raises a single `ValueError` with all of them joined —
pydantic then reports it as one `value_error` entry located at that field,
consistent with how it already reports any other single-exception validator
failure. Filters' individual error codes aren't currently surfaced
structurally in the `ValidationError`; revisit this (e.g. via
`PydanticCustomError` context) if a consumer needs to branch on them
programmatically.

## Consequences

- Every field using `FilterField` needs an explicit, accurate type
  annotation — `FilterField` does not infer one from the chain.
- `FilterField` composes with other `Annotated` metadata (`Field(...)`,
  further `BeforeValidator`s, etc.) in the same annotation.
- A filter chain that produces a value incompatible with the declared
  annotation fails at the pydantic-coercion step, not inside the chain
  itself — the resulting error message names the annotation's type, not the
  filter chain, which may be confusing until this is documented.
- Multiple filter errors on one field collapse into a single joined message;
  downstream code that needs individual error codes must inspect
  `FilterRunner` directly rather than the model's `ValidationError`.
