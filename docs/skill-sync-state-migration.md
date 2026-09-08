# Skill Sync State Migration

This document defines the coordinated migration of machine-private `sync-skills` runtime state out of the repository. It is the implementation plan for [Issue #11](https://github.com/wk1995/skill/issues/11).

## Target State

`sync-skills` stores each checkout's registry and snapshots under:

```text
$XDG_STATE_HOME/sync-skills/<checkout-id>/
```

When `XDG_STATE_HOME` is unset, it uses:

```text
$HOME/.local/state/sync-skills/<checkout-id>/
```

The checkout ID combines the checkout directory name with a hash of its resolved absolute path. An explicit global `--state-dir` continues to override the default.

Repository-local `.skill-sync/` is legacy state. It remains protected and tracked during phase 1 so pulling the migration tooling cannot delete another checkout's registry or rollback snapshots.

## Phase 1: Copy And Verify

Every collaborator with an existing checkout must run this command from that checkout:

```bash
python3 skills/sync-skills/scripts/skill_sync.py migrate-state
```

The command:

- copies the complete legacy tree to the external default;
- verifies relative paths, file contents, sizes, and permission modes;
- preserves the legacy source without changing or deleting it;
- succeeds without rewriting data when the destination already matches;
- stops before copying if the destination differs, either path overlaps the other, or the source contains symlinks or special files.

Keep the JSON output as confirmation evidence. A successful first run reports `"status": "migrated"`; a verified repeated run reports `"status": "already-migrated"`. Both report `"source_preserved": true`.

The known legacy checkout owners are tracked in `migrations/skill-sync-state-v1.json`. Record a UTC confirmation timestamp for each owner only after that owner has successfully migrated or made an independently verified external backup.

## Phase 2: Review Backup Evidence

Each owner must provide an attributable GitHub comment or review confirming their external backup. Record its URL in `backup_evidence`, keyed by the same owner as `backup_confirmations`. Timestamps must be valid UTC and cannot be in the future. Do not invent acknowledgments or evidence URLs.

A maintainer must verify that each linked comment/review belongs to the mapped collaborator and confirms the backup. JSON keys and timestamps alone are not proof of identity. The offline guard validates the recorded form; the prior maintainer review establishes the trust boundary.

Merge an approval-only PR that records the evidence and sets `status` to `approved`. This PR must preserve `.skill-sync/`. Approval must already exist in the protected base branch before deletion is proposed.

## Phase 3: Stop Tracking

In a subsequent dedicated PR:

1. Leave the base-approved migration plan unchanged.
2. Remove the complete tracked legacy tree with `git rm -r --cached .skill-sync`.
3. Verify that `.gitignore` still ignores `.skill-sync/`.
4. Run `bash tests/pr-review-gate.sh origin/main` from a clean committed worktree.

The PR guard permits this one-time transition only when all of the following are true:

- the migration plan is read from the base, remains unchanged in the result, and its schema and identity match;
- the recorded legacy tree object matches the PR base;
- every required collaborator has a non-future UTC confirmation and a base-reviewed evidence link;
- every tracked path under `.skill-sync/` is removed, with none retained or added;
- `.skill-sync/` remains ignored in the resulting tree.

Partial deletion, stale plans, missing confirmations, malformed timestamps, and removal of the ignore rule fail closed.

## Merge Warning

> **Warning:** merging the phase 3 commit removes the old tracked `.skill-sync/` files from a checkout's working tree. Do not merge it until every collaborator has completed phase 1 or made an external backup.

Rewriting Git history to erase absolute paths from earlier commits is intentionally outside this migration. It affects every clone and must be evaluated as a separate repository-wide operation.
