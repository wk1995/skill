# WorkBuddy Adapter Changelog

## [Unreleased]

- No unreleased changes.

## [1.0.1] - 2026-09-07

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated WorkBuddy build artifact.
- Builder validation: direct builds now enforce the same adapter and per-Skill override checks as `--check` before writing output.
- Builder safety: nested reserved `SKILL.append.md` files are rejected and cannot leak unrendered template placeholders into generated Skills.

## [1.0.0] - 2026-09-07

- Added the declarative WorkBuddy adapter and independent `0.1.0` Skill-collection artifact.
- Kept WorkBuddy discovery, invocation, and installation guidance out of portable Skill sources.
