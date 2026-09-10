# Skill Contribution Guide

This file governs all repository work. Its Skill structure rules apply to every
new or substantially updated Skill under `skills/`, and its PR review procedure
applies to every pull request reviewed or fixed in this repository.

## Required Structure

Each new Skill must use a lowercase hyphenated directory name and include the portable core, user documentation, changelog, and an Agent-build boundary:

```text
skills/<skill-name>/
|-- SKILL.md
|-- README.md
|-- README.zh-CN.md
|-- CHANGELOG.md
`-- agent-builds/
    `-- <agent>/              # Optional per-Skill override for a known adapter
```

`SKILL.md` remains the portable agent-facing entry point. It must contain valid frontmatter with `name`, `description`, `metadata.sync_id`, and `metadata.version`; `metadata.sync_id` is the immutable synchronization-group identifier and must not change when the Skill name changes. Add `metadata.triggering.include` and `metadata.triggering.exclude` when explicit trigger metadata is available. Do not put Agent-specific invocation syntax, installation paths, manifests, UI metadata, or compatibility sections in this portable file.

`README.md` is the user-facing companion document. It must introduce the Skill, explain how to use it, state when it triggers, and state when it does not trigger. Keep it consistent with `SKILL.md`; `metadata.triggering.exclude` takes priority if the two descriptions ever appear to conflict.

## README.md Requirements

Write README files in English by default. Chinese is supported through an equivalent `README.zh-CN.md` with visible language links in both README files. Keep the two language versions aligned when changing usage or trigger guidance.

Every Skill README must contain these sections, or clear equivalents:

1. **How To Use It** — user-facing prompts, inputs, commands, or workflow expectations.
2. **When It Triggers** — concrete request types that should select the Skill.
3. **When It Does Not Trigger** — nearby request types that should not select the Skill.

Avoid duplicating the full agent procedure from `SKILL.md`. Link to it for detailed operational and safety instructions instead.

## Repository Documentation

When adding or removing a Skill, update both root catalogs in the same change:

- In `README.md`, link every Skill to its English `skills/<skill-name>/README.md` only.
- In `README.zh-CN.md`, link every Skill to its Chinese `skills/<skill-name>/README.zh-CN.md` only.

Do not mix English and Chinese Skill README links within either root catalog.

## Catalog Generation And Pull Requests

The Skills tables in the root READMEs are generated. After adding, removing, or changing a Skill, run:

```bash
python scripts/skill_catalog.py --write
python scripts/skill_catalog.py --check
```

The `skill-catalog` GitHub Actions check validates every Skill and both generated catalogs on PRs targeting `main`. A PR cannot merge until the check passes. For an internal PR, the workflow can commit catalog updates back to its source branch only when the repository provides `SKILL_CATALOG_TOKEN`; never grant this token permission to bypass `main` branch protection. Fork PRs must include generated catalog changes in their own commits.

`agent-builds/` is the boundary for per-Skill Agent overrides. A platform subdirectory is optional and must match an adapter under `platforms/<agent>/`; for example, Codex UI metadata belongs at `agent-builds/codex/agents/openai.yaml`. If a Skill needs no override yet, retain the otherwise-empty directory with `.gitkeep`. Optional core directories such as `scripts/`, `references/`, `assets/`, `src/`, and `tests/` should be added only when the Skill needs them.

## Agent Adapter Rules

- Put defaults shared by every Skill for one Agent in `platforms/<agent>/`, not in each Skill.
- Put only exceptional, Skill-specific files in `skills/<skill-name>/agent-builds/<agent>/`.
- A new Agent adapter must be discoverable by adding `platforms/<agent>/adapter.json`; do not add it to a central switch or modify every Skill.
- Adapter `version` and generated `artifact_version` are independent from `metadata.version` in portable `SKILL.md`. Adding or changing platform support does not bump a Skill core version unless its portable behavior also changes.
- Run `python3 scripts/agent_build.py --check` and build the affected adapter before submitting the change.

See [docs/agent-build-architecture.md](docs/agent-build-architecture.md) for the overlay contract and generated layouts.

## Required PR Review Procedure

Use [docs/pr-review-playbook.md](docs/pr-review-playbook.md) as the single source
for review methods, matrices, and completion criteria. A green test suite is
necessary evidence, not proof of review coverage. The agent must:

1. Before implementation, identify the affected invariants and new or existing entry points; prepare the playbook's coverage ledger before the first review. Split independently reviewable behavior when practical, and document necessary coupling.
2. Review the complete PR against its exact base and head from a clean, committed worktree. Inspect deletions, renames, executable-bit changes, generated files, and newly tracked ignored files; read every changed implementation file without truncated output.
3. Trace each affected mutating entry point, including unchanged callers, through `entry point -> validation -> first mutation` and its failure-state invariant. Validation must run on direct invocation, before any persistence or early-success branch.
4. Exercise the applicable playbook matrices: state sequences, path identity and containment (including case-only aliases), recursive rules, real distributed artifacts, and missing dependencies under a controlled `PATH`. Record evidence per entry point and scenario; mark inapplicable or untested cases with reasons instead of blanket coverage claims.
5. For every confirmed defect, add regression evidence and expand the check to all sibling entry points and representations governed by the same invariant. Executable behavior requires a regression test; automatic fixes require rejection, fix-success, and idempotency coverage. Apply shared validation and parameterized tests where the contract is shared. Documentation-only corrections require an appropriate consistency check, not an artificial runtime test.
6. Read and deduplicate existing findings by root cause and trigger. Reproduce claims independently and link repeat confirmations to the original finding. After fixes, update the coverage ledger for the new head and recheck affected callers and interactions; fixing the listed comments alone is insufficient.
7. Before declaring a PR review or PR fix complete, run `bash tests/pr-review-gate.sh <base>` from the clean committed tree and report the exact base/head, result, coverage ledger, and residual risks. Normally `<base>` is `origin/main`; CI uses the exact PR base SHA. Verify external product claims against authoritative documentation and versioned configuration where relevant. Follow the playbook's completion criteria; CI or a passing gate alone is insufficient.

The `skill-catalog` required status check invokes the same gate in GitHub Actions. Runtime sync state belongs in the external XDG location selected by `sync-skills`. Legacy local state under `.skill-sync/` must have no net PR changes until every collaborator has migrated or backed it up; stopping tracking requires a dedicated migration change rather than an ordinary cleanup commit.

## Version Upgrade Rules

Follow [docs/versioning-policy.md](docs/versioning-policy.md) when selecting or
reviewing a version. These rules apply to Skill `metadata.version`, adapter
`version`, and generated `artifact_version`, each within its own compatibility
boundary; they do not apply to integer schema versions or external projects.

- Use exactly `MAJOR.MINOR.PATCH`: three non-negative decimal integers without
  leading zeroes, a `v` prefix, prerelease suffixes, or build metadata.
- PATCH (`1.2.3 -> 1.2.4`): compatible bug fixes, small optimizations, and internal
  refactoring that preserve the documented contract. These must not bump MAJOR.
- MINOR (`1.2.3 -> 1.3.0`): backward-compatible new capabilities or optional
  inputs. Reset PATCH to zero.
- MAJOR (`1.2.3 -> 2.0.0`): incompatible changes to supported workflows, triggers,
  inputs, outputs, persisted formats, or requirements. Reset MINOR and PATCH to
  zero. Require a concrete old/new behavior example and migration instructions;
  change size, effort, bug severity, or release count alone never justify MAJOR.
- Apply the same impact rules to `0.x.x`; promotion to `1.0.0` may also explicitly
  declare the first stable contract, but must not disguise an ordinary fix.
- Compare all changes since the last release of the same component. Increment
  only the highest required level once, by one, and reset lower levels. Do not
  bump once per commit or carry digits at nine (`1.2.9 -> 1.2.10`).
- Documentation-only clarifications, tests, and repository maintenance do not
  require a component bump when behavior and its contract stay unchanged.
  Agent-facing instructions that change behavior are not documentation-only.
- Before a bump, record the component, old/new versions, level, compatibility
  evidence, and migration needs in the change description. Record released
  changes in the owning changelog with a UTC date; keep pending changes under
  `[Unreleased]`. Never rewrite a published version to distribute different content.

## Changelog Requirement

Every Skill must maintain a `CHANGELOG.md` in its own directory, next to `SKILL.md`.

- Whenever `metadata.version` is incremented (major, minor, or patch), add an entry recording the new version, the date (UTC), and a short summary of what changed, including any impact on triggers, safety, or compatibility.
- An upgrade PR that bumps `metadata.version` without updating `CHANGELOG.md` is non-compliant.
- Use a top-level `## [Unreleased]` section for committed changes that have not yet shipped under a new version.
- `CHANGELOG.md` is written in English; a bilingual entry is optional for Skills that also ship a Chinese README.
