---
name: workbuddy-compat
description: Use when adding, auditing, or converting an Agent Skill so it stays compatible with both OpenAI Codex and WorkBuddy; also use to check or auto-fix the `## Platform Compatibility` section and the Codex `$<skill>` invocation examples in a Skill's READMEs.
metadata:
  version: "0.0.1"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/workbuddy-compat
  triggering:
    include:
      - The user adds a new Skill authored for OpenAI Codex that must also run in WorkBuddy.
      - The user asks to check or enforce WorkBuddy compatibility for one or all Skills in this repository.
      - The user wants to convert a Codex Skill's documentation (Platform Compatibility section, README examples) for WorkBuddy.
    exclude:
      - The user is only running a Skill's domain workflow and not its cross-tool compatibility.
      - The task is ordinary code editing unrelated to Skill portability.
---

# WorkBuddy Compatibility

## Overview

This Skill keeps every Agent Skill in the repository runnable in both OpenAI Codex and WorkBuddy. The actual logic lives in `scripts/workbuddy_compat.py`, which is the single source of truth for the two compatibility rules enforced in CI.

## Platform Compatibility

This Skill and the script it wraps are written for both OpenAI Codex and WorkBuddy.

- **Codex**: user-level skills live under `$CODEX_HOME/skills` or `~/.codex/skills`; the agent interface is `agents/openai.yaml`; Codex uses `metadata.triggering` and the `$workbuddy-compat` invocation syntax, and Codex-specific artifacts include `agents/` and `extensions.yaml`.
- **WorkBuddy**: WorkBuddy reads `SKILL.md` directly, triggers automatically from the `description` field, and ignores `agents/openai.yaml`. Its installed-Skill directory is product-configured: domestic builds commonly use `~/.workbuddy/skills`, while WorkBuddy AI/overseas builds may use `~/.workbuddy-ai/skills`. Import through WorkBuddy or use the directory configured by the installed product. No `$`-prefix is needed.

The two rules this Skill enforces are: (1) every `SKILL.md` has a `## Platform Compatibility` section, and (2) neither the `SKILL.md` body nor a README "How To Use It" / "如何使用" section teaches the Codex-only `$<skill>` invocation outside a line explicitly scoped to Codex.

## Start Here

1. To check one Skill or the whole repository, run `scripts/workbuddy_compat.py --check`.
2. To fix gaps idempotently, run `scripts/workbuddy_compat.py --fix` (or `--fix --skill skills/<name>` for one Skill).
3. Add the new Skill to CI by ensuring `.github/workflows/skill-catalog.yml` runs `tests/workbuddy-compat.sh`; the test invokes the checker and exercises its negative cases.

## Commands

Check every Skill:

```bash
python3 scripts/workbuddy_compat.py --check
```

Auto-fix every Skill:

```bash
python3 scripts/workbuddy_compat.py --fix
```

Check or fix a single Skill:

```bash
python3 scripts/workbuddy_compat.py --check --skill skills/my-skill
python3 scripts/workbuddy_compat.py --fix --skill skills/my-skill
```

## How The Check Works

For each Skill directory under `skills/`:

- It reads the `name` from `SKILL.md` frontmatter (falling back to the directory name).
- It fails the Skill if `SKILL.md` lacks a `## Platform Compatibility` section.
- It fails the Skill if the `SKILL.md` body or a README "How To Use It" / "如何使用" section teaches the `$<skill>` invocation without an explicit Codex qualifier.

## How The Fix Works

`--fix` is idempotent and never removes Codex behavior:

- It injects a generic `## Platform Compatibility` section into any `SKILL.md` that lacks one, placed as the first `## ` section.
- It rewrites README example code blocks that use the `$<skill>` invocation into natural-language prompts (converting a shell fence to a `text` fence when needed).
- It rewrites unqualified `$<skill>` references in `SKILL.md` and README prose to portable natural-language references. Explicitly Codex-scoped mentions are preserved.

README fixes are limited to the "How To Use It" / "如何使用" section, so they do not change a Chinese README's first body paragraph. `SKILL.md` fixes are limited to the agent-facing document. The bilingual root catalogs therefore stay stable unless a Skill description changes separately.

## CI Gate

`.github/workflows/skill-catalog.yml` runs `tests/workbuddy-compat.sh` on every pull request to `main`; that test exercises positive, negative, auto-fix, idempotency, annotation, and external-path cases. A new cross-tool Skill therefore cannot merge unless it is WorkBuddy-compatible.

## Notes

- WorkBuddy ignores `agents/openai.yaml`; keep that file for Codex but do not rely on it for WorkBuddy behavior.
- `metadata.triggering` is read by Codex, not WorkBuddy; WorkBuddy triggers from `description`, so keep `description` self-contained and actionable.
- The gate checks runtime portability, not WorkBuddy marketplace publication. Marketplace packages must separately follow the current [WorkBuddy Skill publishing schema](https://open.workbuddy.cn/docs/skill), including its top-level frontmatter fields.
- After `--fix` edits a Skill, re-run `python3 scripts/skill_catalog.py --write` only if a Chinese README's first paragraph changed; the example rewrite does not change it.
