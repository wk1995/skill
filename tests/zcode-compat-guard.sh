#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SYNC="$ROOT/skills/sync-skills/scripts/skill_sync.py"
CATALOG_SCRIPT="$ROOT/scripts/skill_catalog.py"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

expect_incompatible() {
  local dir="$1" message="$2"
  set +e
  python3 "$SYNC" check --path "$dir" >/dev/null 2>&1
  local status=$?
  set -e
  [[ "$status" -eq 2 ]] || fail "$message should be reported as ZCode-incompatible (exit 2), got $status"
}

# Every repository Skill must pass the standalone compatibility check.
for skill_dir in "$ROOT"/skills/*/; do
  python3 "$SYNC" check --path "${skill_dir%/}" >/dev/null || fail "repository skill failed the ZCode compatibility check: $skill_dir"
done

TMP="$(mktemp -d)"
trap 'chmod -R u+rwx "$TMP" 2>/dev/null || true; rm -rf "$TMP"' EXIT

make_skill() {
  local dir="$TMP/$1"
  mkdir -p "$dir"
  cat > "$dir/SKILL.md"
}

make_skill no-when-to-use <<'MD'
---
name: no-when-to-use
description: A skill without a top-level when_to_use line.
metadata:
  version: "0.0.1"
---

# No When To Use

Body.
MD

make_skill nested-when-to-use <<'MD'
---
name: nested-when-to-use
description: A skill whose when_to_use is nested under metadata.
metadata:
  version: "0.0.1"
  when_to_use: nested value
---

# Nested When To Use

Body.
MD

make_skill missing-description <<'MD'
---
name: missing-description
when_to_use: A trigger line.
metadata:
  version: "0.0.1"
---

# Missing Description

Body.
MD

mkdir -p "$TMP/long-description"
{
  printf -- '---\nname: long-description\ndescription: '
  printf 'x%.0s' {1..1100}
  printf '\nwhen_to_use: A trigger line.\nmetadata:\n  version: "0.0.1"\n---\n\n# Long Description\n\nBody.\n'
} > "$TMP/long-description/SKILL.md"

expect_incompatible "$TMP/no-when-to-use" "missing when_to_use"
expect_incompatible "$TMP/nested-when-to-use" "nested when_to_use"
expect_incompatible "$TMP/missing-description" "missing description"
expect_incompatible "$TMP/long-description" "over-long description"

# A folder of skills is checked as a batch.
mkdir -p "$TMP/folder"
cp -R "$TMP/no-when-to-use" "$TMP/missing-description" "$TMP/folder/"
set +e
python3 "$SYNC" check --path "$TMP/folder" >"$TMP/folder.json"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "folder check should exit 2, got $status"
grep -q '"no-when-to-use"' "$TMP/folder.json" || fail "folder check did not report no-when-to-use"
grep -q '"missing-description"' "$TMP/folder.json" || fail "folder check did not report missing-description"

# link, convert, and sync warn about incompatible copies without failing.
python3 "$SYNC" --state-dir "$TMP/state" link demo --local "$TMP/no-when-to-use" >/dev/null 2>"$TMP/link.err"
grep -q "not ZCode-compatible" "$TMP/link.err" || fail "link did not warn about the incompatible copy"

python3 "$SYNC" --state-dir "$TMP/state" convert demo --source-path "$TMP/no-when-to-use" --target-path "$TMP/converted/demo" --source-role local --target-role project >/dev/null 2>"$TMP/convert.err"
grep -q "not ZCode-compatible" "$TMP/convert.err" || fail "convert did not warn about the incompatible source"

python3 "$SYNC" --state-dir "$TMP/state" sync demo --source local >/dev/null 2>"$TMP/sync.err"
grep -q "not ZCode-compatible" "$TMP/sync.err" || fail "sync did not warn about the incompatible source"

# Registry mode: check <group> reports every linked role.
set +e
python3 "$SYNC" --state-dir "$TMP/state" check demo >"$TMP/group.json"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "group check should exit 2, got $status"
grep -q '"local"' "$TMP/group.json" || fail "group check did not report the local role"
grep -q '"zcode_compatible": false' "$TMP/group.json" || fail "group check did not mark a role incompatible"

# --path and a group name cannot be combined.
set +e
python3 "$SYNC" --state-dir "$TMP/state" check demo --path "$TMP/no-when-to-use" >/dev/null 2>&1
status=$?
set -e
[[ "$status" -ne 0 ]] || fail "check should reject --path combined with a group name"

# One unreadable skill must not abort the batch scan, and an unreadable child
# directory must be reported as incompatible instead of silently skipped.
mkdir -p "$TMP/folder/broken-skill"
printf 'name: gbk\n' > "$TMP/folder/broken-skill/SKILL.md"  # readable, but no frontmatter markers
mkdir -p "$TMP/folder/unreadable-skill"
printf '\xff\xfe\x00g\x00b\x00k\x00' > "$TMP/folder/unreadable-skill/SKILL.md"
mkdir -p "$TMP/folder/locked-skill"
printf -- '---\nname: locked-skill\n---\n' > "$TMP/folder/locked-skill/SKILL.md"
chmod 000 "$TMP/folder/locked-skill"
set +e
python3 "$SYNC" check --path "$TMP/folder" >"$TMP/batch.json"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "batch scan with an unreadable skill should exit 2, got $status"
grep -q '"unreadable-skill"' "$TMP/batch.json" || fail "batch scan did not report the unreadable skill"
grep -q '"broken-skill"' "$TMP/batch.json" || fail "batch scan did not continue past the unreadable skill"
grep -q '"locked-skill"' "$TMP/batch.json" || fail "batch scan silently skipped the unreadable child directory"
chmod 700 "$TMP/folder/locked-skill"

# The catalog validator also rejects over-long descriptions (ZCode drops them).
python3 - "$CATALOG_SCRIPT" "$ROOT" <<'PY'
import importlib.util
import shutil
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("skill_catalog", sys.argv[1])
skill_catalog = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(skill_catalog)

root = Path(sys.argv[2])
guard_dir = root / ".tmp-zcode-guard"
skill_dir = guard_dir / "long-description"
skill_dir.mkdir(parents=True)
try:
    (skill_dir / "SKILL.md").write_text(
        "---\nname: long-description\ndescription: " + "x" * 1100 + '\nwhen_to_use: A trigger line.\nmetadata:\n  version: "0.0.1"\n---\n\n# Long Description\n\nBody.\n',
        encoding="utf-8",
    )
    (skill_dir / "README.md").write_text(
        "# Long Description\n\nLanguage: **English** | [中文](README.zh-CN.md)\n\nIntro.\n\n## How To Use It\nx\n\n## When It Triggers\nx\n\n## When It Does Not Trigger\nx\n",
        encoding="utf-8",
    )
    (skill_dir / "README.zh-CN.md").write_text(
        "# 超长描述\n\n语言：[English](README.md) | **中文**\n\n简介。\n\n## 如何使用\nx\n\n## 何时触发\nx\n\n## 何时不触发\nx\n",
        encoding="utf-8",
    )
    try:
        skill_catalog.validate_skill(skill_dir)
    except skill_catalog.ValidationError as error:
        assert "1024" in str(error), f"unexpected error: {error}"
    else:
        raise AssertionError("over-long description should fail catalog validation")
finally:
    shutil.rmtree(guard_dir)
print("PASS: catalog rejects over-long descriptions")
PY

printf 'PASS: ZCode compatibility guards\n'
