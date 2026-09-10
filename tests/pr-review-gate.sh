#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
BASE_REF="${1:-origin/main}"

cd "$ROOT"

git rev-parse --verify "${BASE_REF}^{commit}" >/dev/null

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  echo "FAIL: pr-review-gate requires a clean worktree so committed and tested content cannot differ" >&2
  echo "::error::pr-review-gate requires a clean worktree" >&2
  exit 1
fi

echo "Reviewing committed PR tree against $BASE_REF"
git diff --name-status --find-renames "${BASE_REF}...HEAD"
python3 scripts/pr_review_guard.py --base "$BASE_REF"
python3 scripts/version_guard.py --base "$BASE_REF"
git diff --check "${BASE_REF}...HEAD"

python3 - <<'PY'
import ast
from pathlib import Path

files = sorted(Path("scripts").rglob("*.py")) + sorted(Path("skills").rglob("*.py"))
for path in files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print(f"PASS: parsed {len(files)} Python files")
PY

python3 scripts/skill_catalog.py --check

for test_script in tests/*.sh; do
  if [[ "$(basename "$test_script")" == "pr-review-gate.sh" ]]; then
    continue
  fi
  echo "Running $test_script"
  bash "$test_script"
done

echo "PASS: required PR review gate"
