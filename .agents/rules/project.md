## Architecture

A thin integration layer between [pydantic](https://docs.pydantic.dev/) and phx-filters, in `src/filters_pydantic/`, working in both directions:

- `FilterField` runs a filter chain as a pydantic field's validation. pydantic can't read a field's type from a filter chain, so `FilterField` is attached as `typing.Annotated` metadata beside an ordinary type hint: the hint tells pydantic and type checkers what to expect, and the chain does the validating (ADR 001).
- `PydanticModel` runs a pydantic model as a filter in a chain, registered as a `filters.extensions` entry point so it is also `filters.ext.PydanticModel` (ADR 006). `FilterField` is not a filter, so it stays a plain import.

The `phx-filters` skill covers the non-obvious parts of wiring the two together.

These are this project's own content in the template-owned `pyproject.toml`, so edit them here and keep them through a template-update conflict: the entry point, and `[project]`'s dependencies, keywords and classifiers; and the RUF012 ignore.

A forward-reference annotation uses `typing.Optional` or `typing.Union`, never `X | None`: `"ClassName" | None` raises `TypeError` at runtime (`str.__or__`), which Sphinx can't recover from. Put `# Use Optional for Sphinx compat` on the line above the annotation.

## Tests

One module per public symbol, `test/test_<symbol>.py`, with functions named `test_<symbol>_<scenario>`. Build chains with `import filters as f`, and import this package's symbols from `filters_pydantic` directly. `test/test_entry_points.py` checks that `PydanticModel`'s entry point resolves.

The existing tests' multi-line docstrings predate `.agents/rules/testing.md`; write new ones to its one-line rule.
