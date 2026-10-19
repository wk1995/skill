# DeepSeek Harness Adapter Changelog

## [Unreleased]

## [1.0.0] - 2026-10-19

- Change-Type: initial
- Summary: Add the DeepSeek Harness (`dsh`) adapter with its own Agent ID, product Skill root, and generated Skill-collection artifact.
- Compatibility: New adapter; existing Codex, WorkBuddy, and WorkBuddy AI consumers, portable Skills, and their artifacts are unchanged.
- Stable-Contract: Discover and trigger Skills from the portable `name` and `description`; do not require Codex `$` invocation syntax or `agents/openai.yaml`; inventory the Harness user root `~/.dsh/skills` and the shared `~/.agents/skills` root; compare a local install only to the same-Agent `dsh` build.
- Readiness: Checked the bundled `@deepseek-ai/dsh-skill-filesystem` provider in DeepSeek Harness `0.2.0-rc.2` on 2026-10-19: user roots are `$DSH_HOME/skills` (default `~/.dsh/skills`) and `~/.agents/skills`, project roots are `<projectRoot>/.dsh/skills` and `<projectRoot>/.agents/skills`, and discovery reads one directory level containing `SKILL.md`. The adapter emits a plain Skill collection because each Skill installs directly under a discovered user root.

## [artifact 0.1.0] - 2026-10-19

- Change-Type: initial
- Summary: Initial DeepSeek Harness Skill-collection artifact.
- Compatibility: New artifact; consumers install generated Skills under the DeepSeek Harness user Skill directory, not under Codex or WorkBuddy roots.
