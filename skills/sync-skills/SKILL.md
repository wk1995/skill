---
name: sync-skills
description: Use when linking, converting, synchronizing, inventorying, reporting, repairing Agent installs, versioning, auditing, or rolling back Skill copies across repository, project, machine-wide, or explicit external locations.
metadata:
  sync_id: "sync-skills"
  version: "0.2.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/sync-skills
  triggering:
    include:
      - The user asks to link, convert, synchronize, audit, version, compare, or roll back Skill copies.
      - The task involves local, project-level, repository-level, or external copies of the same Skill.
      - The task needs Skill provenance URLs, version history, content digests, snapshots, or difference reports.
      - The user needs to migrate legacy repository-local Skill synchronization state.
      - The user needs a machine-local relationship report across supported AI Agent Builders or needs to repair an incomplete Agent installation.
    exclude:
      - The user is only asking to use a Skill for its domain workflow rather than manage Skill copies.
      - The task is ordinary code editing and does not involve Skill synchronization, conversion, auditing, or rollback.
---

# Sync Skills

## Overview

Use this skill to keep equivalent Skill directories connected across this repository, project-owned locations, machine-wide Agent installations, Agent build artifacts, and explicit external paths. Treat one linked group as one logical Skill with multiple materialized copies and preserve the `portable source -> Agent build -> local install` derivation chain.

## Start Here

1. Identify the stable `metadata.sync_id`, current Skill name, and every copy that should participate in the sync group. The sync ID is immutable; the Skill name may change.
2. Inspect each copy's complete directory tree, including `SKILL.md`, scripts, references, assets, executable extensions, and any build-adapter inputs, before mutating anything.
3. Read `references/sync-model.md` when designing a new sync group, resolving a conflict, changing version policy, or performing a rollback.
4. Use `scripts/skill_sync.py` for deterministic operations whenever copying, snapshotting, status checking, or rollback is needed.
5. Keep runtime state outside the repository. The default is an XDG state directory isolated by checkout; migrate a legacy `.skill-sync/` directory before its tracked files are removed.
6. Read [references/sync-model.md](references/sync-model.md) before repairing an Agent install or interpreting relationship-report statuses.

## Location Roles

Use these role names consistently:

- `repo`: the canonical copy inside this repository, usually `skills/<skill-name>`.
- `local`: a machine-wide user copy at an explicitly resolved path.
- `project`: a project-specific copy owned by another workspace.
- `external`: any other explicit path, such as a checked-out plugin, bundle, archive staging folder, or temporary migration location.

A group may contain any subset of these roles. Do not invent paths; resolve each role to an absolute path before linking.

## Common Operations

Copy legacy repository-local state to the external default without deleting the source:

```bash
python skills/sync-skills/scripts/skill_sync.py migrate-state
```

The command verifies the copied tree, preserves file modes, refuses symlinks and path overlap, stops on a differing destination, and is idempotent when the destination already matches. Keep `.skill-sync/` in place until every collaborator has migrated or backed it up and the dedicated stop-tracking change is ready to merge.

Create or update a sync group using the immutable ID declared in `SKILL.md`:

```bash
python skills/sync-skills/scripts/skill_sync.py link my-skill-id --repo skills/my-skill --local /absolute/path/to/my-skill --external /other/path/to/my-skill --skill-url https://github.com/me/my-skill --repo-url https://github.com/me/skills-repo
```

Convert one physical copy into another location and link both:

```bash
python skills/sync-skills/scripts/skill_sync.py convert my-skill-id --source-path /absolute/path/to/my-skill --source-role local --source-url https://example.com/source --target-path skills/my-skill --target-role repo --target-url https://github.com/me/skills-repo

# Migrate a legacy name-keyed registry and set its first stable ID.
python skills/sync-skills/scripts/skill_sync.py rename old-skill-name --to my-skill-id --name new-skill-name

# For an existing stable group, keep --to equal to its current ID and change only the display name.
python skills/sync-skills/scripts/skill_sync.py rename my-skill-id --to my-skill-id --name new-skill-name
```

Inspect divergence:

```bash
python skills/sync-skills/scripts/skill_sync.py status my-skill-id
```

Show recorded versions and their update times:

```bash
python skills/sync-skills/scripts/skill_sync.py versions my-skill-id
```

Synchronize all linked copies from the most recently modified copy:

```bash
python skills/sync-skills/scripts/skill_sync.py sync my-skill-id
```

Synchronize from an explicit source role:

```bash
python skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
```

Rollback every linked copy to a recorded snapshot:

```bash
python skills/sync-skills/scripts/skill_sync.py rollback my-skill-id --snapshot 20260720T120000Z
```

List available snapshots:

```bash
python skills/sync-skills/scripts/skill_sync.py snapshots my-skill-id
```

Compare the different places between two snapshots or a snapshot and the current copy:

```bash
python skills/sync-skills/scripts/skill_sync.py diff my-skill-id --role local --from-snapshot 20260720T120000Z --to-current
```

Generate the machine-local relationship report using every supported Builder declared by `platforms/*/adapter.json`:

```bash
python skills/sync-skills/scripts/skill_sync.py relationships
python skills/sync-skills/scripts/skill_sync.py relationships --project app-a=/projects/app-a/skills --strict
```

Register another project or a local Agent installation explicitly:

```bash
python skills/sync-skills/scripts/skill_sync.py link-location my-skill-id \
  --location-id project:app-a --kind project --project-id app-a \
  --path /projects/app-a/skills/my-skill
```

Repair an already registered Agent installation from a trusted manifest-v2 build. Diverged local content is preserved unless replacement is explicitly authorized; authorized replacement is still snapshotted first:

```bash
python scripts/agent_build.py codex --force
python skills/sync-skills/scripts/skill_sync.py repair-agent-install my-skill-id \
  --agent codex --discard-local-changes
```

## Sync Rules

- Always snapshot all existing linked copies before overwriting any target.
- Treat `SKILL.md` as required. A path without `SKILL.md` is not a valid source copy.
- Refuse to link two roles that resolve to the same filesystem location, or one role nested inside another, including case-only path aliases on case-insensitive filesystems. A symlinked or case-aliased local directory pointing at the repository copy is already identical to its target, so register only real copies; linking it as a separate role would make a later sync copy the directory onto itself and destroy it.
- Preserve each Skill as a directory tree. Copy `SKILL.md`, `agent-builds/`, `scripts/`, `references/`, `assets/`, `extensions.yaml`, `src/`, and `tests/` when present. Platform-specific materialized files belong in build artifacts, not the portable source tree.
- Discover supported AI Agent Builders from adapter manifests, never from a fixed Agent list or from whichever `dist/` directories happen to exist. Resolve local inventory roots from each adapter, plus explicit overrides.
- Compare a portable source to its manifest-v2 Agent build, then compare a local installation only to the build for the same Agent. Different Agents may legitimately have different output digests.
- Treat an Agent installation without `metadata.sync_id` as registered but incomplete only when the registry already identifies the path. Snapshot and reinstall the complete build; do not declare a hand-edited frontmatter field to be a repair.
- Refuse ordinary portable repo sync into a registered or adapter-discovered Agent install directory. Use the Agent build/install flow instead.
- Exclude transient directories and files such as `.git`, `node_modules`, `dist`, `.DS_Store`, `__pycache__`, and Python bytecode.
- When the skill-management repository is on `master` or its configured default branch, compare linked copies by `metadata.version`; if versions differ, synchronize and let the higher version replace the lower version.
- When the repository is on any other branch, do not synchronize only because versions differ unless the user explicitly requests synchronization or the branch work requires updating the target copy.
- If versions are equal but digests differ, use normal conflict handling and require an explicit source unless only one linked role changed since the previous snapshot.
- If two or more copies changed since the previous snapshot and no source was specified, stop and report the conflict instead of choosing silently.
- Keep the immutable sync-group identity in `metadata.sync_id` and the logical Skill version in `metadata.version` in `SKILL.md`. New Skills must define a stable sync ID that does not change with `metadata.name`; `rename --to` is reserved for migrating legacy name-keyed registry entries and cannot change an existing stable ID.
- Use this Skill's own sync ID as `sync-skills` and its version as `0.2.0`.
- Store registry and snapshot runtime state outside the repository. By default, use `$XDG_STATE_HOME/sync-skills/<checkout-id>/`, or `$HOME/.local/state/sync-skills/<checkout-id>/` when `XDG_STATE_HOME` is unset. Treat repository-local `.skill-sync/` as legacy migration input only.
- Legacy registries keyed by a Skill name remain readable; run `rename <old-reference> --to <sync-id> --name <new-name>` to migrate the group and its snapshots before linking a renamed Skill.
- Record Skill addresses in the registry: `skill_urls` for canonical repository/documentation/registry/source URLs, and `role_urls` for role-specific remote/source URLs.
- If a role URL is not provided, infer it from `git remote get-url origin` when available.
- Record audit times in the registry: group `created_at`, group `updated_at`, per-role `content_updated_at`, per-version `created_at` and `updated_at`, and operation records such as `last_sync`, `last_convert`, and `last_rollback`.
- When a creation/update time is missing, infer it from Git commit history for the Skill path. If Git has no usable record, fall back to file modification time, then current UTC time.
- Record changed file summaries in `last_sync.differences_by_role`; use `diff` when line-level text differences are needed.
- Use `versions` to inspect version history and `diff` to inspect the exact files that differ between snapshots, current copies, or explicit paths.
- Do not overwrite executable extensions from an untrusted remote or external source until the user has approved the source, version, digest, entrypoints, and permissions.
- When bumping `metadata.version`, update the Skill's `CHANGELOG.md` with the new version, the date, and a change summary. This is a project requirement (see AGENTS.md).

## Conversion Pattern

To convert a local, project, external, or repo copy into another location:

1. Validate the source has `SKILL.md` and a valid `name`.
2. Run `convert` with explicit source and target paths.
3. Refuse the conversion if either path is nested inside the other; clearing a parent target would otherwise delete a nested source before copying begins.
4. Run `status` and confirm all roles report the same digest.
5. Preserve or set `metadata.version` according to the source of truth chosen for the group.

## Output Shape

For sync work, report:

- group name and linked roles;
- canonical Skill URLs and role URLs;
- source role and source version;
- targets updated or skipped;
- group creation time;
- snapshot id created before mutation;
- per-version creation/update time;
- content update time, operation time, and available diff command;
- conflicts, trust concerns, or invalid paths;
- rollback command for the created snapshot.

For relationship inventory, write `skill-relationships.json` and `skill-relationships.md` only under the external state directory (or another validated repository-external output directory). Show dynamic Builder columns, complete absolute paths, related projects, unlinked local Skills, build/install derivation, all applicable statuses, and `report_status: stale` when a completed mutation could not refresh the previous report.
