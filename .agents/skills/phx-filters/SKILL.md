---
name: phx-filters
description: Use when writing or debugging phx-filters chains attached to pydantic models via FilterField in this project — covers Annotated placement, validator ordering, and error-message shape.
---

# Working with phx-filters via FilterField

This skill covers only what's non-obvious about wiring `phx-filters` chains
into pydantic models in this project. For chain composition itself (`|`,
`FilterMapper`, `FilterRepeater`, ordering conventions), read `filters`'
own source, or its `writing_filters`/`complex_filters` docs if the package is
installed in the venv (`.venv/lib/*/site-packages/filters/`).

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
