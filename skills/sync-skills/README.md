# Sync Skills

Language: **English** | [中文](README.zh-CN.md)

`sync-skills` manages equivalent copies of one Agent Skill across repository, project, machine-wide, Agent-build, and explicit external locations. It also generates a machine-local relationship report for every supported AI Agent Builder and safely repairs incomplete Agent installations.

## How To Use It

Use the immutable `metadata.sync_id` declared in each `SKILL.md`, along with the paths or location roles involved and the desired operation. The Skill name is a display/trigger name and may change without changing the sync group. Common prompts include:

```text
Compare the repository and local copies of my-skill.
Link this Skill's repository copy to a specified machine-wide Skill directory.
Synchronize the project and external copies from the repository version.
```

Use the supplied script for deterministic changes:

```bash
python skills/sync-skills/scripts/skill_sync.py migrate-state
python skills/sync-skills/scripts/skill_sync.py status my-skill-id
python skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
python skills/sync-skills/scripts/skill_sync.py rename old-skill-name --to my-skill-id --name new-skill-name
python skills/sync-skills/scripts/skill_sync.py relationships
python skills/sync-skills/scripts/skill_sync.py repair-agent-install my-skill-id --agent codex --discard-local-changes
```

Runtime registry and snapshot data defaults to an XDG state directory outside the repository, isolated per checkout. Run `migrate-state` once in a checkout with legacy `.skill-sync/` data; it copies and verifies the complete tree without deleting the source and can be rerun safely. Do not remove the legacy directory until every collaborator has migrated or backed it up.

The `--to` option is for migrating a legacy name-keyed registry. For an existing stable group, keep `--to` equal to its current ID and use `--name` for display or trigger-name changes; stable IDs cannot be changed.

Each location has a role or explicit location ID. The workflow validates `SKILL.md` and its stable `metadata.sync_id`, snapshots existing copies before an overwrite, reports conflicts instead of selecting a source silently, and records versions, digests, provenance, and differences. `relationships` dynamically discovers Builders from adapter manifests and writes JSON/Markdown only to machine-local external state. See [SKILL.md](SKILL.md) for the full command set and trust rules.

## When It Triggers

Use this skill when the request:

- links, converts, synchronizes, versions, audits, compares, or rolls back Skill copies;
- involves repository, project, machine-wide user, or external copies of the same Skill; or
- needs Skill provenance URLs, version history, content digests, snapshots, or difference reports; or
- migrates legacy repository-local Skill synchronization state to machine-local storage.
- inventories local Skills, supported Builders, generated builds, and explicitly registered related projects; or
- repairs an Agent installation whose stable identity or generated files are incomplete.

## When It Does Not Trigger

Do not use this skill when the request:

- only uses a Skill for its domain workflow and does not manage its copies; or
- is ordinary code editing without Skill synchronization, conversion, auditing, or rollback.

## Exit Codes And Recovery

`link`, `link-location`, `convert`, `sync`, `rollback`, `rename`, and `repair-agent-install` return exit code **2** when the mutation succeeded but report refresh failed (`report_status: stale`). Run only the returned `report_retry_command`; do not repeat the mutation just because a shell reports nonzero. Exit code 0 means the command and refresh completed.

For the read-only `relationships --strict` command, exit code **2** instead means the freshly generated report contains findings or unlinked copies. Healthy `project-only` Skills pass, as do `synced` Skills. Without `--strict`, findings are reported in JSON without a nonzero exit code. Validation or execution errors fail separately with an error message.

Use `rollback <sync-id> --snapshot <repair-snapshot-id> --roles local` to restore an Agent repair snapshot, including installations registered only as locations. Only that installation is restored. A repeated rollback of identical content creates no new snapshot. If installation recovery fails, keep the reported staging directory and snapshot path for recovery.

The portable [contract validator](scripts/validate_skill_relationship_report.py) is the authoritative executable report contract and runs with Python's standard library. The [JSON Schema](references/skill-relationships.schema.json) is an informative interoperability document; runtime validation reads its shared status vocabulary but does not execute Draft 2020-12 constraints. The validator and schema ship inside the Skill so installed builds can generate reports independently of the repository CLI.
