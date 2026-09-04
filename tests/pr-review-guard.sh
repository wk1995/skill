#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
GUARD="$ROOT/scripts/pr_review_guard.py"
FIXTURE="$(mktemp -d)"

cleanup() {
  rm -rf -- "$FIXTURE"
}
trap cleanup EXIT

rejects() {
  local base_ref="$1"
  local expected="$2"
  local output
  if output="$(python3 "$GUARD" --base "$base_ref" 2>&1)"; then
    echo "FAIL: expected PR guard rejection containing: $expected" >&2
    exit 1
  fi
  [[ "$output" == *"$expected"* ]] || {
    echo "$output" >&2
    echo "FAIL: PR guard rejection did not contain: $expected" >&2
    exit 1
  }
}

cd "$FIXTURE"
git init -q -b main
git config user.name "PR Guard Test"
git config user.email "pr-guard@example.invalid"

printf '.skill-sync/\nignored.log\n' > .gitignore
printf 'base\n' > shared.txt
mkdir -p .skill-sync
printf '{"local": true}\n' > .skill-sync/registry.json
git add .gitignore shared.txt
git add -f .skill-sync/registry.json
git commit -qm "base"
BASE_COMMIT="$(git rev-parse HEAD)"

git switch -qc safe-change
printf 'safe\n' > safe.txt
git add safe.txt
git commit -qm "safe change"
python3 "$GUARD" --base "$BASE_COMMIT" >/dev/null

git switch -q --detach "$BASE_COMMIT"
git switch -qc protected-delete
rm -- .skill-sync/registry.json
git add -u .skill-sync/registry.json
git commit -qm "delete protected state"
rejects "$BASE_COMMIT" "protected .skill-sync state must have no net PR changes"

git switch -q --detach "$BASE_COMMIT"
git switch -qc ignored-addition
printf 'ignored but tracked\n' > ignored.log
git add -f ignored.log
git commit -qm "track ignored file"
rejects "$BASE_COMMIT" "tracked ignored files outside protected legacy state are not allowed"

git switch -q --detach "$BASE_COMMIT"
git switch -qc base-advanced
printf 'base advanced\n' > shared.txt
git add shared.txt
git commit -qm "advance base"
ADVANCED_BASE="$(git rev-parse HEAD)"

git switch -q --detach "$BASE_COMMIT"
git switch -qc conflicting-head
printf 'conflicting head\n' > shared.txt
git add shared.txt
git commit -qm "conflicting head"
rejects "$ADVANCED_BASE" "base and head cannot be merged cleanly"

echo "PASS: PR review guard negative and merge-simulation cases"
