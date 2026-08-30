# Sync Skills

Language: **English** | [中文](README.zh-CN.md)

`sync-skills` manages equivalent copies of one Agent Skill across this repository, project directories, machine-wide Codex/ZCode skill folders, and explicit external locations. It supports linking, converting, comparing, synchronizing, versioning, snapshotting, auditing, and rolling back those copies.

## How To Use It

Name the logical skill, the paths or location roles involved, and the desired operation. Common prompts include:

```text
Use $sync-skills to compare the repository and local copies of my-skill.
Link this skill repository copy to ~/.codex/skills/my-skill.
Synchronize the project and external copies from the repository version.
```

Use the supplied script for deterministic changes:

```bash
python skills/sync-skills/scripts/skill_sync.py status my-skill
python skills/sync-skills/scripts/skill_sync.py sync my-skill --source repo
```

Before or after importing a Skill from another runtime, verify that it is ZCode-compatible — linked group roles, a single skill directory, or a whole folder of skills all work, and `link`, `convert`, and `sync` print the same findings as a warning whenever a linked or source copy is incompatible:

```bash
python skills/sync-skills/scripts/skill_sync.py check --path ~/.codex/skills
```

Each location has a role: `repo`, `local`, `project`, or `external`. The workflow validates `SKILL.md`, snapshots existing copies before an overwrite, reports conflicts instead of selecting a source silently, and records versions, digests, provenance, and differences. See [SKILL.md](SKILL.md) for the full command set and trust rules.

ZCode copies follow the same role model: link or sync them under `~/.zcode/skills/` (user scope) or `~/.agents/skills/` (shared across tools), with `SKILL.md` as the only required file — `agents/openai.yaml` and `extensions.yaml` are Codex-only and ignored by ZCode.

## When It Triggers

Use this skill when the request:

- links, converts, synchronizes, versions, audits, compares, or rolls back Skill copies;
- involves repository, project, local Codex/ZCode/user, or external copies of the same Skill; or
- needs Skill provenance URLs, version history, content digests, snapshots, or difference reports.

## When It Does Not Trigger

Do not use this skill when the request:

- only uses a Skill for its domain workflow and does not manage its copies; or
- is ordinary code editing without Skill synchronization, conversion, auditing, or rollback.
