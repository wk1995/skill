# GitHub Survey: Codex Usage Learning Skills

Surveyed on 2026-09-08. These projects were used as design references, not copied as implementation dependencies.

## Relevant Approaches

| Project | Relevant idea | Limitation for this Skill |
| --- | --- | --- |
| [mturac/everything-openai-codex](https://github.com/mturac/everything-openai-codex/tree/main/skills/continuous-learning-v2) | Project-scoped observations, confidence-aware lessons, and promotion from project to global scope. | Its hook-driven automatic observation and background learning are broader than the requested review workflow and depend on runtime-specific behavior. |
| [diegosouzapw/awesome-omni-skill](https://github.com/diegosouzapw/awesome-omni-skill/tree/main/skills/data-ai/codex-sessions-skill-scan) | Daily scans of Codex session logs for recurring Skill failures, with redaction and proposal-before-patch boundaries. | It is tied to personal paths and a particular Skill repository layout; the repository had no detected license in the GitHub metadata checked during the survey. |
| [JoernStoehler/dnd-claude-code](https://github.com/JoernStoehler/dnd-claude-code/tree/main/.agents/skills/codex-session-log) | Careful interpretation of local Codex JSONL logs and the rule that local observations are not universal product contracts. | It focuses on forensic log reading rather than a persistent improvement loop; the repository had no detected license in the GitHub metadata checked during the survey. |
| [YUHAO-corn/codex-usage-dashboard](https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard) | Local session logs as the preferred source for usage totals and a clear distinction between estimates and provider invoices. | It focuses on token and cost reporting rather than workflow learning. |
| [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit/tree/main/skills/continuous-learning) | Categorizing corrections, successes, and anti-patterns; tracking frequency and confidence; retaining rejected patterns. | It targets Claude Code conventions and can overstate confidence when lack of correction is treated as positive evidence. |

## Design Decisions

- Use Codex session metadata for a read-only baseline, but never emit raw message or tool-output content from the bundled analyzer.
- Keep durable lessons append-only and outside repositories by default.
- Require explicit user confirmation before a lesson becomes confirmed and separate confidence from authorization.
- Keep project lessons local to a project until cross-project evidence and user confirmation justify broader scope.
- Propose changes to instructions, Skills, configuration, or automations; do not apply them merely because a pattern was detected.
- Treat token counts, failures, compactions, and duration as signals that guide investigation rather than automatic diagnoses.

## Source Scope

Repository metadata, file contents, licenses, stars, and update times reflect GitHub state observed on the survey date. Re-check upstream sources before making version-sensitive or licensing claims.
