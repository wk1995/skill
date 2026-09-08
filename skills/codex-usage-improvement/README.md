# Codex Usage Improvement

Language: **English** | [中文](README.zh-CN.md)

`codex-usage-improvement` turns local Codex session metadata and user-confirmed lessons into privacy-conscious retrospectives. It helps identify repeated friction, preserve useful practices, and test small workflow improvements without silently changing Codex configuration or project instructions.

## How To Use It

Ask for a time-bounded review, optionally limited to one project. You can also ask to save or revisit a lesson after reviewing the evidence.

```text
Review my Codex usage from the last seven days and suggest two improvements.
Analyze recent Codex sessions for this repository and find repeated friction.
Record this as a project lesson, then show the currently confirmed lessons.
```

The bundled script can produce a metadata-only report or manage the append-only learning journal:

```bash
python scripts/codex_usage_improvement.py review --days 7
python scripts/codex_usage_improvement.py review --days 30 --project-root /absolute/project/path
python scripts/codex_usage_improvement.py list --status confirmed
```

The default journal lives in the external XDG state directory rather than in a repository. See [SKILL.md](SKILL.md) for the evidence, privacy, and mutation boundaries.

## When It Triggers

Use this Skill when a user wants to:

- review how they have used Codex across recent sessions;
- find recurring tool failures, context pressure, task-scoping problems, or effective habits;
- record, confirm, reject, or supersede an evidence-backed lesson; or
- design a small experiment to improve future Codex work.

## When It Does Not Trigger

Do not use this Skill when the request is only for token or cost accounting, an ordinary code review or debugging task, or a general claim about Codex behavior that local session logs cannot establish. It also does not silently modify project instructions, Skills, configuration, or automations.
