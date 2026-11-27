# Git Repo Sync

Language: **English** | [简体中文](README.zh-CN.md)

Audit and reconcile a Git clone that is shared across devices or teammates.
Classify ahead, behind, diverged, rewritten, and upstream-gone branches;
fast-forward safe branches; and remove branches already contained in the
default branch only after archiving their tips. Unmerged stale branches are
reported for review and are deleted only when explicitly named. Use it for
multi-device drift, squash-merge cleanup, and stale branch audits. It does not
publish commits, resolve conflicts, or synchronize Skill copies.

A repository with several devices or contributors accumulates drift quickly:
one device merges a feature, another rebases it, a third force-pushes after a
review, and branches are left behind on the remote and in every clone. `git
fetch` alone does not tell you which branches are safe to remove. This Skill
separates reading the state, fast-forwarding what is merely behind, and deleting
what is provably already in the default branch.

## How To Use It

Ask your agent: “Audit this clone against origin, show me stale and merged
branches, then fast-forward what is safe. Do not delete anything until I
confirm.” Or run the commands directly.

Start with a read-only audit. It fetches remote-tracking refs, classifies every
local branch, and reports cleanup candidates and blockers:

```sh
python3 <skill-dir>/scripts/repo_sync.py audit --repo . --check-prs
```

Fast-forward only. This never pushes a commit and never rewrites history:

```sh
python3 <skill-dir>/scripts/repo_sync.py sync --apply
```

Delete merged branches. The default is a dry run; `--apply` archives each tip
under `refs/repo-sync/archive/` before deleting it:

```sh
python3 <skill-dir>/scripts/repo_sync.py prune --target local --apply
python3 <skill-dir>/scripts/repo_sync.py prune --target remote --apply --check-prs
```

Recover a deleted branch:

```sh
python3 <skill-dir>/scripts/repo_sync.py archive list --repo .
python3 <skill-dir>/scripts/repo_sync.py restore feature/old --repo . --branch feature/old
```

Typical audit output:

```text
Local branches (4)
  main          up-to-date    merged        [current, protected]
  feature/a     behind 2      merged
  feature/b     diverged      unmerged
  old/c         upstream gone merged

Remote branches (7)
  feature/a     12d  merged (squash)
  feature/b      3d  unmerged

Cleanup candidates (merged, unprotected, no uncommitted work)
  local   feature/a
  remote  feature/a
```

`--json` returns the same information for scripts. See [SKILL.md](SKILL.md) for
the complete state model, safety boundaries, command flags, and exit codes.

### Why a merge-tree check

`git branch --merged` misses squash merges and cherry-picks, which are common on
GitHub. The tool checks whether merging a branch into the freshly fetched
default branch would change the tree. If the result is identical, the branch has
nothing left to contribute and is safe to archive and delete. If merging would
add or conflict with content, the branch is left untouched. A branch with no
common ancestor with the default branch, such as an orphan `gh-pages`, cannot be
merged at all; it is reported as unmerged and left untouched instead of aborting
the audit.

### What is never deleted

Protected branches (the detected default branch, `main`, `master`,
`develop`, `trunk`, `release/*`, `hotfix/*`, `gh-pages`, and extra `--protect`
globs), the current branch, and branches with an open pull request when
`--check-prs` is used. The same set applies to local and remote deletion;
`--default-branch` changes what merge containment is measured against and never
removes the protection of the branch the remote serves as its default. Unmerged
branches cannot be deleted in bulk: `--allow-unmerged` requires an explicit
`--branch` name.

A branch checked out in another worktree is treated like any other branch,
except that uncommitted work is never deleted out from under you: while that
worktree has tracked changes, or while the repository holds a stash, the branch
is reported as blocked and kept. A clean checkout is only a checkout, so its
branch can be pruned; the worktree is then detached at the archived tip, which
leaves every file in place. Untracked files are left alone and do not hold a
branch back, because detaching never touches them. Only local deletion detaches
anything, so `--target remote` leaves the checkout exactly as it was. A worktree
whose directory was removed is a stale record: it holds no branch back and there
is nothing to detach, so `git worktree prune` clears it separately.

Remote deletion is lease-checked against the audited tip. If another device
pushes to that branch after the audit, the delete is rejected instead of
removing the new work.

### Requirements

- Git 2.38+ for squash-merge detection; older Git falls back to the ancestor
  check and treats squash-merged branches as unmerged.
- Python 3.10+.
- `gh`, authenticated for the repository, only when `--check-prs` is used.
- A normal clone with a worktree; bare repositories are refused.

Exercised on Windows and Linux, including through the repository gate.
Archives are local refs: they are not pushed, and `git push --mirror` would publish them. If
an archive must be shared, create and push a tag explicitly.

## When It Triggers

- A clone is behind its remote, has diverged, or shows branches that no longer
  exist upstream.
- Multiple devices or teammates push, merge, rebase, squash-merge, or force-push
  to the same repository.
- The user asks to clean up merged, stale, abandoned, or “invalid” local or
  remote branches.
- A central branch was deleted and local clones are left with upstream-gone
  branches.
- An upstream rewrite must be distinguished from genuine local work before
  resetting or rebasing.
- A deleted branch tip needs to be archived and restored later.

## When It Does Not Trigger

- Publishing local commits, force-pushing history, opening pull requests, or
  checking commit message format.
- Resolving an active merge or rebase conflict, editing files, or reviewing a
  pull request.
- Synchronizing Skill copies or other directory trees; use `sync-skills`.
- Bare repositories, submodules, Git LFS objects, release tags, or file-sync
  tools.
- Creating a branch for new work; use ordinary Git.
