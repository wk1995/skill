# Skill Contribution Guide

This file governs every new or substantially updated Skill under `skills/`.

## Required Structure

Each new Skill must use a lowercase hyphenated directory name and include both files:

```text
skills/<skill-name>/
|-- SKILL.md
`-- README.md
```

`SKILL.md` remains the agent-facing entry point. It must contain valid frontmatter with `name`, `description`, `metadata.sync_id`, and `metadata.version`; `metadata.sync_id` is the immutable synchronization-group identifier and must not change when the Skill name changes. Add `metadata.triggering.include` and `metadata.triggering.exclude` when explicit trigger metadata is available.

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

Optional directories such as `agents/`, `scripts/`, `references/`, `assets/`, `src/`, and `tests/` should be added only when the Skill needs them.

## Changelog Requirement

Every Skill must maintain a `CHANGELOG.md` in its own directory, next to `SKILL.md`.

- Whenever `metadata.version` is incremented (major, minor, or patch), add an entry recording the new version, the date (UTC), and a short summary of what changed, including any impact on triggers, safety, or compatibility.
- An upgrade PR that bumps `metadata.version` without updating `CHANGELOG.md` is non-compliant.
- Use a top-level `## [Unreleased]` section for committed changes that have not yet shipped under a new version.
- `CHANGELOG.md` is written in English; a bilingual entry is optional for Skills that also ship a Chinese README.
