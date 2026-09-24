# Codex Adapter Changelog

## [Unreleased]

## [artifact 0.2.0] - 2026-09-24

- Change-Type: feature
- Summary: Bundle the updated PR review workflow and Skill sync rules while excluding local review policy files.
- Compatibility: Existing installed Skills retain their supported usage; the optional private project policy is an additional input.

## [1.1.2] - 2026-09-24

- Change-Type: fix
- Summary: Keep ignored PR review project policy files out of Codex build inputs and digests.
- Compatibility: Existing adapter discovery and generated file layout remain unchanged.

## [1.1.1] - 2026-09-08

- Discover the current user Skill root `.agents/skills` alongside the legacy `.codex/skills` root; preserve shared-root Agent attribution.

- No unreleased changes.

## [1.1.0] - 2026-09-07

- Declared the machine-local Codex Skill root for adapter-driven relationship inventory.

## [1.0.1] - 2026-09-07

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated Codex build artifact.
- Builder validation: direct builds now enforce the same adapter and per-Skill override checks as `--check` before writing output.
- Builder safety: nested reserved `SKILL.append.md` files are rejected and cannot leak unrendered template placeholders into generated Skills.

## [1.0.0] - 2026-09-07

- Added the declarative Codex adapter and independent `0.1.0` plugin artifact.
- Materialized per-Skill Codex overrides as standard `agents/openai.yaml` files in the generated plugin.
