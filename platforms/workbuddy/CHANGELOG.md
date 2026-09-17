# WorkBuddy Adapter Changelog

## [Unreleased]

- No unreleased changes.

## [1.1.1] - 2026-09-17

- Change-Type: fix
- Summary: Declare both WorkBuddy editions' machine-local Skill roots so relationship inventory and Agent-install repair can locate either install.
- Compatibility: Portable Skills and generated artifacts are unchanged; only adapter `local_skill_roots` metadata changed.

- Replaced the non-existent `.agents/skills` root with the international (`~/.workbuddy-ai/skills`, workbuddy.ai) and China (`~/.workbuddy/skills`, workbuddy.cn) WorkBuddy roots.

## [1.1.0] - 2026-09-07

- Declared the machine-local WorkBuddy-compatible Skill root for adapter-driven relationship inventory.

## [1.0.1] - 2026-09-07

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated WorkBuddy build artifact.
- Builder validation: direct builds now enforce the same adapter and per-Skill override checks as `--check` before writing output.
- Builder safety: nested reserved `SKILL.append.md` files are rejected and cannot leak unrendered template placeholders into generated Skills.

## [1.0.0] - 2026-09-07

- Added the declarative WorkBuddy adapter and independent `0.1.0` Skill-collection artifact.
- Kept WorkBuddy discovery, invocation, and installation guidance out of portable Skill sources.
