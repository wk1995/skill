---
name: git-repo-sync
description: Audit and reconcile a Git clone shared across devices or teammates. Classify ahead, behind, diverged, rewritten, and upstream-gone branches; fast-forward safe branches; remove branches already contained in the default branch after archiving their tips, and delete other stale branches only when explicitly named. Use for multi-device drift, squash-merge cleanup, and stale branch audits; do not use to publish commits, resolve conflicts, or synchronize Skill copies.
metadata:
  sync_id: "git-repo-sync"
  version: "0.1.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/git-repo-sync
  triggering:
    include:
      - A clone is behind, diverged, detached, or has branches deleted or rewritten on the remote.
      - Several devices or teammates push, merge, rebase, squash-merge, or force-push to one repository.
      - Stale, merged, or abandoned local and remote branches need an audit and a safe cleanup plan.
      - A remote branch disappeared and local branches now have a missing upstream.
      - A deleted branch tip must be archived and restored later.
    exclude:
      - Publishing local commits, force-pushing history, opening pull requests, or formatting commit messages.
      - Resolving an active merge or rebase conflict, editing files, or reviewing a pull request.
      - Synchronizing Skill copies or other file trees; use the sync-skills Skill instead.
      - Bare repositories, submodules, Git LFS objects, release tags, or non-Git file synchronization.
---

# Git Repo Sync

## Overview

Use this Skill when one repository is shared by multiple devices or teammates and
the clone no longer matches the remote. The usual symptoms are stale local
branches, branches that were merged with a squash or rebase, remote branches
that no longer exist, and a local branch whose history was rewritten upstream.

The tool separates three decisions that are easy to mix up:

1. **Refresh** remote-tracking state and report drift (`audit`).
2. **Fast-forward** branches that only need the upstream commits (`sync`).
3. **Delete** branches whose content is already in the default branch (`prune`).

Nothing destructive happens without `--apply`. Bulk deletion is limited to
branches that are provably already contained in the default branch; an
unmerged branch can only be removed when the user names it and passes
`--allow-unmerged`. Every deleted tip is archived first.

## Start Here

1. Resolve the repository, remote, and default branch. The default is `origin`
   and is detected from the remote symref, local `origin/HEAD`, or `main`/
   `master`/`trunk`; pass `--remote` or `--default-branch` when detection is
   ambiguous. `--default-branch` changes which branch merge containment is
   measured against; the branch the remote actually serves as its default stays
   protected either way.
2. Run a read-only audit before proposing changes:

   ```bash
   python3 <skill-dir>/scripts/repo_sync.py audit --repo . --check-prs
   ```

3. Show the user the local and remote branch tables, the cleanup candidates,
   and every blocker. Get explicit approval before `--apply`.
4. Fast-forward safe branches. This never publishes commits and never rewrites
   history:

   ```bash
   python3 <skill-dir>/scripts/repo_sync.py sync --apply
   ```

   Use `--rebase-current` only when the user accepts replaying the current
   branch, and `--reset-rewritten` only for non-current branches whose patches
   are already upstream after a rewrite.
5. Delete merged branches, local first, then remote:

   ```bash
   python3 <skill-dir>/scripts/repo_sync.py prune --target local --apply
   python3 <skill-dir>/scripts/repo_sync.py prune --target remote --apply --check-prs
   ```

6. Re-run `audit --strict` and report the before/after state, archive refs, and
   any remaining attention items.

## Safety Rules

- `audit` never changes a branch or the worktree. It refreshes remote-tracking
  refs with `git fetch` unless `--offline` is given. `sync` and `prune` without
  `--apply` are dry runs but still fetch unless `--offline` is given.
- Every `sync` or `prune` mutation requires `--apply`; `restore` is an explicit
  branch-creation command.
- Never push commits or force-push history. `sync` only fast-forwards, rebases
  the current branch when explicitly requested, or resets a non-current branch
  whose patches are already upstream. Both rewrite paths archive the old tip.
- Bulk deletion requires proof that merging the branch into the freshly fetched
  default tip would change nothing. Tree equality detects squash merges and
  cherry-picks; a conflict or unavailable merge check counts as unmerged. Only
  an explicitly named branch with `--allow-unmerged` bypasses the content proof.
- Never delete the default branch, `main`, `master`, `develop`, `trunk`,
  `release/*`, `hotfix/*`, `gh-pages`, a branch matched by `--protect`, the
  current branch, or a branch checked out in any worktree. This holds for
  `--target local`, `--target remote`, and `--target all` alike.
- Bulk deletion of unmerged branches is impossible. `--allow-unmerged` requires
  one or more explicit `--branch` names and is intended for an abandoned branch
  the user has confirmed can be removed.
- Archive the tip under `refs/repo-sync/archive/<branch>/<sha>` before deleting
  anything. Abort if the archive cannot be created or verified.
- Delete a remote branch with
  `git push --force-with-lease=refs/heads/<branch>:<sha> --delete`. A remote
  branch that moved after the audit must be rejected, not deleted.
- A tracked worktree change blocks updating the current branch. Untracked files
  never block an `update-ref` fast-forward of a non-current branch and are
  preserved. On the current branch they are preserved too, but git refuses the
  fast-forward when it would have to overwrite one; the branch and the file are
  then left untouched and the run exits 2. Never stash, reset, or discard user
  changes automatically.
- A merge, rebase, cherry-pick, revert, or bisect in progress blocks every
  mutation. Run `audit` only.
- A shallow clone blocks cleanup unless `--allow-shallow` is given. A branch
  whose commit is missing locally is never deleted.
- A branch with no common ancestor with the default branch, such as an orphan
  `gh-pages` or a branch in a depth-limited shallow clone, is reported as
  `unrelated` and treated as unmerged. It never blocks `audit`, and it is only
  deleted when it is named with `--branch` and `--allow-unmerged`.
- `--check-prs` is fail closed: if `gh` is missing, unauthenticated, or returns
  an error, no deletion happens.
- Never delete a branch that has an open pull request when `--check-prs` was
  requested.
- Archives are local refs. They are not pushed by this tool; a `git push
  --mirror` would publish them. If an archive must outlive the clone, create a
  tag and push it explicitly.

## Branch States

| State | Meaning | Default action |
| --- | --- | --- |
| `up-to-date` | Local and upstream point at the same commit. | None |
| `behind` | Local is an ancestor of upstream. | Fast-forward |
| `ahead` | Local has commits that are not upstream. | Report only; publishing is separate |
| `diverged` | Both sides have unique commits. | Stop; `--rebase-current` or manual resolution |
| `rewritten-upstream` | Both sides differ, but every local patch already exists upstream. | `--reset-rewritten` (non-current) or `--rebase-current` |
| `upstream-gone` | The configured upstream branch no longer exists. | Archive and prune locally, or re-publish |
| `unpublished` | No upstream is configured. | Report only |
| `foreign-upstream` | Upstream belongs to another remote. | Report only; run the tool against that remote |

Merge classification is separate from tracking status:

| Merge state | Meaning |
| --- | --- |
| `ancestor` | The tip is already in the default branch. |
| `noop` | Merging would reproduce the default tree; covers squash merges and cherry-picks. |
| `changes` | Merging would add content; the branch is unmerged. |
| `conflict` | Merging conflicts; never deleted automatically. |
| `unrelated` | No common ancestor with the default branch, such as an orphan `gh-pages`; treated as unmerged. |
| `unavailable` | The merge check cannot run; treated as unmerged. |

## Commands

All commands accept `--repo`, `--remote`, `--default-branch`, `--offline`,
`--json`, and repeatable `--protect <glob>`. Options follow the subcommand.

### audit

```bash
python3 <skill-dir>/scripts/repo_sync.py audit --repo . --stale-days 90 --check-prs
```

- `--stale-days N` marks branches whose tip commit is at least `N` days old.
- `--strict` exits 2 when findings exist, without changing anything.
- `--offline` uses existing refs and skips network access; treat the result as a
  snapshot of the last fetch.

### sync

```bash
python3 <skill-dir>/scripts/repo_sync.py sync
python3 <skill-dir>/scripts/repo_sync.py sync --apply
python3 <skill-dir>/scripts/repo_sync.py sync --apply --rebase-current
python3 <skill-dir>/scripts/repo_sync.py sync --apply --reset-rewritten
```

- Fast-forwards the default branch first, then the other local branches.
- Updates a non-current branch with an atomic compare-and-swap; a branch checked
  out in another worktree is skipped.
- `--rebase-current` replays the current branch on its upstream, aborts on
  conflict, and leaves the original branch restored. The old tip stays archived.
- `--reset-rewritten` moves a non-current branch to upstream only when all its
  patches are already upstream.
- Dry-run output exits 0 even when it reports blocked branches; inspect the JSON
  `actions` array. `--apply` exits 2 when anything remains blocked or failed.

### prune

```bash
python3 <skill-dir>/scripts/repo_sync.py prune --target local --apply
python3 <skill-dir>/scripts/repo_sync.py prune --target remote --apply --check-prs
python3 <skill-dir>/scripts/repo_sync.py prune --target all --stale-days 180 --apply
python3 <skill-dir>/scripts/repo_sync.py prune --target local --gone --apply
python3 <skill-dir>/scripts/repo_sync.py prune --target local --branch experiment --allow-unmerged --apply
```

- Default target is `local`; default selector is `--merged`. The default branch
  and other protected branches are excluded from bulk selection.
- `--gone` selects local branches whose upstream disappeared. Only the ones
  already contained in the default branch are deleted in bulk.
- `--stale-days N` selects branches older than `N` days. Unmerged stale branches
  are reported as skipped; they are never bulk-deleted.
- `--branch` names an exact branch. Naming a branch does not authorize an
  unmerged deletion; add `--allow-unmerged` for that.
- `--strict` makes a dry run exit 2 when it has deletion candidates.
- Exit 2 after `--apply` means an explicitly named branch was skipped or a
  deletion failed. A bulk plan that only skips branches still exits 0; the skip
  reasons, including `open pull request`, are in the output.

### archive and restore

```bash
python3 <skill-dir>/scripts/repo_sync.py archive list --repo .
python3 <skill-dir>/scripts/repo_sync.py restore feature/old --repo .
python3 <skill-dir>/scripts/repo_sync.py restore refs/repo-sync/archive/feature/old/<sha> --branch recovered
```

`restore` refuses to overwrite an existing branch. When several archives exist
for one name, it chooses the newest tip by commit date.

## Team Workflow

- One owner deletes merged remote branches, after `--check-prs`, so two people
  do not prune the same branch. Teammates run `sync --apply`; it prunes their
  stale remote-tracking refs and reports upstream-gone branches.
- Run `audit` before switching devices and `sync --apply` after returning. This
  is how a device learns that its branch was merged, squashed, rebased, or
  deleted elsewhere.
- After an upstream rebase or force-push, `audit` reports
  `rewritten-upstream` instead of silently treating the local branch as ahead.
  Never push the stale commits back; reset or rebase after confirming that no
  local patch is unique.
- Squash-merged branches stay visible to `git branch --merged` as unmerged. The
  merge-tree check removes them safely without deleting a branch whose changes
  were later reverted.
- Deleting a remote branch archives its tip only in the clone that ran the
  command. Create and push a tag when the archive must be shared.

## Output And Exit Codes

`audit --json` returns one object with `schema`, `repo`, `fetch`,
`stale_tracking`, `local_branches`, `remote_branches`, `summary`, and
`findings`. `sync --json` returns `actions` and a post-run `summary`. `prune
--json` returns `plan` (dry run) or `deleted`, `skipped`, `failed`, and
`archives` (apply).

Exit codes:

- **0**: completed with nothing requiring attention.
- **1**: could not run (not a Git worktree, no remote, missing commit, fetch
  failure, invalid archive reference).
- **2**: a safety rule refused the request; `prune` skipped an explicitly named
  branch, could not resolve a name, or failed to delete; or `sync --apply` left
  a branch blocked or failed. A bulk plan that only skips branches, including
  branches held by an open pull request, still exits 0. Nothing was partially
  deleted without being reported.

## Limitations

- Merge detection uses `git merge-tree --write-tree` (Git 2.38+). On older Git,
  only the ancestor check runs and squash-merged branches are treated as
  unmerged, which is safe but less effective.
- `--check-prs` needs the GitHub CLI and a GitHub remote. Other hosts are
  audited without PR state; do not delete remote branches without another way
  to confirm no review is open. The check also fails closed when the open-PR
  list reaches its 1000-entry limit.
- Tags, submodules, Git LFS objects, and release assets are out of scope.
- Archives are ordinary refs. Delete them explicitly with
  `git update-ref -d <ref>` when they are no longer needed.
