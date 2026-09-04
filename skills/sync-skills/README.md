# Sync Skills

Language: **English** | [中文](README.zh-CN.md)

`sync-skills` manages equivalent copies of one Agent Skill across this repository, project directories, machine-wide Codex skill folders, and explicit external locations. It supports linking, converting, comparing, synchronizing, versioning, snapshotting, auditing, and rolling back those copies.

## How To Use It

Use the immutable `metadata.sync_id` declared in each `SKILL.md`, along with the paths or location roles involved and the desired operation. The Skill name is a display/trigger name and may change without changing the sync group. Common prompts include:

```text
Use $sync-skills to compare the repository and local copies of my-skill.
Link this skill repository copy to ~/.codex/skills/my-skill.
Synchronize the project and external copies from the repository version.
```

Use the supplied script for deterministic changes:

```bash
python skills/sync-skills/scripts/skill_sync.py status my-skill-id
python skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
python skills/sync-skills/scripts/skill_sync.py rename old-skill-name --to my-skill-id --name new-skill-name
```

Each location has a role: `repo`, `local`, `project`, or `external`. The workflow validates `SKILL.md` and its stable `metadata.sync_id`, snapshots existing copies before an overwrite, reports conflicts instead of selecting a source silently, and records versions, digests, provenance, and differences. See [SKILL.md](SKILL.md) for the full command set and trust rules.

## When It Triggers

Use this skill when the request:

- links, converts, synchronizes, versions, audits, compares, or rolls back Skill copies;
- involves repository, project, local Codex/user, or external copies of the same Skill; or
- needs Skill provenance URLs, version history, content digests, snapshots, or difference reports.

## When It Does Not Trigger

Do not use this skill when the request:

- only uses a Skill for its domain workflow and does not manage its copies; or
- is ordinary code editing without Skill synchronization, conversion, auditing, or rollback.
