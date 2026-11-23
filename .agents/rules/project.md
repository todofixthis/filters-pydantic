## Architecture

A thin integration layer between [pydantic](https://docs.pydantic.dev/) and phx-filters, in `src/filters_pydantic/`, working in both directions:

- `FilterField` runs a filter chain as a pydantic field's validation. pydantic can't read a field's type from a filter chain, so `FilterField` is attached as `typing.Annotated` metadata beside an ordinary type hint: the hint tells pydantic and type checkers what to expect, and the chain does the validating (ADR 001).
- `PydanticModel` runs a pydantic model as a filter in a chain, registered as a `filters.extensions` entry point so it is also `filters.ext.PydanticModel` (ADR 006). `FilterField` is not a filter, so it stays a plain import.

The `phx-filters` skill covers the non-obvious parts of wiring the two together.

Every module declares `__all__` and imports explicitly, never with a wildcard. To add a public symbol:

- export it from `src/filters_pydantic/__init__.py` and add it to `__all__`;
- if it subclasses `BaseFilter`, register it as a `filters.extensions` entry point in `pyproject.toml`, named after the class, and assert that it resolves in `test/test_entry_points.py`;
- document it in `README.rst` and `docs/index.rst`, which hold this project's user docs. todofixthis/filters' docs don't cover this package.

In the template-owned `pyproject.toml`, this project's own content is the entry point, `[project]`'s dependencies, keywords and classifiers, and the RUF012 ignore. Edit them here and keep them through a template-update conflict.

A forward-reference annotation uses `typing.Optional` or `typing.Union`, never `X | None`: `"ClassName" | None` raises `TypeError` at runtime (`str.__or__`), which Sphinx can't recover from. Put `# Use Optional for Sphinx compat` on the line before the annotation; for a return type, on the line before `) ->`, splitting a one-line signature to make one.

## Tests

One module per public symbol, `test/test_<symbol>.py`, each with a module docstring and functions named `test_<symbol>_<scenario>`; `test/test_entry_points.py` checks the entry points. Build chains with `import filters as f`, and import this package's symbols from `filters_pydantic` directly.

The existing tests' multi-line docstrings predate `.agents/rules/testing.md`'s one-line rule; write new ones to it.

## Package

The PyPI name is `phx-filters-pydantic`; the import name is `filters_pydantic`.
