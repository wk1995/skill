# Sync Skills

Language: **English** | [中文](README.zh-CN.md)

`sync-skills` manages equivalent copies of one Agent Skill across this repository, other projects, machine-wide Agent installations, generated Agent builds, and explicit external locations. It records stable identity, provenance, versions, digests, snapshots, and audit times; compares or synchronizes copies; inventories Builder relationships; and repairs registered Agent installations from trusted builds.

## How To Use It

Run the bundled CLI from the skill-management repository:

```bash
python3 skills/sync-skills/scripts/skill_sync.py --help
```

Identify the Skill by the immutable `metadata.sync_id` in `SKILL.md`, not by its directory or display name. A managed group can contain these location roles:

| Role | Meaning |
| --- | --- |
| `repo` | Portable source in this Skill repository, usually `skills/<skill-name>` |
| `local` | A machine-wide user or Agent installation at an explicit path |
| `project` | A copy owned by another project workspace |
| `external` | Another explicit copy, such as a plugin checkout or staging directory |

Use absolute paths for locations outside this repository. Do not register a symlink, the same physical directory twice, or paths nested inside one another.

### Create or extend a sync group

Register the portable repository copy and any equivalent physical copies:

```bash
python3 skills/sync-skills/scripts/skill_sync.py link my-skill-id \
  --name my-skill \
  --repo skills/my-skill \
  --local /absolute/path/to/my-skill \
  --skill-url https://github.com/example/my-skill \
  --repo-url https://github.com/example/skills
```

Use `link-location` when one group needs an additional named project, local Agent installation, or external location:

```bash
python3 skills/sync-skills/scripts/skill_sync.py link-location my-skill-id \
  --location-id project:app-a \
  --kind project \
  --project-id app-a \
  --path /projects/app-a/skills/my-skill
```

`link` and `link-location` register relationships; they do not make divergent copies equal. Use `status` before selecting a synchronization source.

### Convert an existing copy

Use `convert` to materialize a validated source at a new location and register both locations:

```bash
python3 skills/sync-skills/scripts/skill_sync.py convert my-skill-id \
  --source-path /absolute/path/to/my-skill \
  --source-role local \
  --target-path skills/my-skill \
  --target-role repo
```

The source must contain a valid `SKILL.md`. An existing target Skill is snapshotted before replacement; a non-Skill target, overlapping path, symlink, special file, or conflicting identity is rejected.

### Inspect status, history, and differences

```bash
python3 skills/sync-skills/scripts/skill_sync.py status my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py versions my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py snapshots my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py diff my-skill-id \
  --role local \
  --from-snapshot 20260720T120000Z \
  --to-current
```

- `status` shows the registered locations, versions, digests, and divergence.
- `versions` shows observed versions and their creation/update times.
- `snapshots` lists recovery points created before mutations.
- `diff` compares snapshots, current roles, or explicit paths and reports added, removed, modified text, and modified binary files.

### Synchronize and roll back

Prefer an explicit source when copies differ:

```bash
python3 skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
```

Every existing linked copy is snapshotted before an overwrite. If more than one copy changed and no source is specified, synchronization stops and reports the conflict. On the repository's default branch, a version mismatch selects the higher `metadata.version`; on another branch, a version mismatch alone does not authorize synchronization.

Restore all registered roles, or only the named roles, from a snapshot:

```bash
python3 skills/sync-skills/scripts/skill_sync.py rollback my-skill-id \
  --snapshot 20260720T120000Z

python3 skills/sync-skills/scripts/skill_sync.py rollback my-skill-id \
  --snapshot 20260720T120000Z \
  --roles local project
```

Rollback keeps the selected snapshot and creates a new pre-rollback snapshot before replacing current content.

### Rename without changing identity

Migrate a legacy name-keyed registry by assigning its first stable sync ID:

```bash
python3 skills/sync-skills/scripts/skill_sync.py rename old-skill-name \
  --to my-skill-id \
  --name new-skill-name
```

For a group that already has a stable ID, `--to` must equal that current ID. Use `--name` to change only the display/trigger name; an existing stable sync ID cannot be replaced.

### Inventory Builder relationships

Generate the machine-local JSON and Markdown reports:

```bash
python3 skills/sync-skills/scripts/skill_sync.py relationships
python3 skills/sync-skills/scripts/skill_sync.py relationships \
  --project app-a=/projects/app-a/skills \
  --strict
```

Supported Builders come from `platforms/*/adapter.json`; the report is not limited to a hard-coded Agent list. It follows the derivation chain `portable source -> same-Agent manifest-v2 build -> local install`, includes explicitly registered projects and nested local locations, deduplicates physical paths, and reports missing builds, incomplete identities, divergence, and conflicts.

Reports default to the checkout-specific external state directory. If `--output-dir` is supplied, it must remain outside the repository and every Skill input tree. `--strict` returns exit code 2 when the new report contains findings or unlinked copies; healthy `synced` and `project-only` entries pass.

### Repair a registered Agent installation

Build the current adapter output, then repair the registered installation from its trusted manifest-v2 build:

```bash
python3 scripts/agent_build.py codex --force
python3 skills/sync-skills/scripts/skill_sync.py repair-agent-install my-skill-id \
  --agent codex
```

Repair preserves a divergent installation by default. Add `--discard-local-changes` only when replacing it is intended; the current install is still snapshotted first. Repair checks Skill identity, content, and executable file modes, refuses a different non-empty sync ID, and is idempotent when the trusted build is already installed. Use ordinary `sync` only for portable copies, never to copy portable source directly into an Agent installation.

### Migrate legacy repository state

Runtime registry, snapshots, reports, and locks belong outside the repository in a checkout-specific XDG state directory. Copy and verify legacy `.skill-sync/` state without deleting the source:

```bash
python3 skills/sync-skills/scripts/skill_sync.py migrate-state
```

The migration preserves file modes, rejects unsafe paths and differing destinations, and succeeds without changes when rerun against an identical destination. Keep `.skill-sync/` until every collaborator has migrated or backed it up and its removal is handled in a dedicated change.

See [SKILL.md](SKILL.md) for the complete operational and trust rules and [the sync model](references/sync-model.md) for identity, conflict, snapshot, version, and Agent-build policies.

## When It Triggers

Use this Skill when the request:

- links, converts, synchronizes, compares, audits, or rolls back Skill copies;
- involves repository, project, machine-wide, Agent-build, or explicit external copies of the same Skill;
- needs stable identity, provenance URLs, version history, digests, snapshots, audit times, or file differences;
- inventories local Skills, supported Builders, generated builds, Agent installations, or related projects;
- repairs an incomplete or diverged registered Agent installation; or
- migrates legacy repository-local Skill synchronization state.

## When It Does Not Trigger

Do not use this Skill when the request:

- only uses a Skill for its domain workflow and does not manage its copies or installation;
- creates or updates the behavior of one Skill without any copy-management work; or
- is ordinary application or repository work unrelated to Skill synchronization, conversion, inventory, repair, or rollback.

## Exit Codes And Recovery

`link`, `link-location`, `convert`, `sync`, `rollback`, `rename`, and `repair-agent-install` return exit code **2** when the mutation succeeded but report refresh failed (`report_status: stale`). Run only the returned `report_retry_command`; do not repeat the mutation. Exit code 0 means both the requested operation and report refresh completed.

For read-only `relationships --strict`, exit code **2** instead means the newly generated report contains findings or unlinked copies. Without `--strict`, those findings remain in the report without changing the command's exit status.

For a repair snapshot, use `rollback <sync-id> --snapshot <snapshot-id> --roles local`. If installation recovery fails, keep the reported staging directory and snapshot path. The portable [relationship-report validator](scripts/validate_skill_relationship_report.py) is the authoritative executable report contract; the [JSON Schema](references/skill-relationships.schema.json) is an informative interoperability document. Runtime validation reads the shared status vocabulary but does not execute the Draft 2020-12 constraints.
