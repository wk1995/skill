# WorkBuddy AI Adapter Changelog

## [Unreleased]

- No unreleased changes.

## [1.0.0] - 2026-09-17

- Change-Type: initial
- Summary: Add the international WorkBuddy AI adapter with its own Agent ID and China-independent local Skill root.
- Compatibility: New adapter; existing `workbuddy` (China) consumers, portable Skills, and Codex builds are unchanged.
- Stable-Contract: Discover and trigger Skills from portable `name` and `description`; do not require Codex `$` invocation syntax or `agents/openai.yaml`; inventory the international product Skill directory `~/.workbuddy-ai/skills`; compare a local install only to the same-Agent `workbuddy-ai` build.
- Readiness: Uses the generic builder and the same Skill-collection layout as WorkBuddy; local root matches WorkBuddy AI.app `dataFolderName` `.workbuddy-ai` as checked on 2026-09-17.

## [artifact 0.1.0] - 2026-09-17

- Change-Type: initial
- Summary: Initial international WorkBuddy AI Skill-collection artifact.
- Compatibility: New artifact; consumers install generated Skills under the WorkBuddy AI product Skill directory, not under the China WorkBuddy adapter.
