#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
README="$ROOT/README.md"
README_ZH="$ROOT/README.zh-CN.md"
SPEC="$ROOT/docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md"
AGENTS="$ROOT/AGENTS.md"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for file in "$README" "$README_ZH" "$SPEC" "$AGENTS"; do
  [[ -f "$file" ]] || fail "missing file: $file"
done

for skill_dir in "$ROOT"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || fail "missing SKILL.md in $skill_dir"
  [[ -f "$skill_dir/README.md" ]] || fail "missing README.md in $skill_dir"
  [[ -f "$skill_dir/README.zh-CN.md" ]] || fail "missing Chinese README in $skill_dir"

  for section in '^## How To Use It$' '^## When It Triggers$' '^## When It Does Not Trigger$'; do
    rg -q "$section" "$skill_dir/README.md" || fail "missing README section $section in $skill_dir"
  done

  for section in '^## 如何使用$' '^## 何时触发$' '^## 何时不触发$'; do
    rg -q "$section" "$skill_dir/README.zh-CN.md" || fail "missing Chinese README section $section in $skill_dir"
  done
done

rg -q '## Required Structure' "$AGENTS" || fail "missing Skill structure guidance"
rg -q '`README.md`' "$AGENTS" || fail "AGENTS.md does not require README.md"
rg -q 'When It Triggers' "$AGENTS" || fail "AGENTS.md does not require trigger documentation"
rg -q 'When It Does Not Trigger' "$AGENTS" || fail "AGENTS.md does not require non-trigger documentation"
rg -q 'English by default' "$AGENTS" || fail "AGENTS.md does not define the default language"
rg -q 'README.zh-CN.md' "$AGENTS" || fail "AGENTS.md does not define Chinese README support"
rg -q 'release-engineering/README.md' "$README" || fail "missing release-engineering README link"
rg -q 'sync-skills/README.md' "$README" || fail "missing sync-skills README link"

rg -q '^# Personal Skills$' "$README" || fail "missing English README title"
rg -q 'Language: \*\*English\*\* \| \[中文\]\(README.zh-CN.md\)' "$README" || fail "missing Chinese switch link in README.md"
rg -q '^## Current State$' "$README" || fail "missing English current-state section"
rg -q '^## Skill Structure And Versioning$' "$README" || fail "missing English Skill structure section"
rg -q '^## CLI \(Planned\)$' "$README" || fail "missing English planned CLI section"
rg -q '^## MCP Server \(Planned\)$' "$README" || fail "missing English planned MCP section"
rg -q '^## Codex Adapter \(Planned\)$' "$README" || fail "missing English planned Codex section"

rg -q '^# Personal Skills$' "$README_ZH" || fail "missing Chinese README title"
rg -q '语言：\[English\]\(README.md\) \| \*\*中文\*\*' "$README_ZH" || fail "missing English switch link in README.zh-CN.md"
rg -q '^## 当前状态$' "$README_ZH" || fail "missing Chinese current-state section"
rg -q '^## Skill 结构与版本$' "$README_ZH" || fail "missing Chinese Skill structure section"
rg -q '^## CLI（规划）$' "$README_ZH" || fail "missing Chinese planned CLI section"
rg -q '^## MCP Server（规划）$' "$README_ZH" || fail "missing Chinese planned MCP section"
rg -q '^## Codex 适配器（规划）$' "$README_ZH" || fail "missing Chinese planned Codex section"

for file in "$README" "$README_ZH"; do
  rg -q 'triggering:' "$file" || fail "missing triggering metadata in $file"
  rg -q 'include:' "$file" || fail "missing explicit trigger list in $file"
  rg -q 'exclude:' "$file" || fail "missing explicit non-trigger list in $file"
  rg -q '`metadata.triggering`' "$file" || fail "missing trigger metadata explanation in $file"
  rg -q 'include: \[\]' "$file" || fail "missing default-empty include rule in $file"
  rg -q 'exclude: \[\]' "$file" || fail "missing default-empty exclude rule in $file"
  rg -q '`exclude`' "$file" || fail "missing trigger conflict priority in $file"
  rg -q 'skills run <skill-name> <command> \[args\]' "$file" || fail "missing custom Skill command namespace in $file"
  rg -q 'skills__<action>' "$file" || fail "missing management MCP namespace in $file"
  rg -q '<skill-name>__<tool-name>' "$file" || fail "missing Skill MCP namespace in $file"
done

printf 'PASS: bilingual skill architecture docs\n'
