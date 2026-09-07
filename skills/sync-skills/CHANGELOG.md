# Changelog

All notable changes to this Skill are documented here. This file is required
per `AGENTS.md`: every `metadata.version` bump must add an entry with the
version, date, and a change summary.

## [Unreleased]

- No unreleased changes.

## [0.0.5] - 2026-09-07

- Safety: reject copies when the source is nested inside the target, preventing target cleanup from deleting the source before iteration begins.
- Safety: validate all persisted role paths before `sync` creates snapshots or copies files, so malformed legacy registries fail without modifying either Skill.
- Tests: exercise both the low-level reverse-nesting guard and a stateful `sync` against an unsafe persisted registry.

## [0.0.4] - 2026-09-04

- Safety: `link` and `convert` now validate the complete candidate registry,
  including roles saved by earlier commands and symlink-resolved paths.
- Status: unsafe same-path or nested role registrations now report
  `path_issues` and make the group non-clean.
- Data safety: documented that removal of legacy tracked `.skill-sync` state
  must be staged separately so merges cannot delete collaborators' snapshots.
- Docs: updated the version-policy example and changelog requirement.

## [0.0.3] - 2026-08-30

- Safety: `copy_skill_tree` now rejects same-source or nested targets across its
  four call sites, preventing a later `sync` from clearing a Skill directory onto
  itself.
- Safety: `command_link` refuses role paths that resolve to the same or nested
  location at registration time, instead of discovering the hazard during sync.
- Docs: `SKILL.md` Sync Rules document the symlink self-copy hazard.
- Bumped `metadata.version` to `0.0.3`.
