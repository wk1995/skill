# Skill Contribution Guide

This file governs every new or substantially updated Skill under `skills/`.

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

Before declaring a PR review or PR fix complete, the agent must:

1. Work from a clean, committed worktree and compare the complete PR with its base branch using `git diff --name-status --find-renames <base>...HEAD`.
2. Inspect deletions, renames, executable-bit changes, generated files, and newly tracked ignored files. A review based only on reading changed source lines is incomplete.
3. Run `bash tests/pr-review-gate.sh <base>` and report its result. For the usual local checkout, `<base>` is `origin/main`; CI passes the pull request's exact base SHA.
4. Exercise stateful commands across multiple invocations, including existing or malformed persisted state, rather than testing only a fresh single command.
5. Add a regression test for every confirmed review defect. Auto-fix behavior requires negative, fix-success, and idempotency coverage.
6. Verify external product claims against current authoritative documentation and, when behavior is version-dependent, a versioned product configuration. State the scope instead of generalizing one installation.

The `skill-catalog` required status check invokes the same gate in GitHub Actions. Protected local state under `.skill-sync/` must have no net PR changes; stopping tracking or migrating it requires a separately designed migration rather than an ordinary cleanup commit.

## Changelog Requirement

Every Skill must maintain a `CHANGELOG.md` in its own directory, next to `SKILL.md`.

- Whenever `metadata.version` is incremented (major, minor, or patch), add an entry recording the new version, the date (UTC), and a short summary of what changed, including any impact on triggers, safety, or compatibility.
- An upgrade PR that bumps `metadata.version` without updating `CHANGELOG.md` is non-compliant.
- Use a top-level `## [Unreleased]` section for committed changes that have not yet shipped under a new version.
- `CHANGELOG.md` is written in English; a bilingual entry is optional for Skills that also ship a Chinese README.
