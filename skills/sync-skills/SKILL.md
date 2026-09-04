---
name: sync-skills
description: Use when linking, converting, synchronizing, versioning, auditing, or rolling back multiple copies of the same Agent Skill across this repository, project-level skill folders, local Codex/user skill folders, or arbitrary external paths.
metadata:
  sync_id: "sync-skills"
  version: "0.0.4"
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
    exclude:
      - The user is only asking to use a Skill for its domain workflow rather than manage Skill copies.
      - The task is ordinary code editing and does not involve Skill synchronization, conversion, auditing, or rollback.
---

# Sync Skills

## Overview

Use this skill to keep equivalent Skill directories connected across locations such as this repository's `skills/`, a project's skill folder, a local Codex/user or WorkBuddy skill folder, and any external path. Treat one linked group as one logical Skill with multiple materialized copies.

## Platform Compatibility

This skill keeps Skill copies in sync across both OpenAI Codex and WorkBuddy.

- **Codex**: user-level skills live under `$CODEX_HOME/skills` or `~/.codex/skills`; the agent interface is `agents/openai.yaml`; Codex-specific artifacts include `agents/` and `extensions.yaml`.
- **WorkBuddy**: WorkBuddy reads `SKILL.md` directly and ignores `agents/openai.yaml`. Its installed-Skill directory is product-configured: domestic builds commonly use `~/.workbuddy/skills`, while WorkBuddy AI/overseas builds may use `~/.workbuddy-ai/skills`. Use the actual directory configured by the installed product. When syncing WorkBuddy copies, treat `SKILL.md` as the required file and copy `agents/`/`extensions.yaml` only when they exist.

Triggering differs between the two runtimes: Codex uses `metadata.triggering` and the `$sync-skills` invocation, while WorkBuddy triggers from the `description` automatically, so no `$`-prefix is needed there. Resolve the real Skill directory for the installed product before linking it.

## Start Here

1. Identify the stable `metadata.sync_id`, current Skill name, and every copy that should participate in the sync group. The sync ID is immutable; the Skill name may change.
2. Inspect each copy's `SKILL.md`, `agents/openai.yaml` (Codex only; ignored by WorkBuddy), scripts, references, assets, and extension files before mutating anything.
3. Read `references/sync-model.md` when designing a new sync group, resolving a conflict, changing version policy, or performing a rollback.
4. Use `scripts/skill_sync.py` for deterministic operations whenever copying, snapshotting, status checking, or rollback is needed.

## Location Roles

Use these role names consistently:

- `repo`: the canonical copy inside this repository, usually `skills/<skill-name>`.
- `local`: a machine-wide copy. In OpenAI Codex this is usually under `$CODEX_HOME/skills` or `~/.codex/skills`; in WorkBuddy it is under the product-configured data directory's `skills/` folder.
- `project`: a project-specific copy owned by another workspace.
- `external`: any other explicit path, such as a checked-out plugin, bundle, archive staging folder, or temporary migration location.

A group may contain any subset of these roles. Do not invent paths; resolve each role to an absolute path before linking.

## Common Operations

Create or update a sync group using the immutable ID declared in `SKILL.md`:

```bash
python skills/sync-skills/scripts/skill_sync.py link my-skill-id --repo skills/my-skill --local ~/.codex/skills/my-skill --external /path/to/my-skill --skill-url https://github.com/me/my-skill --repo-url https://github.com/me/skills-repo
```

Convert one physical copy into another location and link both:

```bash
python skills/sync-skills/scripts/skill_sync.py convert my-skill-id --source-path ~/.codex/skills/my-skill --source-role local --source-url https://example.com/source --target-path skills/my-skill --target-role repo --target-url https://github.com/me/skills-repo

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

## Sync Rules

- Always snapshot all existing linked copies before overwriting any target.
- Treat `SKILL.md` as required. A path without `SKILL.md` is not a valid source copy.
- Refuse to link two roles that resolve to the same path, or one role nested inside another. A symlinked copy such as `~/.workbuddy/skills/<name>` pointing at the repository copy is already identical to its target, so register only real copies; linking it as a separate role would make a later sync copy the directory onto itself and destroy it.
- Preserve each Skill as a directory tree. Copy `SKILL.md`, `agents/` (Codex only), `scripts/`, `references/`, `assets/`, `extensions.yaml` (Codex only), `src/`, and `tests/` when present. WorkBuddy skills are defined entirely by `SKILL.md` and often contain none of the Codex-only `agents/` or `extensions.yaml` files, so copy them only when they exist.
- Exclude transient directories and files such as `.git`, `node_modules`, `dist`, `.DS_Store`, `__pycache__`, and Python bytecode.
- When the skill-management repository is on `master` or its configured default branch, compare linked copies by `metadata.version`; if versions differ, synchronize and let the higher version replace the lower version.
- When the repository is on any other branch, do not synchronize only because versions differ unless the user explicitly requests synchronization or the branch work requires updating the target copy.
- If versions are equal but digests differ, use normal conflict handling and require an explicit source unless only one linked role changed since the previous snapshot.
- If two or more copies changed since the previous snapshot and no source was specified, stop and report the conflict instead of choosing silently.
- Keep the immutable sync-group identity in `metadata.sync_id` and the logical Skill version in `metadata.version` in `SKILL.md`. New Skills must define a stable sync ID that does not change with `metadata.name`; `rename --to` is reserved for migrating legacy name-keyed registry entries and cannot change an existing stable ID.
- Use this Skill's own sync ID as `sync-skills` and its version as `0.0.3`.
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
3. Run `status` and confirm all roles report the same digest.
4. Preserve or set `metadata.version` according to the source of truth chosen for the group.

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
