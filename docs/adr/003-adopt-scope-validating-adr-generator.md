---
status: Accepted
date: 2026-08-29
scope: [docs/adr/, scripts/adr/, scripts/frontmatter.py, .autohooks/adr_index.py, pyproject.toml]
summary: Replace the PyYAML-based, tags-only ADR index generator with the phx:writing-adrs skill's stdlib-only, scope-validating reference implementation from todofixthis/phx-claude-siat.
revisit-when: scripts/adr/generate_index.py or scripts/frontmatter.py changes upstream in phx-claude-siat.
---

# 003: Adopt Scope-Validating ADR Generator

## Context

[ADR 001][] shipped with a `tags` field and no `scope`, and reviewing it against
[`phx:writing-adrs`][] surfaced why: `scripts/adr/generate_index.py` here predates, and
diverges from, what the skill assumes a generator does. It parses frontmatter with
PyYAML, renders a `tags`-keyed Tags column the skill doesn't define, has no `scope`
field or validation at all, has no `revisit-when` column, and excludes only `Superseded`
ADRs from the index rather than `Superseded` and `Archived` both. Nothing here catches
an ADR missing `scope`, an `Archived` decision without `archived-because`, or a `scope`
entry naming a path that no longer exists.

`todofixthis/phx-claude-siat` — the skill's own repository — carries a reference
implementation (`scripts/adr/generate_index.py` and `scripts/frontmatter.py`) enforcing
every rule the skill documents, plus an `--for <path>` mode answering the reverse
question a `docs/adr/INDEX.md` reader cannot ask: which decisions bind the file I'm
about to edit.

## Options

### Option 1: Do nothing — keep the tags-based generator

**Pros:** No migration.
**Cons:** ADRs in this repo can't rely on the guarantees `phx:writing-adrs` documents —
a missing `scope`, an unpaired `archived-because`, or a dead `scope` entry all pass
silently, as ADR 001's gaps did.
**Risks:** The drift between this repo's tooling and the skill it claims to follow keeps
compounding with every ADR written against the skill's text rather than a check.

### Option 2: Port the reference implementation from `phx-claude-siat` (Accepted)

Replace `scripts/adr/generate_index.py` and add `scripts/frontmatter.py` with the
upstream versions, adapted to this repo's layout and pytest-based test running.

**Cons:** Requires rewriting `.autohooks/adr_index.py` to the new `generate(adr_dir,
repo_root)` signature and porting its ~800-line test suite. This is a copied file, not a
dependency — no package boundary re-syncs it, so a later change to the upstream
generator only reaches this repo if someone notices and re-ports it by hand.
**Risks:** None significant — the logic is already exercised by that suite; the port
only needs to prove the adaptation didn't drift from it.

### Option 3: Write a bespoke local generator implementing the same rules

Reimplement `scope` validation, the `revisit-when` column, and `Archived` exclusion
independently, without adopting the upstream module.

**Pros:** Full control over this repo's exact wording and behaviour.
**Cons:** Duplicates logic that already exists, is tested, and evolves with the skill
upstream.
**Risks:** Reintroduces the exact failure mode this ADR responds to — a local
implementation drifting from what `phx:writing-adrs` assumes.

## Decision

Adopt Option 2. Porting the upstream implementation, rather than reimplementing its
rules locally, closes the current drift without a second party maintaining its own
reading of what the skill requires. It does not prevent drift from recurring — the port
is a copy, not a dependency, so it goes stale the moment upstream changes without
someone noticing — which is why this ADR carries a `revisit-when` for exactly that.

## Consequences

- `scripts/adr/generate_index.py` and `scripts/frontmatter.py` gain a ported
  `unittest`-based test suite; `pytest`'s `testpaths` gains `scripts` so `uv run pytest`
  covers it alongside `test/`.
- `pyyaml` and `types-pyyaml` are dropped from the dev dependency group — the generator
  was their only consumer in this repo.
- Every `Accepted` or `Archived` ADR must carry a valid `scope`, checked against the
  filesystem, and the ported parser rejects a bare `tags` field outright; ADR 001 needed
  `scope` added and `tags` removed as part of this change.
- The ported module's `Archived`/`Superseded` field-pairing and `revisit-when` checks
  have no prior exercise in this repo — no ADR here has used either yet, so this port is
  their first real test, not a like-for-like swap of proven local behaviour.
- `.autohooks/adr_index.py` calls `generate(ADR_DIR, REPO_ROOT)` instead of the old
  zero-argument `generate()`, and stages the index via the module's own path constants
  rather than a removed `INDEX_FILE` export.
- The generator gains a `--for <path>` mode, callable manually
  (`uv run python -m scripts.adr.generate_index --for <path>`) but not wired into any
  hook or CI job here — `.autohooks/adr_index.py` only regenerates the index, so this
  repo gets the lookup without yet exposing it at commit time.

[ADR 001]: 001-filterfield-as-annotated-metadata.md
[`phx:writing-adrs`]: https://github.com/todofixthis/phx-claude-siat/blob/main/skills/writing-adrs/SKILL.md
