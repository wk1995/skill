# WorkBuddy Adapter Changelog

## [Unreleased]

## [artifact 1.0.0] - 2026-10-15

- Change-Type: breaking
- Summary: Bundle the updated PR review workflow, including project policy exclusion and one shared machine policy. Every Agent reads one state file, and the first review upgrades an identical legacy Skill-adjacent policy.
- Compatibility: The optional private project policy is an additional input; existing machine-policy precedence changes as described below. A new machine policy is no longer stored beside the WorkBuddy Skill; identical legacy adjacent policies are copied to the shared state file.

- Breaking-Change: Previously, an installed adjacent machine policy overrode an existing shared XDG file; the bundled pr-review-loop now uses the shared file. Adjacent `comment: false` with shared `comment: true` and a matching target changes from disabled to enabled comments.
- Migration: Compare legacy adjacent files with the shared policy before reviewing, explicitly choose the intended settings in the shared file, and verify effective comment targets and limits. Use `upgrade-machine-policy` only for identical legacy files when the shared file is absent.

## [1.1.2] - 2026-09-24

- Change-Type: fix
- Summary: Use immutable Skill identity to keep ignored PR review project policy files out of WorkBuddy build inputs and digests.
- Compatibility: Existing adapter discovery and generated file layout remain unchanged.

## [1.1.1] - 2026-09-17

- Change-Type: fix
- Summary: Add the China WorkBuddy product Skill root and keep the 1.1.0 `.agents/skills` root as a legacy install location.
- Compatibility: Existing 1.1.0 `workbuddy` installs under `~/.agents/skills` remain valid for inventory, repair, and rollback. `~/.workbuddy/skills` is an additional supported root. Portable Skills and generated artifacts are unchanged.

- Inventory `~/.workbuddy/skills` for China WorkBuddy.app (`dataFolderName` `.workbuddy`) and retain `~/.agents/skills` so 1.1.0 registrations stay on Agent `workbuddy`.
- Optional migration: copy or convert a Skill into `~/.workbuddy/skills/<skill>`, then register that product path with `link-location --agent-id workbuddy`. Do not retarget a 1.1.0 `workbuddy` install to `codex`; `.agents/skills` was the documented WorkBuddy root in 1.1.0, even though Codex also inventories that directory.
- International WorkBuddy AI is a separate adapter (`workbuddy-ai`) and is not claimed by this Agent ID.

## [1.1.0] - 2026-09-07

- Declared the machine-local WorkBuddy-compatible Skill root for adapter-driven relationship inventory.

## [1.0.1] - 2026-09-07

- Builder safety: repository-local output is restricted to `dist/`, and `--force` replaces only a validated WorkBuddy build artifact.
- Builder validation: direct builds now enforce the same adapter and per-Skill override checks as `--check` before writing output.
- Builder safety: nested reserved `SKILL.append.md` files are rejected and cannot leak unrendered template placeholders into generated Skills.

## [1.0.0] - 2026-09-07

- Added the declarative WorkBuddy adapter and independent `0.1.0` Skill-collection artifact.
- Kept WorkBuddy discovery, invocation, and installation guidance out of portable Skill sources.
