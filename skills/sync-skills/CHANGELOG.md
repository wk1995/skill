# Changelog

All notable changes to this Skill are documented here. This file is required
per `AGENTS.md`: every `metadata.version` bump must add an entry with the
version, date, and a change summary.

## [Unreleased]

- Expand the English and Chinese README coverage for every supported command, location role, source-selection rule, report workflow, installation repair path, state migration, and recovery behavior. This is a documentation-only change with no version or trigger-metadata change.

## [0.2.3] - 2026-09-08

- Apply registry-wide location identity and containment checks to ordinary role registration, conversion, synchronization, and rollback before mutation.
- Reject Agent snapshot rollback when the current installation declares another Skill identity, and fail installation protection closed when adapter discovery reports errors.
- Detect and restore permission-only installation damage, including staged/post-install verification and idempotent permission-aware rollback. Manifest-v2 content digests remain compatible.
- Inventory explicitly registered nested local installs through shared identity, Agent ownership, and deduplication checks.
- Add five stateful finding regressions and a staged/post-install permission-failure test. Trigger selection and adapter versions are unchanged.

## [0.2.2] - 2026-09-08

- Reject cross-group nested installation paths before repair or rollback, and conflicting non-empty install identities before repair can modify data.
- Report external/project identity conflicts and duplicate identities within related projects without linking ambiguous copies or aborting inventory.
- Deduplicate repeated local roots by filesystem identity and align portable digests with the builder's top-level Agent override boundary.
- Protect Skill inputs from report lock writes and report installs without trusted builds as `agent-build-missing`, never `synced`.
- Add eight stateful regressions covering rejection, correction, repeat execution, path aliases, and preservation of unselected copies. Triggers and adapter versions remain unchanged.

## [0.2.1] - 2026-09-08

- Package the report validator and informative schema with the portable Skill.
- Validate complete build manifests before accepting any entries; report malformed builds without aborting inventory.
- Reject conflicting registry identities, unsupported/cross-Agent local locations, symlink installs, and report output overlapping known Skill trees.
- Preserve recovery staging and report snapshot paths on installation recovery failure; support repair snapshot rollback with idempotency.
- Treat healthy project-only inventories as strict success and document exit code 2, report-only retries, and the authoritative runtime contract. Triggers remain unchanged.

- No unreleased changes.

## [0.2.0] - 2026-09-07

- Relationship reporting: generate canonical machine-local JSON and a single-table Markdown report across portable Skills, dynamic Agent Builders, local installs, and explicitly registered projects.
- Builder discovery: resolve local Skill inventory roots from declarative adapters and support future Builders without a fixed Agent list.
- Provenance: upgrade Agent build manifests to v2 with stable sync IDs, portable digests, output digests, core versions, and safe artifact paths.
- Registry: add explicit multi-project/local/external locations while retaining read compatibility with legacy `roles`.
- Safety: atomically write private reports outside the repository, preserve completed mutations when refresh becomes stale, and reject portable sync into Agent install roots before snapshot or overwrite.
- Repair: snapshot and atomically reinstall incomplete Agent installations from a trusted same-Agent build, preserve divergent local changes by default, and make repeated repair idempotent.
- Tests: cover dynamic coverage, version divergence, unlinked local Skills, explicit projects, stable rendering, output permissions, replacement failure recovery, stale refresh, sync rejection, repair success, conflict preservation, and idempotency.

## [0.1.0] - 2026-09-07

- State isolation: default registry and snapshot storage now uses an XDG state directory outside the repository, namespaced by checkout identity.
- Migration: add an idempotent `migrate-state` command that copies and verifies legacy `.skill-sync/` data without deleting its source or overwriting a different destination.
- Safety: reject symlinks, special files, same-path aliases, and both source/target nesting directions before migration mutates the destination.
- Compatibility: callers can continue to select an explicit location with `--state-dir`; legacy repository-local state remains available as migration input.
- Tests: cover successful migration, malformed state preservation, file-mode fidelity, repeat execution, destination conflicts, interrupted copies, path overlap, case aliases, symlinks, missing sources, file targets, and missing optional executables.

## [0.0.6] - 2026-09-07

- Safety: compare existing paths by filesystem identity as well as resolved spelling, preventing case-only aliases on case-insensitive filesystems from bypassing self-copy and role-path validation.
- Safety: apply filesystem-aware ancestor checks to paths that do not exist yet, so case-aliased nested targets are rejected before any directory is created or cleared.
- Tests: cover copy rejection, status reporting, content preservation, and nested-path detection for real or simulated case-insensitive path aliases.

## [0.0.5] - 2026-09-07

- Safety: reject copies when the source is nested inside the target, preventing target cleanup from deleting the source before iteration begins.
- Safety: validate all persisted role paths before `sync` creates snapshots or copies files, so malformed legacy registries fail without modifying either Skill.
- Safety: apply the same persisted-path validation before `rollback` creates a pre-rollback snapshot or restores any role, preventing a parent restore from overwriting an unselected nested role.
- Tests: exercise both the low-level reverse-nesting guard and a stateful `sync` against an unsafe persisted registry.
- Tests: cover a stateful single-role `rollback` against an unsafe persisted registry and verify that no content or snapshot is changed.

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
