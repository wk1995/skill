# Changelog

All notable changes to this Skill are documented here. This file is required
per `AGENTS.md`: every `metadata.version` bump must add an entry with the
version, date, and a change summary.

## [Unreleased]

- Docs: fixed the version example in `references/sync-model.md` (`0.0.2` -> `0.0.3`).
- Sync Rules: added the requirement that every `metadata.version` bump must
  update `CHANGELOG.md` (project constraint, see `AGENTS.md`).

## [0.0.3] - 2026-08-30

- Safety: `copy_skill_tree` now rejects same-source or nested targets across its
  four call sites, preventing a later `sync` from clearing a Skill directory onto
  itself.
- Safety: `command_link` refuses role paths that resolve to the same or nested
  location at registration time, instead of discovering the hazard during sync.
- Docs: `SKILL.md` Sync Rules document the symlink self-copy hazard.
- Bumped `metadata.version` to `0.0.3`.
