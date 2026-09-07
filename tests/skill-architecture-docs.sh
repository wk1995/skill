#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
README="$ROOT/README.md"
README_ZH="$ROOT/README.zh-CN.md"
SPEC="$ROOT/docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md"
AGENT_BUILD_DOC="$ROOT/docs/agent-build-architecture.md"
AGENTS="$ROOT/AGENTS.md"
CATALOG_SCRIPT="$ROOT/scripts/skill_catalog.py"
AGENT_BUILD_SCRIPT="$ROOT/scripts/agent_build.py"
CATALOG_WORKFLOW="$ROOT/.github/workflows/skill-catalog.yml"
PR_REVIEW_GATE="$ROOT/tests/pr-review-gate.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for file in "$README" "$README_ZH" "$SPEC" "$AGENT_BUILD_DOC" "$AGENTS" "$CATALOG_SCRIPT" "$AGENT_BUILD_SCRIPT" "$CATALOG_WORKFLOW" "$PR_REVIEW_GATE"; do
  [[ -f "$file" ]] || fail "missing file: $file"
done

python3 "$CATALOG_SCRIPT" --check

PYTHONDONTWRITEBYTECODE=1 python3 - "$CATALOG_SCRIPT" <<'PY'
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

script = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("skill_catalog", script)
assert spec is not None and spec.loader is not None
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def write_fixture(skill: Path, changelog: str | None) -> None:
    skill.mkdir()
    (skill / "agent-builds").mkdir()
    (skill / "SKILL.md").write_text(
        """---
name: demo
description: Demonstrate catalog validation.
metadata:
  sync_id: "demo"
  version: "1.2.3"
  triggering:
    include: [demo]
    exclude: [unrelated]
---

# Demo
""",
        encoding="utf-8",
    )
    (skill / "README.md").write_text(
        """# Demo

[中文](README.zh-CN.md)

Intro.

## How To Use It

Use it.

## When It Triggers

For demos.

## When It Does Not Trigger

For unrelated work.
""",
        encoding="utf-8",
    )
    (skill / "README.zh-CN.md").write_text(
        """# Demo

[English](README.md)

简介。

## 如何使用

使用它。

## 何时触发

用于演示。

## 何时不触发

无关工作。
""",
        encoding="utf-8",
    )
    if changelog is not None:
        (skill / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


with tempfile.TemporaryDirectory() as raw_tmp:
    fixture_root = Path(raw_tmp).resolve()
    catalog.ROOT = fixture_root

    missing = fixture_root / "demo"
    write_fixture(missing, None)
    try:
        catalog.validate_skill(missing)
    except catalog.ValidationError as error:
        assert "missing CHANGELOG.md" in str(error)
    else:
        raise AssertionError("missing CHANGELOG.md must fail validation")

    shutil.rmtree(missing)

    mismatched = fixture_root / "demo"
    write_fixture(
        mismatched,
        """# Changelog

## [Unreleased]

## [1.2.2] - 2026-09-04

- Previous release.
""",
    )
    try:
        catalog.validate_skill(mismatched)
    except catalog.ValidationError as error:
        assert "must document current metadata.version 1.2.3 with a UTC date" in str(error)
    else:
        raise AssertionError("a mismatched CHANGELOG version must fail validation")

print("PASS: CHANGELOG negative validation cases")
PY

grep -Eq '^    name: skill-catalog$' "$CATALOG_WORKFLOW" || fail "missing skill-catalog required check name"
grep -Eq 'bash tests/pr-review-gate.sh' "$CATALOG_WORKFLOW" || fail "workflow does not run the required PR review gate"
grep -Eq 'python3 scripts/skill_catalog.py --check' "$PR_REVIEW_GATE" || fail "PR review gate does not validate generated catalogs"
grep -Eq 'scripts/pr_review_guard.py' "$PR_REVIEW_GATE" || fail "PR review gate does not inspect PR tree safety"
grep -Eq 'SKILL_CATALOG_TOKEN' "$CATALOG_WORKFLOW" || fail "workflow cannot synchronize internal PR catalogs"
grep -Eq '::error file=README.md' "$CATALOG_WORKFLOW" || fail "workflow does not annotate stale catalog errors"
grep -Eq '::error file=' "$CATALOG_SCRIPT" || fail "catalog validator does not annotate structural errors"

for skill_dir in "$ROOT"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || fail "missing SKILL.md in $skill_dir"
  [[ -f "$skill_dir/README.md" ]] || fail "missing README.md in $skill_dir"
  [[ -f "$skill_dir/README.zh-CN.md" ]] || fail "missing Chinese README in $skill_dir"
  [[ -f "$skill_dir/CHANGELOG.md" ]] || fail "missing CHANGELOG.md in $skill_dir"
  [[ -d "$skill_dir/agent-builds" ]] || fail "missing agent-builds in $skill_dir"
  [[ ! -e "$skill_dir/agents" ]] || fail "platform-specific agents directory leaked into $skill_dir"
  ! grep -Fq '## Platform Compatibility' "$skill_dir/SKILL.md" || fail "platform compatibility leaked into $skill_dir/SKILL.md"

  for section in '^## How To Use It$' '^## When It Triggers$' '^## When It Does Not Trigger$'; do
    grep -Eq "$section" "$skill_dir/README.md" || fail "missing README section $section in $skill_dir"
  done

  for section in '^## 如何使用$' '^## 何时触发$' '^## 何时不触发$'; do
    grep -Eq "$section" "$skill_dir/README.zh-CN.md" || fail "missing Chinese README section $section in $skill_dir"
  done
done

grep -Eq '## Required Structure' "$AGENTS" || fail "missing Skill structure guidance"
grep -Eq '## Required PR Review Procedure' "$AGENTS" || fail "missing required PR review procedure"
grep -Eq 'tests/pr-review-gate.sh' "$AGENTS" || fail "AGENTS.md does not require the PR review gate"
grep -Eq '`README.md`' "$AGENTS" || fail "AGENTS.md does not require README.md"
grep -Eq 'When It Triggers' "$AGENTS" || fail "AGENTS.md does not require trigger documentation"
grep -Eq 'When It Does Not Trigger' "$AGENTS" || fail "AGENTS.md does not require non-trigger documentation"
grep -Eq 'English by default' "$AGENTS" || fail "AGENTS.md does not define the default language"
grep -Eq 'README.zh-CN.md' "$AGENTS" || fail "AGENTS.md does not define Chinese README support"
grep -Eq 'metadata.sync_id' "$AGENTS" || fail "AGENTS.md does not require stable Skill sync IDs"
grep -Eq '## Agent Adapter Rules' "$AGENTS" || fail "AGENTS.md does not define Agent adapter boundaries"
grep -Fq 'platforms/<agent>/adapter.json' "$AGENTS" || fail "AGENTS.md does not define open adapter discovery"
grep -Eq 'android-code-release-train/README.md' "$README" || fail "missing android-code-release-train README link"
grep -Eq 'build-pipeline-engineering/README.md' "$README" || fail "missing build-pipeline-engineering README link"
grep -Eq 'sync-skills/README.md' "$README" || fail "missing sync-skills README link"
grep -Eq 'android-code-release-train/README.zh-CN.md' "$README_ZH" || fail "missing Chinese android-code-release-train README link"
grep -Eq 'build-pipeline-engineering/README.zh-CN.md' "$README_ZH" || fail "missing Chinese build-pipeline-engineering README link"
grep -Eq 'sync-skills/README.zh-CN.md' "$README_ZH" || fail "missing Chinese sync-skills README link"
grep -Eq 'metadata.sync_id' "$README" || fail "README.md does not document stable Skill sync IDs"

grep -Eq '^# Personal Skills$' "$README" || fail "missing English README title"
grep -Eq 'Language: \*\*English\*\* \| \[中文\]\(README.zh-CN.md\)' "$README" || fail "missing Chinese switch link in README.md"
grep -Eq '^## Current State$' "$README" || fail "missing English current-state section"
grep -Eq '^## Skill Structure And Versioning$' "$README" || fail "missing English Skill structure section"
grep -Eq '^## CLI \(Planned\)$' "$README" || fail "missing English planned CLI section"
grep -Eq '^## MCP Server \(Planned\)$' "$README" || fail "missing English planned MCP section"
grep -Eq '^## Agent Build Adapters$' "$README" || fail "missing English Agent build section"
grep -Eq '^## Codex Adapter$' "$README" || fail "missing English Codex section"

grep -Eq '^# Personal Skills$' "$README_ZH" || fail "missing Chinese README title"
grep -Eq '语言：\[English\]\(README.md\) \| \*\*中文\*\*' "$README_ZH" || fail "missing English switch link in README.zh-CN.md"
grep -Eq '^## 当前状态$' "$README_ZH" || fail "missing Chinese current-state section"
grep -Eq '^## Skill 结构与版本$' "$README_ZH" || fail "missing Chinese Skill structure section"
grep -Eq '^## CLI（规划）$' "$README_ZH" || fail "missing Chinese planned CLI section"
grep -Eq '^## MCP Server（规划）$' "$README_ZH" || fail "missing Chinese planned MCP section"
grep -Eq '^## Agent Build 适配器$' "$README_ZH" || fail "missing Chinese Agent build section"
grep -Eq '^## Codex 适配器$' "$README_ZH" || fail "missing Chinese Codex section"

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

grep -Fq 'platforms/*/adapter.json' "$AGENT_BUILD_DOC" || fail "Agent build doc does not define adapter discovery"
grep -Fq 'must not bump the portable Skill version' "$AGENT_BUILD_DOC" || fail "Agent build doc does not separate versions"
python3 "$AGENT_BUILD_SCRIPT" --check

printf 'PASS: bilingual skill architecture docs\n'
