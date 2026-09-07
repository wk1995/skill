# Codex Adapter Changelog

## [Unreleased]

- No unreleased changes.

## [1.0.1] - 2026-09-07

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated Codex build artifact.
- Builder validation: direct builds now enforce the same adapter and per-Skill override checks as `--check` before writing output.
- Builder safety: nested reserved `SKILL.append.md` files are rejected and cannot leak unrendered template placeholders into generated Skills.

## [1.0.0] - 2026-09-07

- Added the declarative Codex adapter and independent `0.1.0` plugin artifact.
- Materialized per-Skill Codex overrides as standard `agents/openai.yaml` files in the generated plugin.
