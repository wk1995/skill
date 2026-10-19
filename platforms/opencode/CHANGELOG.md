# OpenCode Adapter Changelog

## [Unreleased]

## [1.0.0] - 2026-10-19

- Change-Type: initial
- Summary: Add the OpenCode (`opencode`) adapter with its own Agent ID, OpenCode global Skill roots, and generated Skill-collection artifact.
- Compatibility: New adapter; existing Codex, WorkBuddy, WorkBuddy AI, and DeepSeek Harness consumers, portable Skills, and their artifacts are unchanged.
- Stable-Contract: Discover and trigger Skills from the portable `name` and `description`; do not require Codex `$` invocation syntax or `agents/openai.yaml`; inventory the global roots `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.agents/skills` as directory bundles; compare a local install only to the same-Agent `opencode` build.
- Readiness: Checked the OpenCode V2 Skills documentation at https://opencode.ai/v2/docs/skills on 2026-10-19: global discovery sources are `~/.config/opencode/skills` plus the compatibility roots `~/.claude/skills` and `~/.agents/skills`, project sources are `.opencode/skills`, `.claude/skills`, and `.agents/skills`, and every source accepts a `<name>/SKILL.md` directory bundle or a flat `<name>.md` file. The adapter writes a plain Skill collection (`skills_path: "."`) because each generated Skill installs directly under a discovered global root, where OpenCode derives the Skill ID from the directory name; flat Markdown copies and relocated roots stay with explicit relationship-report arguments.

## [artifact 0.1.0] - 2026-10-19

- Change-Type: initial
- Summary: Initial OpenCode Skill-collection artifact.
- Compatibility: New artifact; consumers install generated Skills under an OpenCode global Skill root, not under Codex, WorkBuddy, WorkBuddy AI, or DeepSeek Harness roots.
