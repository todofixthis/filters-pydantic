> `CLAUDE.md` is a symlink to this file — edit `AGENTS.md` only.

## Getting Started

Before writing code, check:

- `docs/plans/` — current implementation plan
- `docs/adr/INDEX.md` — prior decisions (don't re-litigate)
- `docs/future/` — deferred features (don't re-discuss)

## Architecture Decision Records

When making significant decisions — choosing between libraries, patterns, tools, or conventions — you **must** write an ADR before implementing the decision. Use the `writing-adrs` skill for the format and conventions. ADRs live in `docs/adr/`. Before writing, run `ls docs/adr/` to find the highest existing number and increment it.

If you find yourself about to establish a new cross-cutting pattern (something that will affect multiple domains or files, e.g. a testing convention, a shared utility, an error-handling approach), stop and write an ADR first even if the immediate task feels local. A pattern adopted once becomes the template for everything that follows.

## Commands

```bash
uv run autohooks activate --mode=pythonpath            # install pre-commit hook (once per clone)
uv run git commit                                      # ALWAYS use this — never bare `git commit` (autohooks won't run without `uv run`)
uv add --bounds major <package>                        # add a runtime dependency at latest version
uv add --bounds major --group dev <package>            # add a dev dependency at latest version
uv sync --group=dev                                    # sync deps after pulling
uv run pytest                                          # run tests (current Python)
uv run tox -p                                          # run tests (all supported versions)
uv run pytest --collect-only                           # verify test count (note at start of mahi; confirm it increases when done)
uv run mypy src test                                   # type-check
uv run ruff check                                      # lint
uv run make -C docs clean && uv run make -C docs html  # build docs
```

## Architecture

Thin integration layer between [pydantic](https://docs.pydantic.dev/) and [phx-filters](https://github.com/todofixthis/filters). `phx-filters` chains have no generic typing, so `FilterField` is attached as `typing.Annotated` metadata alongside an ordinary type hint — the annotation tells pydantic (and static type checkers) what shape to expect; the filter chain does the actual validation. Source in `src/filters_pydantic/`.

- Explicit imports with `__all__` throughout — no wildcard imports
- Forward-reference type hints must use `typing.Optional`/`typing.Union` (not `X | None`) — `"ClassName" | None` raises a Python runtime `TypeError` (`str.__or__` unsupported) that Sphinx cannot recover from; this is not fixed in Sphinx 9 — add `# Use Optional for Sphinx compat` inline

## Tests

One file per public symbol in `test/`, named `test_{symbol_name}.py`. Always `import filters as f` for building test filter chains, and `import filters_pydantic as fp` for the package under test.

Test functions: `test_{symbol_name}_{scenario}`. Each test file needs a module-level docstring.

Every test function also needs its own one-sentence docstring stating the scenario under test — what must hold, not a restatement of the function name or the call being made. It's the sentence a reviewer checks an assertion against, so name the requirement (e.g. "A single chain failure surfaces as one `value_error` located at the failing field"), not the mechanism. This isn't the code the "Writing for coding agents" rule below tells you to skip documenting — a requirement lives in the author's head, not in the test body — see ADR 004.

## Docstrings

Google/Napoleon format (`Args:`, `Returns:`, `Note:`) — not Sphinx `:param:` style. Max 80 chars per line. Escape backslashes (e.g. `'\\n'` not `'\n'`). Blank line before lists inside `Args:` sections to avoid Sphinx indentation warnings. ReadTheDocs treats all Sphinx warnings as errors — resolve them before pushing.

## Code Comments

Place comments on the line preceding the code they document, not as trailing comments.

## Language and Style

- NZ English; incorporate Te Reo Māori where natural (e.g. "mahi", "kaupapa")
- Use "Initialises" not "Initializes"

### Writing for coding agents

- Do not document information that already exists in the coding agent's training data or could be easily discovered by reading the code.
- Do not list individual files; list high-level directories so the agent knows where to look.
- Aim for concise style that optimises token count without sacrificing clarity.

## Branches

- `main` — the only long-lived branch; releases are tagged directly from it
- Feature branches off `main` for all new work, merged back via PR

## Git Worktrees

Use `.claude/worktrees/` for isolated workspaces (project-local, gitignored).

Keep `.claude/` a real directory — only `.claude/skills` is a symlink into `.agents/skills`. If `.claude/` itself is a symlink, the native worktree tool refuses to run.

After switching to a worktree, run the autohooks activate command (see Commands) to install the pre-commit hook for that worktree.

## Package

Package name is `phx-filters-pydantic` (distinct from the `filters_pydantic` import name).

## Troubleshooting

**Sphinx forward reference errors** (`TypeError: unsupported operand type(s) for |`): `"ClassName" | None` fails at Python runtime because `str.__or__` is not supported — not a Sphinx bug, and not fixed in Sphinx 9. Use `typing.Optional["ClassName"]` — see Architecture above.
