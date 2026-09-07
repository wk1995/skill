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
mkdir -p .skill-sync/snapshots/demo
printf '{"local": true}\n' > .skill-sync/registry.json
printf 'snapshot\n' > .skill-sync/snapshots/demo/state.txt
git add .gitignore shared.txt
git add -f .skill-sync/registry.json .skill-sync/snapshots/demo/state.txt
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
git switch -qc ignore-rule-base
printf 'ignored-by-base.log\n' >> .gitignore
git add .gitignore
git commit -qm "base adds ignore rule"
IGNORE_RULE_BASE="$(git rev-parse HEAD)"

git switch -q --detach "$BASE_COMMIT"
git switch -qc ignored-via-base
printf 'tracked by pull request\n' > ignored-by-base.log
git add ignored-by-base.log
git commit -qm "track file ignored by advanced base"
rejects "$IGNORE_RULE_BASE" "tracked ignored files outside protected legacy state are not allowed"

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

git switch -q --detach "$BASE_COMMIT"
git switch -qc migration-plan
mkdir -p migrations
STATE_TREE="$(git rev-parse HEAD:.skill-sync)"
python3 - migrations/skill-sync-state-v1.json "$STATE_TREE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(json.dumps({
    "backup_confirmations": {},
    "expected_base_tree": sys.argv[2],
    "legacy_path": ".skill-sync",
    "migration": "skill-sync-xdg-state-v1",
    "required_backup_confirmations": ["alice", "bob"],
    "schema_version": 1,
    "status": "awaiting-backups",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
git add migrations/skill-sync-state-v1.json
git commit -qm "add pending migration plan"
MIGRATION_BASE="$(git rev-parse HEAD)"

approve_migration() {
  python3 - migrations/skill-sync-state-v1.json <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plan = json.loads(path.read_text(encoding="utf-8"))
plan["backup_confirmations"] = {
    "alice": "2026-09-07T01:02:03Z",
    "bob": "2026-09-07T02:03:04Z",
}
plan["status"] = "approved"
path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-pending
git rm -qr .skill-sync
git commit -qm "remove state without confirmations"
rejects "$MIGRATION_BASE" "migration plan is not approved"

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-partial
approve_migration
git rm -q .skill-sync/registry.json
git add migrations/skill-sync-state-v1.json
git commit -qm "partially remove protected state"
rejects "$MIGRATION_BASE" "remove the complete legacy state tree"

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-stale
approve_migration
python3 - migrations/skill-sync-state-v1.json <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plan = json.loads(path.read_text(encoding="utf-8"))
plan["expected_base_tree"] = "0000000000000000000000000000000000000000"
path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
git rm -qr .skill-sync
git add migrations/skill-sync-state-v1.json
git commit -qm "remove protected state from stale baseline"
rejects "$MIGRATION_BASE" "does not match the reviewed migration baseline"

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-invalid-confirmation
approve_migration
python3 - migrations/skill-sync-state-v1.json <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plan = json.loads(path.read_text(encoding="utf-8"))
plan["backup_confirmations"]["bob"] = "2026-99-99T99:99:99Z"
path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
git rm -qr .skill-sync
git add migrations/skill-sync-state-v1.json
git commit -qm "remove protected state with malformed confirmation"
rejects "$MIGRATION_BASE" "must contain UTC timestamps"

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-not-ignored
approve_migration
git rm -qr .skill-sync
printf '.skill-sync/registry.json\n' > .gitignore
git add .gitignore migrations/skill-sync-state-v1.json
git commit -qm "remove protected state without ignore rule"
rejects "$MIGRATION_BASE" "must remain ignored after migration"

git switch -q --detach "$MIGRATION_BASE"
git switch -qc migration-approved
approve_migration
git rm -qr .skill-sync
git add migrations/skill-sync-state-v1.json
git commit -qm "remove protected state after backups"
python3 "$GUARD" --base "$MIGRATION_BASE" >/dev/null
MIGRATED_HEAD="$(git rev-parse HEAD)"

git switch -q --detach "$MIGRATED_HEAD"
git switch -qc migration-follow-up
printf 'after migration\n' > after.txt
git add after.txt
git commit -qm "safe change after migration"
python3 "$GUARD" --base "$MIGRATED_HEAD" >/dev/null

echo "PASS: PR review guard negative, merge-simulation, and approved migration cases"
