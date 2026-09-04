# WorkBuddy Compatibility

Language: **English** | [中文](README.zh-CN.md)

`workbuddy-compat` keeps every Agent Skill in this repository runnable in both OpenAI Codex and WorkBuddy. The companion script `scripts/workbuddy_compat.py` checks and auto-fixes two common compatibility gaps: a missing `## Platform Compatibility` section and unqualified Codex-only `$<skill>` invocations in `SKILL.md` or README usage examples. WorkBuddy's installed-Skill directory is product-configured rather than one universal path.

## How To Use It

Name the Skill (or say "all Skills") and the action you want. Common prompts:

```text
Check that every Skill is WorkBuddy-compatible.
Make the new Codex Skill compatible with WorkBuddy.
Fix compatibility gaps in skills/my-skill.
```

In OpenAI Codex you can also invoke the skill explicitly with `$workbuddy-compat`.

Run the script directly for deterministic output:

```bash
python3 scripts/workbuddy_compat.py --check
python3 scripts/workbuddy_compat.py --fix --skill skills/my-skill
```

See [SKILL.md](SKILL.md) for the exact rules, the injected section text, the distinction between runtime portability and marketplace publishing, and how the CI gate runs.

## When It Triggers

Use this skill when the request:

- adds a new Skill authored for OpenAI Codex that must also run in WorkBuddy;
- asks to check or enforce WorkBuddy compatibility for one or all Skills; or
- wants to convert a Codex Skill's documentation (Platform Compatibility section, README examples) for WorkBuddy.

## When It Does Not Trigger

Do not use this skill when the request:

- only runs a Skill's domain workflow and does not touch its cross-tool compatibility; or
- is ordinary code editing unrelated to Skill portability.
