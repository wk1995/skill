# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [0.0.2] - 2026-09-07

- Fixed README auto-fix handling for Codex invocation syntax embedded within a fenced example line, including natural-language forms such as `Use $skill-name ...`.
- Added regression coverage proving the rewritten example passes the compatibility check and preserves idempotency.

## [0.0.1] - 2026-09-04

- Added the WorkBuddy compatibility audit and auto-fix workflow.
- Added product-configured Skill directory guidance for domestic and WorkBuddy AI/overseas builds.
- Added checks for unqualified Codex invocation syntax in `SKILL.md` and README usage sections.
- Added safe external-path reporting, file-accurate CI annotations, negative fixtures, and idempotency coverage.
