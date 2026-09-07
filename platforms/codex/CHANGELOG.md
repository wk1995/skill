# Codex Adapter Changelog

## [Unreleased]

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated Codex build artifact.

## [1.0.0] - 2026-09-07

- Added the declarative Codex adapter and independent `0.1.0` plugin artifact.
- Materialized per-Skill Codex overrides as standard `agents/openai.yaml` files in the generated plugin.
