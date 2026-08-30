---
name: phx-filters
description: Use when writing or debugging phx-filters integrations in this project — FilterField running a chain inside a pydantic field, or PydanticModel running a model inside a chain — covers Annotated placement, validator ordering, and error-message shape in both directions.
---

# Working with phx-filters

This skill covers only what's non-obvious about wiring `phx-filters` chains
into pydantic models in this project. For chain composition itself (`|`,
`FilterMapper`, `FilterRepeater`, ordering conventions), read the installed
package's source (`.venv/lib/*/site-packages/filters/` — it ships no
prose docs) or its `writing_filters`/`complex_filters` guides at
<https://filters.readthedocs.io/>.

## Attaching a chain to a field

`FilterField` is `Annotated` metadata, not a `Field()` replacement — give the
field its real type, and add the chain alongside it:

```python
name: Annotated[str, FilterField(f.Required | f.Unicode | f.NotEmpty)]
```

It composes with other `Annotated` metadata in the same slot, e.g.
`pydantic.Field()`:

```python
retries: Annotated[int, FilterField(f.Int | f.Min(0)), Field(ge=0)] = 3
```

## Validator ordering

The chain runs as a pydantic **before**-validator: it sees the raw incoming
value first, and its output is then validated/coerced against the field's
annotated type. Two consequences:

- A value the annotated type itself can't accept — even after the chain
  transforms it — fails with a plain pydantic error (`int_parsing`, etc.),
  not a `value_error` from the chain. Get the annotation right; `FilterField`
  doesn't infer one.
- Constructing a model directly (`Person(age="7")`) is typed against the
  annotation, so a value the chain is meant to coerce (a `str` for an `int`
  field) fails mypy even though it's valid at runtime — this is exactly the
  scenario `FilterField` exists for. Use `Model.model_validate({...})` in
  tests exercising that coercion; it's typed as `Any`/`dict` input, matching
  how data actually arrives from outside (JSON, form data).

## Error messages

On failure, `FilterField` raises one `ValueError` joining every message from
`FilterRunner.get_errors()` with `; `, prefixing each with its filters
sub-key when non-empty (e.g. a `FilterMapper` chain on a dict field produces
`"x: This value is required.; y: This value is required."`). Filter error
*codes* aren't surfaced in the `ValidationError` — only the rendered
messages. If a caller needs to branch on codes, they need `FilterRunner`
directly, not the model.

## Validating via a pydantic model with `PydanticModel`

```python
f.Required | PydanticModel(Person)
```

Each `pydantic.ValidationError` entry becomes its own phx-filters error,
keyed by that entry's dot-joined `loc` path — so nesting `PydanticModel`
inside a `FilterMapper` produces correctly-scoped keys (e.g.
`address.postcode`), matching how `FilterMapper` already reports its own
multi-key failures. Every error surfaces as `PydanticModel.CODE_INVALID`;
pydantic's finer-grained error types (`missing`, `int_parsing`, etc.)
aren't preserved as distinct phx-filters codes. See
`docs/adr/002-pydanticmodel-error-translation.md` for why this filter
reports per-key rather than joining messages the way `FilterField` does.

A whole-model error (e.g. from `model_validator(mode="after")`) has an
empty `loc`, so it lands at `PydanticModel`'s own key rather than a
sub-key — same as any other non-nested filter's own failures.
