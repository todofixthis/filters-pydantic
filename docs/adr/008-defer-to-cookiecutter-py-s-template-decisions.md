---
status: Accepted
date: 2026-11-23
scope: [.agents/rules/template-owned.md, .claude/settings.json, .copier-answers.yml, .github/workflows/build.yml, AGENTS.md, docs/adr/, pyproject.toml, renovate.json]
summary: This project follows the copier template todofixthis/cookiecutter-py, which writes and owns the files that .agents/rules/template-owned.md lists, and defers to its decisions in them; cookiecutter-py ADR 019 replaces this project's ADR 007 (rely on the phx plugin for ADR tooling, never a repo-local generator, vendored copy or pre-commit hook), and ADR 018 there sets the phx-adr pins; diverging from a template decision on purpose needs an ADR here naming the cookiecutter-py ADR it departs from.
revisit-when: This project stops taking template updates; the template supersedes or renumbers one of the ADRs named here.
---

# 008: Defer to cookiecutter-py's Template Decisions

## Context

This project now takes its tooling from [cookiecutter-py's copier
template][], recorded in `.copier-answers.yml`; each template release
arrives as a Renovate PR running `copier update` ([cookiecutter-py ADR
015][]). The files copier writes are template-owned:
`.agents/rules/template-owned.md` lists them and says how to change one,
and is itself written by the template.

[ADR 007][] decided to rely on the phx plugin for ADR tooling, with CI's
`phx-adr` pinned to a release's commit. The template decides the same in
[cookiecutter-py ADR 019][], and pins `phx-adr` in its `adrs` job and
AGENTS.md as [cookiecutter-py ADR 018][] decides. 007 describes files the
template now owns: it names the CI job `adr`, which the template calls
`adrs`.

## Options

### Option 1: Do nothing

Keep ADR 007 beside the template's files.

**Cons:** Two records of one decision, one describing a CI job that no
longer exists, and a project-level owner for files whose changes now arrive
from the template.

### Option 2: Defer to the template, superseding 007 (Accepted)

**Cons:** A reader follows a link to another repository for the reasoning.
This ADR names template ADRs by number, which goes stale if the template
supersedes or renumbers one; the links pin the 1.3.2 tag, so they still
lead to the decision this project adopted.

## Decision

Option 2. The template owns these files, so it owns the decisions about
them, and ADR 019 records 007's decision with the same rejected options; a
second copy here can only fall behind.

## Consequences

- `.agents/rules/template-owned.md` decides whether a change to a
  template-owned file is made here or proposed to cookiecutter-py; that
  rule, not this ADR's `scope`, lists the files.
- Diverging from a template decision on purpose needs its own ADR here,
  naming the template ADR it departs from.
- Required status checks on `develop` and `main` move to the template's
  `gate` job, which aggregates every CI job, `adrs` included.

[ADR 007]: 007-rely-on-the-phx-plugin-for-adr-tooling.md
[cookiecutter-py ADR 015]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/015-propagate-template-changes-with-copier-and-rotate-python-from-agent-sessions.md
[cookiecutter-py ADR 018]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/018-require-gate-everywhere-and-the-release-check-on-main.md
[cookiecutter-py ADR 019]: https://github.com/todofixthis/cookiecutter-py/blob/1.3.2/docs/adr/019-rely-on-the-phx-plugin-for-adr-tooling.md
[cookiecutter-py's copier template]: https://github.com/todofixthis/cookiecutter-py
