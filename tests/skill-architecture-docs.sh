#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
README="$ROOT/README.md"
README_ZH="$ROOT/README.zh-CN.md"
SPEC="$ROOT/docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md"
AGENTS="$ROOT/AGENTS.md"
CATALOG_SCRIPT="$ROOT/scripts/skill_catalog.py"
CATALOG_WORKFLOW="$ROOT/.github/workflows/skill-catalog.yml"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for file in "$README" "$README_ZH" "$SPEC" "$AGENTS" "$CATALOG_SCRIPT" "$CATALOG_WORKFLOW"; do
  [[ -f "$file" ]] || fail "missing file: $file"
done

python3 "$CATALOG_SCRIPT" --check

grep -Eq '^    name: skill-catalog$' "$CATALOG_WORKFLOW" || fail "missing skill-catalog required check name"
grep -Eq 'python3 scripts/skill_catalog.py --check' "$CATALOG_WORKFLOW" || fail "workflow does not validate generated catalogs"
grep -Eq 'SKILL_CATALOG_TOKEN' "$CATALOG_WORKFLOW" || fail "workflow cannot synchronize internal PR catalogs"
grep -Eq '::error file=README.md' "$CATALOG_WORKFLOW" || fail "workflow does not annotate stale catalog errors"
grep -Eq '::error file=' "$CATALOG_SCRIPT" || fail "catalog validator does not annotate structural errors"

for skill_dir in "$ROOT"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || fail "missing SKILL.md in $skill_dir"
  [[ -f "$skill_dir/README.md" ]] || fail "missing README.md in $skill_dir"
  [[ -f "$skill_dir/README.zh-CN.md" ]] || fail "missing Chinese README in $skill_dir"

  for section in '^## How To Use It$' '^## When It Triggers$' '^## When It Does Not Trigger$'; do
    grep -Eq "$section" "$skill_dir/README.md" || fail "missing README section $section in $skill_dir"
  done

  for section in '^## 如何使用$' '^## 何时触发$' '^## 何时不触发$'; do
    grep -Eq "$section" "$skill_dir/README.zh-CN.md" || fail "missing Chinese README section $section in $skill_dir"
  done
done

grep -Eq '## Required Structure' "$AGENTS" || fail "missing Skill structure guidance"
grep -Eq '`README.md`' "$AGENTS" || fail "AGENTS.md does not require README.md"
grep -Eq 'When It Triggers' "$AGENTS" || fail "AGENTS.md does not require trigger documentation"
grep -Eq 'When It Does Not Trigger' "$AGENTS" || fail "AGENTS.md does not require non-trigger documentation"
grep -Eq 'English by default' "$AGENTS" || fail "AGENTS.md does not define the default language"
grep -Eq 'README.zh-CN.md' "$AGENTS" || fail "AGENTS.md does not define Chinese README support"
grep -Eq 'android-code-release-train/README.md' "$README" || fail "missing android-code-release-train README link"
grep -Eq 'build-pipeline-engineering/README.md' "$README" || fail "missing build-pipeline-engineering README link"
grep -Eq 'sync-skills/README.md' "$README" || fail "missing sync-skills README link"
grep -Eq 'android-code-release-train/README.zh-CN.md' "$README_ZH" || fail "missing Chinese android-code-release-train README link"
grep -Eq 'build-pipeline-engineering/README.zh-CN.md' "$README_ZH" || fail "missing Chinese build-pipeline-engineering README link"
grep -Eq 'sync-skills/README.zh-CN.md' "$README_ZH" || fail "missing Chinese sync-skills README link"

grep -Eq '^# Personal Skills$' "$README" || fail "missing English README title"
grep -Eq 'Language: \*\*English\*\* \| \[中文\]\(README.zh-CN.md\)' "$README" || fail "missing Chinese switch link in README.md"
grep -Eq '^## Current State$' "$README" || fail "missing English current-state section"
grep -Eq '^## Skill Structure And Versioning$' "$README" || fail "missing English Skill structure section"
grep -Eq '^## CLI \(Planned\)$' "$README" || fail "missing English planned CLI section"
grep -Eq '^## MCP Server \(Planned\)$' "$README" || fail "missing English planned MCP section"
grep -Eq '^## Codex Adapter \(Planned\)$' "$README" || fail "missing English planned Codex section"

grep -Eq '^# Personal Skills$' "$README_ZH" || fail "missing Chinese README title"
grep -Eq '语言：\[English\]\(README.md\) \| \*\*中文\*\*' "$README_ZH" || fail "missing English switch link in README.zh-CN.md"
grep -Eq '^## 当前状态$' "$README_ZH" || fail "missing Chinese current-state section"
grep -Eq '^## Skill 结构与版本$' "$README_ZH" || fail "missing Chinese Skill structure section"
grep -Eq '^## CLI（规划）$' "$README_ZH" || fail "missing Chinese planned CLI section"
grep -Eq '^## MCP Server（规划）$' "$README_ZH" || fail "missing Chinese planned MCP section"
grep -Eq '^## Codex 适配器（规划）$' "$README_ZH" || fail "missing Chinese planned Codex section"

for file in "$README" "$README_ZH"; do
  grep -Eq 'triggering:' "$file" || fail "missing triggering metadata in $file"
  grep -Eq 'include:' "$file" || fail "missing explicit trigger list in $file"
  grep -Eq 'exclude:' "$file" || fail "missing explicit non-trigger list in $file"
  grep -Eq '`metadata.triggering`' "$file" || fail "missing trigger metadata explanation in $file"
  grep -Eq 'include: \[\]' "$file" || fail "missing default-empty include rule in $file"
  grep -Eq 'exclude: \[\]' "$file" || fail "missing default-empty exclude rule in $file"
  grep -Eq '`exclude`' "$file" || fail "missing trigger conflict priority in $file"
  grep -Eq 'skills run <skill-name> <command> \[args\]' "$file" || fail "missing custom Skill command namespace in $file"
  grep -Eq 'skills__<action>' "$file" || fail "missing management MCP namespace in $file"
  grep -Eq '<skill-name>__<tool-name>' "$file" || fail "missing Skill MCP namespace in $file"
done

printf 'PASS: bilingual skill architecture docs\n'
