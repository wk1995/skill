#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
README="$ROOT/README.md"
SPEC="$ROOT/docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for file in "$README" "$SPEC"; do
  [[ -f "$file" ]] || fail "missing file: $file"
  rg -q 'triggering:' "$file" || fail "missing triggering metadata in $file"
  rg -q 'include:' "$file" || fail "missing explicit trigger list in $file"
  rg -q 'exclude:' "$file" || fail "missing explicit non-trigger list in $file"
  rg -q '未配置 `metadata.triggering` 时等价于 `include: \[\]` 和 `exclude: \[\]`' "$file" || fail "missing default-empty trigger rule in $file"
  rg -q '`exclude` 优先于 `include`' "$file" || fail "missing trigger conflict priority in $file"
done

printf 'PASS: skill architecture trigger metadata docs\n'
