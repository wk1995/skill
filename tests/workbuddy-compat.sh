#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
COMPAT_SCRIPT="$ROOT/scripts/workbuddy_compat.py"
CATALOG_WORKFLOW="$ROOT/.github/workflows/skill-catalog.yml"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[[ -f "$COMPAT_SCRIPT" ]] || fail "missing $COMPAT_SCRIPT"
[[ -f "$CATALOG_WORKFLOW" ]] || fail "missing $CATALOG_WORKFLOW"

python3 "$COMPAT_SCRIPT" --check

grep -Eq 'python3 scripts/workbuddy_compat.py --check' "$CATALOG_WORKFLOW" \
  || fail "workflow does not run the WorkBuddy compatibility gate"

printf 'PASS: all Skills are WorkBuddy-compatible and the CI gate is wired\n'
