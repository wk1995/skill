# Sync Model

## Logical Group

A sync group maps one logical Skill to one or more physical copies. The registry lives in `.skill-sync/registry.json` by default and stores group names, roles, absolute paths, canonical URLs, role-specific URLs, last known digests, versions, content update times, operation update times, and snapshot history.

Use stable role names:

- `repo`: copy inside the current skill-management repository.
- `local`: machine-wide user/Codex copy.
- `project`: another workspace's project-level copy.
- `external`: arbitrary copy outside the previous categories.

Additional role names are allowed only when the user explicitly needs more than one location of the same category, such as `external-docs` or `project-client-a`.

## URL Policy

Record addresses separately from local paths:

- `skill_urls`: canonical URLs for the logical Skill, such as a standalone Git repository, registry page, documentation page, package page, or upstream source.
- `role_urls`: role-specific URLs for each physical copy, such as the remote for `repo`, source page for `external`, or project repository for `project`.

Use explicit CLI values when provided:

```bash
python skills/sync-skills/scripts/skill_sync.py link my-skill --repo skills/my-skill --repo-url https://github.com/me/skills --skill-url https://github.com/me/my-skill
```

If a role URL is missing, infer it from `git remote get-url origin` for that role's path. Keep inferred URLs in member state and preserve explicit URLs in the registry.

Version history should include `skill_urls`, and digest records should include `role_urls` so a later audit can tell which version came from which repository or source address.

## Conversion Policy

Conversion means materializing a Skill copy from one role or path into another role or path, then registering both under the same logical group. Use conversion when moving a machine-wide Skill into this repository, exporting a repository Skill to a project, or adopting an external Skill into the managed set.

Before conversion:

1. Validate the source path has `SKILL.md`.
2. Refuse targets inside the source tree to avoid recursive self-copying.
3. If the target exists and contains a Skill, snapshot it before overwriting.
4. If the target exists but is not a Skill directory, stop and ask for a different target.

After conversion, run `status` and confirm matching digests.

## Version Policy

Each Skill keeps its own version in `metadata.version` inside `SKILL.md`. Prefer SemVer for normal Skills, but preserve an explicitly requested version string when the user provides one.

For this skill, use:

```yaml
metadata:
  version: "0.0.1"
```

When a group is synchronized, copy the selected source version to all targets. If target versions differ before sync, record them in the pre-sync snapshot and report the difference.

## Branch-Aware Repository/Local Policy

Use this policy for a machine-wide local Skill that is linked to this repository's Skill copy:

1. Resolve the repository role path and detect its current Git branch.
2. If the repository role is on `master` and the repository/local versions differ, synchronize from the higher version to the lower version.
3. If versions are equal, do not synchronize only because timestamps or digests differ; report status and let the user choose.
4. If the repository role is on any branch other than `master`, skip synchronization unless the user explicitly requests it with `--force`.
5. Always snapshot both copies before overwriting either one.

Use `policy-sync` for this behavior. Use plain `sync --source <role>` only when the user has explicitly chosen a source.

## Conflict Policy

Use content digests, not timestamps alone, to detect divergence. A conflict exists when multiple roles have different current digests and no explicit source role is provided.

When conflict occurs:

1. Report every role, path, version, and digest prefix.
2. Ask for or infer a source only when there is clear evidence from the user's request.
3. Snapshot all copies before resolving.
4. Prefer a three-way merge only for plain documentation changes. For scripts, assets, extension declarations, or tests, choose one source and then apply explicit edits.

## Snapshot Policy

Create snapshots before every operation that may overwrite a linked copy. A snapshot id should be UTC time in `YYYYMMDDTHHMMSSZ` form.

Store snapshots as full directory copies:

```text
.skill-sync/
|-- registry.json
`-- snapshots/
    `-- <group>/
        `-- <snapshot-id>/
            |-- manifest.json
            |-- repo/
            |-- local/
            |-- project/
            `-- external/
```

The manifest records original paths, versions, digests, source role, operation, and created time. Snapshot manifests are the stable comparison points for answering "what changed between versions?"

## Update Time Policy

Record two kinds of update time:

- `content_updated_at`: per-role timestamp derived from the newest non-ignored file in that Skill copy.
- `version_history.<version>.created_at`: first time this version was observed in the sync group.
- `version_history.<version>.updated_at`: most recent time this version was observed or synchronized.
- Operation timestamps: group-level records for actions such as `created_at`, `updated_at`, `last_sync.at`, `last_convert.at`, and `last_rollback.at`.

Use UTC ISO 8601 timestamps. Do not treat timestamps as the source of truth for equality; use digests for equality and timestamps for auditability.

When an audit time is missing, infer it in this order:

1. Existing registry value, if present.
2. Git commit time for the Skill path:
   - first commit time for group or version `created_at`;
   - latest commit time for content or version `updated_at`.
3. File modification time for non-ignored Skill files.
4. Current UTC time.

Record `content_updated_at_source` as `git` or `filesystem` for each role so later audits know how the time was derived.

## Difference Policy

Use `diff` to compare versions by snapshot or path. Report:

- added files;
- removed files;
- modified text files with unified diffs;
- modified binary files by path only.

Prefer snapshot-to-snapshot comparisons for released or historical versions. Use snapshot-to-current comparisons when reviewing uncommitted local updates before deciding which copy should become the source.

For sync operations, also record a lightweight changed-file summary under `last_sync.differences_by_role`. This summary compares each target role's pre-sync snapshot with the selected source role and records added, removed, modified text, and modified binary paths. Use the `diff` command for full line-level text diffs.

## Rollback Policy

Rollback should restore from a named snapshot to all linked roles by default. If the user asks for a partial rollback, restore only the requested roles and leave the registry showing the resulting digests.

Never delete snapshots during rollback. If rollback itself overwrites current directories, create a new pre-rollback snapshot first.

## Trust Policy

Documentation-only Skills can be copied after validation. Skills with executable content require extra inspection before copying from remote or external sources:

- `scripts/`
- `src/`
- `extensions.yaml`
- `.mcp.json`
- package manager manifests
- binaries or archives in `assets/`

Before enabling or syncing executable content from an untrusted source, report the source path, version, digest, executable entrypoints, and permissions implied by extension metadata.
