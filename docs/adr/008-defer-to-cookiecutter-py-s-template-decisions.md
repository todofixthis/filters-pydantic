---
status: Accepted
date: 2026-11-23
scope: [.agents/rules/template-owned.md, .agents/rules/testing.md, .autohooks/, .claude/settings.json, .copier-answers.yml, .github/workflows/build.yml, AGENTS.md, docs/adr/, pyproject.toml, renovate.json, test/]
summary: This project follows the copier template todofixthis/cookiecutter-py, which writes and owns the files that .agents/rules/template-owned.md lists, and defers to its decisions in them; cookiecutter-py ADR 019 replaces this project's ADR 007 (rely on the phx plugin for ADR tooling, never a repo-local generator, vendored copy or pre-commit hook), ADR 018 there sets the phx-adr pins, and the templated .agents/rules/testing.md (ADR 010 there) replaces this project's ADR 004 (a one-line docstring on every test function); diverging from a template decision on purpose needs an ADR here naming the cookiecutter-py ADR it departs from.
revisit-when: This project stops taking template updates; the template supersedes or renumbers one of the ADRs named here; ADRs here are routinely authored in a harness other than Claude Code.
---

# 008: Defer to cookiecutter-py's Template Decisions

## Context

This project now takes its tooling from [cookiecutter-py's copier
template][], recorded in `.copier-answers.yml`; each template release
arrives as a Renovate PR running `copier update` ([cookiecutter-py ADR
015][]). The files copier writes are template-owned:
`.agents/rules/template-owned.md` lists them and says how to change one,
and is itself written by the template.

Two of this project's ADRs decide what the template now decides:

- [ADR 007][] relies on the phx plugin for ADR tooling, with CI's
  `phx-adr` pinned to a release's commit. [cookiecutter-py ADR 019][]
  decides the same, rejecting 007's repo-local and vendored alternatives
  and a pre-commit hook besides, and [cookiecutter-py ADR 018][] sets the
  pins in the `adrs` job and AGENTS.md. 007 names the CI job `adr`, which
  the template calls `adrs`.
- [ADR 004][] requires a one-sentence docstring on every test function, and
  is archived on `.agents/rules/testing.md` as its defence. That rule is now
  the template's ([cookiecutter-py ADR 010][]): it requires the docstring on
  one line, no longer cites 004, and changes with any template release.

The template also brings the `develop` → `main` branch model and its
release skill, replacing this project's single `main` branch with releases
tagged from it.

## Options

### Option 1: Do nothing

Keep ADRs 004 and 007 beside the template's files.

**Cons:** Two records of each decision. 007 describes a CI job that no
longer exists; 004 is archived on a rule this project no longer owns, which
can drift from it with nothing in this corpus noticing.

### Option 2: Defer to the template, superseding 004 and 007 (Accepted)

**Cons:** A reader follows a link to another repository for the reasoning,
and the revisit triggers of ADR 019 sit in the template's index, where
only the template's maintainer meets them. This ADR names template ADRs by
number, which goes stale if the template supersedes or renumbers one; the
links pin the 1.3.2 tag, so they still lead to the decision this project
adopted.

## Decision

Option 2. The template owns these files, so it owns the decisions about
them, and its ADRs and rules record 004's and 007's decisions; a second
copy here can only fall behind. One of 019's triggers, ADRs routinely
authored outside Claude Code, can only be seen from inside this project,
so this ADR's `revisit-when` carries it.

## Consequences

- `.agents/rules/template-owned.md` decides whether a change to a
  template-owned file is made here or proposed to cookiecutter-py; that
  rule, not this ADR's `scope`, lists the files.
- Diverging from a template decision on purpose needs its own ADR here,
  naming the template ADR it departs from.
- The `develop` and `main` rulesets must require the template's `gate` job,
  which aggregates every CI job, `adrs` included, in place of `docs`,
  `test (…)` and `adr`. `adr` never reports once the template's CI lands,
  so make the switch before or with the merge that brings it.
- The existing tests' multi-line docstrings predate the template's one-line
  rule; new ones follow it.

[ADR 004]: 004-docstring-per-test-function.md
[ADR 007]: 007-rely-on-the-phx-plugin-for-adr-tooling.md
[cookiecutter-py ADR 010]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/010-split-agents-md-into-templated-and-project-parts.md
[cookiecutter-py ADR 015]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/015-propagate-template-changes-with-copier-and-rotate-python-from-agent-sessions.md
[cookiecutter-py ADR 018]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/018-require-gate-everywhere-and-the-release-check-on-main.md
[cookiecutter-py ADR 019]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/019-rely-on-the-phx-plugin-for-adr-tooling.md
[cookiecutter-py's copier template]: https://github.com/todofixthis/cookiecutter-py
