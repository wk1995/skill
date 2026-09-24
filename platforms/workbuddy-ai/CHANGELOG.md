# WorkBuddy AI Adapter Changelog

## [Unreleased]

## [artifact 0.2.0] - 2026-09-24

- Change-Type: feature
- Summary: Bundle the updated PR review workflow and Skill sync rules while excluding local review policy files.
- Compatibility: Existing installed Skills retain their supported usage; the optional private project policy is an additional input.

## [1.0.1] - 2026-09-24

- Change-Type: fix
- Summary: Keep ignored PR review project policy files out of WorkBuddy AI build inputs and digests.
- Compatibility: Existing adapter discovery and generated file layout remain unchanged.

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
