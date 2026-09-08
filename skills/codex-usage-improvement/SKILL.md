---
name: codex-usage-improvement
description: Analyze local Codex session logs and a user-confirmed learning journal to produce privacy-safe, evidence-backed usage retrospectives and improvement proposals. Use when the user asks to review how they use Codex, identify repeated friction or effective patterns, record a confirmed lesson, or improve future Codex workflows; do not use for token or cost accounting alone, generic code review, or silent automatic behavior changes.
metadata:
  sync_id: "codex-usage-improvement"
  version: "0.1.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/codex-usage-improvement
  triggering:
    include:
      - The user asks to review recent Codex sessions, habits, repeated friction, or effective workflows.
      - The user asks to record, confirm, reject, or revisit a lesson learned from using Codex.
      - The user wants evidence-backed recommendations for improving prompts, task scoping, tool use, or reusable Codex guidance.
    exclude:
      - The user only wants token or cost accounting without a workflow retrospective.
      - The user asks for an ordinary code review, debugging task, or one-off implementation unrelated to prior Codex usage.
      - The user asks for product-wide claims that cannot be established from local session evidence.
---

# Codex Usage Improvement

## Purpose

Turn local Codex usage into a small, reviewable feedback loop: measure recent sessions, distinguish observations from hypotheses, confirm durable lessons with the user, and propose narrowly scoped improvements.

## Workflow

1. Establish the requested time window and project scope. If they are omitted, use the last seven days and include all local Codex sessions.
2. Run the bundled script in read-only review mode:

   ```bash
   python scripts/codex_usage_improvement.py review --days 7
   python scripts/codex_usage_improvement.py review --days 30 --project-root /absolute/project/path
   ```

3. Interpret the aggregate signals together with the user's stated goals. Separate findings into:
   - observations directly supported by the report;
   - hypotheses that need transcript inspection or another session;
   - previously confirmed lessons from the learning journal.
4. When deeper diagnosis is needed, inspect only the smallest relevant log excerpts. Remove secrets, personal data, source payloads, and large tool results before quoting anything.
5. Recommend at most a few high-leverage changes. For each recommendation, state its evidence, intended scope, expected benefit, and how to tell whether it helped.
6. Record a lesson only when the user explicitly asks to remember it or confirms it as durable:

   ```bash
   python scripts/codex_usage_improvement.py record \
     --scope project \
     --project example-repo \
     --category task-scoping \
     --status confirmed \
     --lesson "Split independent research and implementation into separate tasks." \
     --evidence "session 01abc: repeated context compaction before implementation"
   ```

7. Revisit prior lessons with `list`. Reject or supersede a lesson by recording a new event with the same `--id` and the new status; the journal remains append-only.

## Evidence Rules

- Local session logs are evidence of observed behavior in one installation and time window, not a general Codex product contract.
- Counts such as failed work items, compactions, duration, and token usage are signals, not diagnoses. Explain plausible alternatives.
- Do not treat a missing user correction as proof that an approach was good.
- Do not generalize one project's convention globally without evidence from more than one project and user confirmation.
- Prefer session IDs, timestamps, event types, and aggregate counts as evidence. Do not store raw prompts, model responses, command output, source code, tokens, or credentials in the learning journal.

## Improvement Boundaries

- Review and proposal are the default. Editing `AGENTS.md`, a Skill, prompts, configuration, automation, or source code requires a user request that covers that change.
- A confidence label never grants permission to apply a change automatically.
- Keep project lessons project-scoped. Promote one to global scope only after it recurs across projects and the user confirms the broader rule.
- Prefer one reversible experiment over several simultaneous changes so later sessions can show which change helped.
- Preserve rejected and superseded journal events as history; do not rewrite the log to make earlier conclusions disappear.

## Script Contract

`scripts/codex_usage_improvement.py` has three commands:

- `review`: read Codex JSONL logs and return aggregate Markdown or JSON without emitting message or tool-output content.
- `list`: show the latest state of recorded lessons.
- `record`: append a bounded, structured lesson event to the external state directory.

By default, sessions are read from the Codex home session directory. The learning journal is stored under the operating system's XDG state location, outside repositories and Skill installations. Use `--sessions-root` or `--state-dir` only when a different explicit location is required.

For the GitHub approaches that informed this design and their limitations, read [references/github-survey.md](references/github-survey.md) only when maintaining or comparing this Skill.

## Output

Return a concise retrospective containing:

- scope and evidence window;
- notable aggregate signals and any data-quality warnings;
- repeated friction and effective patterns, each with evidence;
- candidate experiments ordered by likely impact;
- lessons recorded, rejected, or left unconfirmed;
- the next review condition, such as after five comparable sessions.
