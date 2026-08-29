---
status: Archived
date: 2026-08-29
scope: [test/, scripts/]
summary: Every test function carries a one-sentence docstring stating the scenario under test — what must hold, not a restatement of the function name or call.
revisit-when: Generic or restating docstrings recur across reviews, i.e. the convention alone isn't holding, and presence-only enforcement (e.g. ruff's pydocstyle "D" rules) is worth adding.
archived-because: A `.claude/rules/testing.md` rule with `paths` frontmatter loads this convention whenever an agent reads or edits an existing matching test file; a brand-new file's first `Write` doesn't trigger it, so `AGENTS.md`'s always-loaded pointer to the same file backs that case.
---

# 004: Docstring Per Test Function

## Context

Test functions here follow `test_{symbol_name}_{scenario}` naming, and some carry an
inline comment somewhere in the body explaining the scenario — but neither is
consistent or placed where a reviewer looks first. A name states the setup
(`fail_reports_single_filter_error`), not the requirement the assertions exist to
prove, and most tests in [`test_filter_field.py`][] and
[`test_pydantic_model.py`][] carry no explanatory comment at all. A reviewer
judging whether an assertion is the right one has to read the whole function body,
and for a name-only test, infer the requirement from the assertions themselves —
which is exactly the check a docstring should let them skip.

## Options

### Option 1: Do nothing — names and ad hoc comments only

Keep relying on `test_{symbol_name}_{scenario}` names, with an inline comment added
only when a contributor judges the scenario non-obvious.

**Cons:** Whether a comment exists, and where inside the body it sits, is left to
individual judgement, so a reviewer has no consistent place to check an assertion
against.
**Risks:** "Non-obvious" drifts per author as the suite grows, and the scenarios most
worth documenting — a subtle edge case — are exactly the ones an author is most
likely to find obvious to themselves.

### Option 2: One-sentence docstring on every test function (Accepted)

Every test function or method carries a one-sentence docstring stating what must
hold — the claim the assertions exist to prove — not a restatement of the function
name or the call being made.

**Cons:** Adds a line to every test function.
**Risks:** None significant — `scripts/`'s test suite (ported from
`phx-claude-siat`) already follows this shape, so the convention adopts a pattern
already proven in this repo rather than inventing one.

### Option 3: Non-obvious tests only, per the project's "Writing for coding agents" rule

Require a docstring only where a contributor judges the scenario isn't obvious,
consistent with [`AGENTS.md`][]'s existing rule not to document what a reader can
discover by reading the code.

**Cons:** "Obvious" is the same per-author judgement Option 1 already relies on; a
reviewer still can't tell, from the file alone, whether a missing docstring means
"obvious" or "nobody wrote one".
**Risks:** That rule stops a reader documenting a test's *own* code — the setup, the
call, the assertions, all already there to read. A docstring here isn't that: it
states which requirement the code under test must satisfy, a fact that lives in the
author's head, not in the test body or in `src/`, so reading either one harder
doesn't recover it. The rule and this convention govern different things; the rule
doesn't authorise skipping this.

## Decision

Adopt Option 2. A reviewer checks an assertion against the requirement it is meant
to prove, not against the test's name or its call — so that requirement needs a
fixed, predictable place to live. A docstring is that place: unlike a comment, it
sits in one location on every test regardless of body length, and unlike the name,
it states a claim in a full sentence rather than a scenario label.

## Consequences

- Every existing test function gains a docstring; `test_filter_field.py` and
  `test_pydantic_model.py` predate this convention and are updated as part of this
  change.
- An inline comment that already states what must hold moves into the docstring; a
  comment explaining a coding choice (e.g. why a test calls `model_validate` instead
  of the constructor) stays a comment, since that's a different kind of fact from
  the requirement a docstring records.
- A generic docstring that restates the function name (rather than the requirement)
  is a defect the same way an unclear test name is — nothing here checks for it
  automatically.
- The convention now lives in [`testing.md`][], loaded automatically for an existing
  matching test file rather than read once from this ADR or from `AGENTS.md` prose;
  this document keeps the record of why.
- Claude Code loads a `paths`-scoped rule on read, not on write
  ([anthropics/claude-code#23478][]), so a brand-new test file's first `Write` still
  depends on `AGENTS.md`'s pointer rather than the rule firing on its own.

[`AGENTS.md`]: ../../AGENTS.md
[anthropics/claude-code#23478]: https://github.com/anthropics/claude-code/issues/23478
[`test_filter_field.py`]: ../../test/test_filter_field.py
[`test_pydantic_model.py`]: ../../test/test_pydantic_model.py
[`testing.md`]: ../../.agents/rules/testing.md
