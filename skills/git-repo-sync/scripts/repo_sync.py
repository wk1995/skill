#!/usr/bin/env python3
"""Audit and reconcile a Git clone with its remote across devices and teammates.

The default mode is read-only. Branch deletion always requires ``--apply``,
refuses protected or checked-out branches, archives the deleted tip under
``refs/repo-sync/archive/``, and validates the remote tip with a push lease
before deleting it. The tool never pushes commits, never force-pushes history,
and never rewrites a branch without an explicit flag.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = 1
ARCHIVE_PREFIX = "refs/repo-sync/archive"
DEFAULT_PROTECTED_PATTERNS = ("main", "master", "develop", "trunk", "release/*", "hotfix/*", "gh-pages")
IN_PROGRESS_MARKERS = (
    ("rebase-merge", "rebase"),
    ("rebase-apply", "rebase"),
    ("MERGE_HEAD", "merge"),
    ("CHERRY_PICK_HEAD", "cherry-pick"),
    ("REVERT_HEAD", "revert"),
    ("BISECT_LOG", "bisect"),
)
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
UNRELATED_BLOCKER = "unmerged content: no common ancestor with the default branch"


class GitError(RuntimeError):
    """A Git command failed or the repository is not in a usable state."""


class Refusal(GitError):
    """A safety rule refused the request before any branch was modified."""


def emit(text: str = "") -> None:
    """Write UTF-8 text without depending on the console encoding."""
    stream = getattr(sys.stdout, "buffer", None)
    data = (text + "\n").encode("utf-8", "backslashreplace")
    if stream is None:  # pragma: no cover - only for embedded callers
        sys.stdout.write(data.decode("utf-8", "replace"))
    else:
        stream.write(data)
        stream.flush()


def emit_error(text: str) -> None:
    stream = getattr(sys.stderr, "buffer", None)
    data = (text + "\n").encode("utf-8", "backslashreplace")
    if stream is None:  # pragma: no cover - only for embedded callers
        sys.stderr.write(data.decode("utf-8", "replace"))
    else:
        stream.write(data)
        stream.flush()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_sha(sha: str | None) -> str:
    return sha[:8] if sha else "-"


def iso_date(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age_days(timestamp: int | None) -> int | None:
    if timestamp is None:
        return None
    return max(0, int((datetime.now(timezone.utc).timestamp() - timestamp) // 86400))


def one_line(value: str, limit: int = 500) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[:limit] + "..."


def same_path(left: str | os.PathLike[str], right: str | os.PathLike[str]) -> bool:
    return os.path.normcase(os.path.realpath(str(left))) == os.path.normcase(
        os.path.realpath(str(right))
    )


@dataclass
class Git:
    cwd: Path

    def run(
        self,
        *args: str,
        check: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "git",
            "-C",
            str(self.cwd),
            "-c",
            "core.quotePath=false",
            "-c",
            "color.ui=false",
            *args,
        ]
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="backslashreplace",
            env=env,
        )
        if check and result.returncode != 0:
            detail = one_line(result.stderr or result.stdout, 2000)
            raise GitError(f"git {args[0]} failed: {detail or 'unknown error'}")
        return result

    def out(self, *args: str, check: bool = True) -> str:
        return self.run(*args, check=check).stdout.strip()


@dataclass
class Repository:
    path: Path
    git: Git
    remote: str


def is_true(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def resolve_repository(options: argparse.Namespace) -> Repository:
    raw_path = Path(options.repo).expanduser()
    if not raw_path.exists():
        raise GitError(f"repository path does not exist: {raw_path}")
    probe = Git(raw_path)
    inside = probe.run("rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or not is_true(inside.stdout):
        raise GitError(f"not a Git worktree: {raw_path}")
    if is_true(probe.out("rev-parse", "--is-bare-repository")):
        raise GitError("bare repositories are not supported; run this tool in a clone")
    root = Path(probe.out("rev-parse", "--show-toplevel"))
    git = Git(root)
    remotes = [line for line in git.out("remote").splitlines() if line]
    if options.remote:
        if options.remote not in remotes:
            raise GitError(f"remote {options.remote!r} is not configured")
        remote = options.remote
    elif "origin" in remotes:
        remote = "origin"
    elif len(remotes) == 1:
        remote = remotes[0]
    else:
        raise GitError("cannot choose a remote; pass --remote <name>")
    return Repository(path=root, git=git, remote=remote)


def tracking_refs(git: Git, remote: str) -> dict[str, str]:
    fmt = "%(refname)%00%(objectname)"
    output = git.out("for-each-ref", f"--format={fmt}", f"refs/remotes/{remote}")
    refs: dict[str, str] = {}
    prefix = f"refs/remotes/{remote}/"
    for line in output.splitlines():
        if not line:
            continue
        ref, _, sha = line.partition("\0")
        name = ref[len(prefix):] if ref.startswith(prefix) else ref
        if name == "HEAD":
            continue
        refs[name] = sha
    return refs


def remote_heads(git: Git, remote: str) -> dict[str, str]:
    result = git.run("ls-remote", "--heads", remote)
    heads: dict[str, str] = {}
    for line in result.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            heads[ref[len("refs/heads/"):]] = sha
    return heads


def remote_default_branch(git: Git, remote: str) -> str | None:
    result = git.run("ls-remote", "--symref", remote, "HEAD", check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        match = re.match(r"^ref: refs/heads/(\S+)\tHEAD$", line)
        if match:
            return match.group(1)
    return None


def detect_default_branch(
    git: Git,
    remote: str,
    heads: dict[str, str],
    *,
    allow_network: bool,
) -> str | None:
    """Detect the repository default branch without applying an override."""
    if allow_network:
        candidate = remote_default_branch(git, remote)
        if candidate and candidate in heads:
            return candidate

    local = git.run("symbolic-ref", "-q", f"refs/remotes/{remote}/HEAD", check=False)
    if local.returncode == 0:
        target = local.stdout.strip()
        prefix = f"refs/remotes/{remote}/"
        if target.startswith(prefix):
            candidate = target[len(prefix):]
            if candidate in heads:
                return candidate

    for candidate in ("main", "master", "trunk"):
        if candidate in heads:
            return candidate
    if len(heads) == 1:
        return next(iter(heads))
    return None


def resolve_default_branch(
    git: Git,
    remote: str,
    override: str | None,
    heads: dict[str, str],
    *,
    allow_network: bool,
) -> tuple[str, str | None]:
    """Return the effective merge base and the detected repository default.

    An override replaces the merge base but never hides what the remote serves
    as its default, which must stay protected.
    """
    detected = detect_default_branch(git, remote, heads, allow_network=allow_network)
    if override:
        if override not in heads:
            raise GitError(f"--default-branch {override!r} is not a branch of {remote}")
        return override, detected
    if detected is None:
        raise GitError("cannot determine the default branch; pass --default-branch <name>")
    return detected, detected


def local_branches(git: Git) -> list[dict[str, Any]]:
    fmt = "%(refname)%00%(objectname)%00%(upstream)%00%(committerdate:unix)"
    output = git.out("for-each-ref", f"--format={fmt}", "refs/heads")
    records: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line:
            continue
        ref, sha, upstream, timestamp = line.split("\0")
        records.append(
            {
                "name": ref[len("refs/heads/"):],
                "sha": sha,
                "upstream": upstream or None,
                "commit_time": int(timestamp) if timestamp else None,
            }
        )
    return records


def _worktree_record(current: dict[str, str]) -> dict[str, Any]:
    branch_ref = current.get("branch", "")
    return {
        "path": current.get("worktree"),
        "branch": branch_ref[len("refs/heads/"):] if branch_ref.startswith("refs/heads/") else None,
        "detached": "detached" in current,
        "bare": "bare" in current,
    }


def worktrees(git: Git) -> list[dict[str, Any]]:
    """Read worktrees with NUL records so unusual paths cannot split a record."""
    nul = git.run("worktree", "list", "--porcelain", "-z", check=False)
    items: list[dict[str, Any]] = []
    if nul.returncode == 0:
        current: dict[str, str] = {}
        for token in nul.stdout.split("\0"):
            if not token:
                if current:
                    items.append(_worktree_record(current))
                    current = {}
                continue
            key, _, value = token.partition(" ")
            current[key] = value
        if current:
            items.append(_worktree_record(current))
        return items

    output = git.out("worktree", "list", "--porcelain")
    current = {}
    for line in output.splitlines():
        if not line:
            if current:
                items.append(_worktree_record(current))
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        items.append(_worktree_record(current))
    return items


def dirty_counts(git: Git) -> tuple[int, int]:
    result = git.run(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=normal",
        "--ignore-submodules=none",
    )
    parts = result.stdout.split("\0")
    tracked = 0
    untracked = 0
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        if entry.startswith("??"):
            untracked += 1
            continue
        tracked += 1
        if entry[0] in ("R", "C"):
            index += 1
    return tracked, untracked


def operation_in_progress(git: Git) -> str | None:
    git_dir = Path(git.out("rev-parse", "--absolute-git-dir"))
    for marker, label in IN_PROGRESS_MARKERS:
        if (git_dir / marker).exists():
            return label
    return None


def stash_count(git: Git) -> int:
    return len([line for line in git.out("stash", "list").splitlines() if line])


def is_protected(name: str, default_branch: str, extra: Iterable[str]) -> bool:
    patterns = list(DEFAULT_PROTECTED_PATTERNS) + [default_branch] + list(extra)
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def ahead_behind(git: Git, upstream_ref: str, sha: str) -> tuple[int, int]:
    result = git.out("rev-list", "--count", "--left-right", f"{upstream_ref}...{sha}")
    left, right = (int(part) for part in result.split())
    return right, left  # ahead, behind


def unique_patch_count(git: Git, upstream_ref: str, sha: str) -> int | None:
    result = git.run("cherry", upstream_ref, sha, check=False)
    if result.returncode != 0:
        return None
    return sum(1 for line in result.stdout.splitlines() if line.startswith("+"))


def commit_timestamp(git: Git, sha: str) -> int | None:
    result = git.run("show", "-s", "--format=%ct", sha, check=False)
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def commit_available(git: Git, sha: str) -> bool:
    return git.run("cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


class MergeChecker:
    """Decide whether merging a branch into the default branch is a no-op.

    Tree equality also detects squash merges and cherry-picked content that
    ``git branch --merged`` misses. A conflict, an unrelated history, or an
    unsupported Git is reported as unmerged, so cleanup fails closed.
    """

    def __init__(self, git: Git, target_sha: str) -> None:
        self.git = git
        self.target_sha = target_sha
        self.target_tree = git.out("rev-parse", f"{target_sha}^{{tree}}")
        self._supported: bool | None = None
        self._cache: dict[str, str] = {}

    def supports_write_tree(self) -> bool:
        if self._supported is None:
            result = self.git.run("merge-tree", "-h", check=False)
            self._supported = "--write-tree" in (result.stdout + result.stderr)
        return self._supported

    def has_merge_base(self, sha: str) -> bool:
        """Whether the branch and the default branch share any history.

        Tested before ``merge-tree`` because that command exits 128 for unrelated
        histories, which cannot be told apart from a genuine Git failure by exit
        status alone. Matching translated stderr would be locale dependent, while
        ``merge-base`` answers the question directly.
        """
        base = self.git.run("merge-base", self.target_sha, sha, check=False)
        if base.returncode == 0:
            return True
        if base.returncode == 1:
            return False
        detail = (base.stderr or base.stdout).strip()
        raise GitError(f"git merge-base failed: {detail or 'unknown error'}")

    def classify(self, sha: str) -> str:
        if sha in self._cache:
            return self._cache[sha]
        ancestor = self.git.run("merge-base", "--is-ancestor", sha, self.target_sha, check=False)
        if ancestor.returncode == 0:
            state = "ancestor"
        elif ancestor.returncode != 1:
            raise GitError("git merge-base --is-ancestor failed")
        elif not self.supports_write_tree():
            state = "unavailable"
        elif not self.has_merge_base(sha):
            # An orphan branch such as gh-pages shares no history with the
            # default branch, so `git merge-tree` refuses the merge with
            # "refusing to merge unrelated histories". Content can never be
            # contained in the default branch in that case, so report the branch
            # as unmerged instead of aborting every command in the repository.
            state = "unrelated"
        else:
            merged = self.git.run("merge-tree", "--write-tree", self.target_sha, sha, check=False)
            if merged.returncode == 0:
                tree = merged.stdout.splitlines()[0].strip() if merged.stdout.strip() else ""
                state = "noop" if tree == self.target_tree else "changes"
            elif merged.returncode == 1:
                state = "conflict"
            else:
                detail = (merged.stderr or merged.stdout).strip()
                raise GitError(f"git merge-tree failed: {detail or 'unknown error'}")
        self._cache[sha] = state
        return state


def open_pull_requests(git: Git) -> dict[str, list[int]]:
    gh = shutil.which("gh")
    if not gh:
        raise Refusal("--check-prs requires the GitHub CLI (gh) on PATH; refusing to guess PR state")
    env = os.environ.copy()
    env.update({"GH_PROMPT_DISABLED": "1", "GH_PAGER": "cat", "GH_NO_UPDATE_NOTIFIER": "1"})
    result = subprocess.run(
        [gh, "pr", "list", "--state", "open", "--limit", "1000", "--json", "headRefName,number"],
        cwd=git.cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        env=env,
    )
    if result.returncode != 0:
        detail = one_line(result.stderr or result.stdout)
        raise Refusal(f"gh pr list failed; refusing to delete branches without PR state: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise Refusal(f"gh pr list returned invalid JSON: {error}") from error
    if not isinstance(payload, list):
        raise Refusal("gh pr list returned an unexpected payload")
    if len(payload) >= 1000:
        raise Refusal(
            "gh returned the maximum number of open pull requests; "
            "refusing to guess which branches have no review"
        )
    mapping: dict[str, list[int]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("headRefName")
        number = item.get("number")
        if isinstance(name, str) and isinstance(number, int):
            mapping.setdefault(name, []).append(number)
    return mapping


def archive_ref(branch: str, sha: str) -> str:
    return f"{ARCHIVE_PREFIX}/{branch}/{sha}"


def archive_tip(git: Git, branch: str, sha: str) -> str:
    ref = archive_ref(branch, sha)
    existing = git.run("show-ref", "--verify", "--quiet", ref, check=False)
    if existing.returncode == 0:
        current = git.out("rev-parse", ref)
        if current != sha:
            raise GitError(f"archive ref {ref} already points to {current}, not {sha}")
        return ref
    git.run("update-ref", ref, sha)
    if git.out("rev-parse", ref) != sha:
        raise GitError(f"failed to verify archive ref {ref}")
    return ref


def list_archives(git: Git) -> list[dict[str, Any]]:
    fmt = "%(refname)%00%(objectname)%00%(committerdate:unix)"
    output = git.out("for-each-ref", f"--format={fmt}", ARCHIVE_PREFIX)
    archives: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line:
            continue
        ref, sha, timestamp = line.split("\0")
        remainder = ref[len(ARCHIVE_PREFIX) + 1:]
        branch, _, leaf = remainder.rpartition("/")
        if not branch or not SHA_RE.match(leaf):
            continue
        when = int(timestamp) if timestamp else None
        archives.append(
            {
                "ref": ref,
                "branch": branch,
                "sha": sha,
                "commit_time": when,
                "commit_date": iso_date(when),
            }
        )
    archives.sort(key=lambda item: (item["commit_time"] or 0, item["sha"]), reverse=True)
    return archives


def check_branch_name(git: Git, name: str) -> None:
    if not name or name.startswith("-"):
        raise GitError(f"invalid branch name: {name!r}")
    result = git.run("check-ref-format", "--branch", name, check=False)
    if result.returncode != 0:
        raise GitError(f"invalid branch name: {name!r}")


@dataclass
class Ctx:
    repo: Repository
    remote: str
    default_branch: str
    default_sha: str
    merge: MergeChecker
    commit_times: dict[str, int | None]
    patch_counts: dict[tuple[str, str], int | None]

    def timestamp(self, sha: str) -> int | None:
        if sha not in self.commit_times:
            self.commit_times[sha] = commit_timestamp(self.repo.git, sha)
        return self.commit_times[sha]

    def patches(self, upstream_ref: str, sha: str) -> int | None:
        key = (upstream_ref, sha)
        if key not in self.patch_counts:
            self.patch_counts[key] = unique_patch_count(self.repo.git, upstream_ref, sha)
        return self.patch_counts[key]


def base_facts(git: Git) -> dict[str, Any]:
    head = git.run("rev-parse", "--verify", "HEAD", check=False)
    if head.returncode != 0:
        raise GitError("repository has no commits")
    current = git.run("symbolic-ref", "--short", "-q", "HEAD", check=False)
    dirty_tracked, dirty_untracked = dirty_counts(git)
    return {
        "head_sha": head.stdout.strip(),
        "current_branch": current.stdout.strip() if current.returncode == 0 else None,
        "detached": current.returncode != 0,
        "dirty": {"tracked": dirty_tracked, "untracked": dirty_untracked},
        "in_progress": operation_in_progress(git),
        "stashes": stash_count(git),
        "shallow": is_true(git.out("rev-parse", "--is-shallow-repository")),
        "worktrees": worktrees(git),
    }


def build_snapshot(
    repo: Repository,
    *,
    offline: bool,
    prune_remote_refs: bool,
    stale_days: int,
    check_prs: bool,
    protected_extra: Sequence[str],
    default_branch_override: str | None = None,
) -> dict[str, Any]:
    git = repo.git
    facts = base_facts(git)
    before = tracking_refs(git, repo.remote)
    fetch_info: dict[str, Any] = {"performed": False, "updated": [], "pruned": []}
    if not offline:
        args = ["fetch"]
        if prune_remote_refs:
            args.append("--prune")
        args.append(repo.remote)
        result = git.run(*args, check=False)
        if result.returncode != 0:
            detail = one_line(result.stderr or result.stdout)
            raise GitError(f"git fetch {repo.remote} failed: {detail or 'unknown error'}")
        fetch_info["performed"] = True
    after = tracking_refs(git, repo.remote)
    fetch_info["updated"] = sorted(name for name, sha in after.items() if before.get(name) != sha)
    fetch_info["pruned"] = sorted(set(before) - set(after))

    if offline:
        heads = dict(after)
        if not heads:
            raise GitError("no remote-tracking refs available offline; fetch once first")
    else:
        heads = remote_heads(git, repo.remote)
        if not heads:
            raise GitError(f"remote {repo.remote!r} has no branches")

    stale_tracking = [] if offline else sorted(set(after) - set(heads))
    default_branch, detected_default = resolve_default_branch(
        git,
        repo.remote,
        default_branch_override,
        heads,
        allow_network=not offline,
    )
    # An override changes the merge base, never the protection set: the branch
    # the remote actually serves as its default stays protected.
    protected_defaults = [default_branch]
    if detected_default and detected_default not in protected_defaults:
        protected_defaults.append(detected_default)
    protected_extra = list(protected_extra) + [
        name for name in protected_defaults if name != default_branch
    ]
    default_sha = heads.get(default_branch) or after.get(default_branch)
    if not default_sha:
        raise GitError(f"default branch {default_branch!r} is not available")
    if not commit_available(git, default_sha):
        raise GitError(
            f"default branch commit {default_sha} is missing locally; run without --offline"
        )

    ctx = Ctx(
        repo=repo,
        remote=repo.remote,
        default_branch=default_branch,
        default_sha=default_sha,
        merge=MergeChecker(git, default_sha),
        commit_times={},
        patch_counts={},
    )

    pr_map: dict[str, list[int]] = {}
    if check_prs:
        pr_map = open_pull_requests(git)

    worktree_map = {
        item["branch"]: item["path"]
        for item in facts["worktrees"]
        if item["branch"] and item["path"]
    }
    current_branch = facts["current_branch"]

    local_records: list[dict[str, Any]] = []
    for item in local_branches(git):
        name = item["name"]
        sha = item["sha"]
        upstream = item["upstream"]
        upstream_branch: str | None = None
        upstream_remote: str | None = None
        ahead: int | None = None
        behind: int | None = None
        status = "unpublished"
        unique: int | None = None

        if upstream:
            prefix = f"refs/remotes/{repo.remote}/"
            if upstream.startswith(prefix):
                upstream_branch = upstream[len(prefix):]
                upstream_remote = repo.remote
                if upstream_branch not in heads:
                    status = "upstream-gone"
                    if git.run("show-ref", "--verify", "--quiet", upstream, check=False).returncode == 0:
                        ahead, behind = ahead_behind(git, upstream, sha)
                else:
                    ahead, behind = ahead_behind(git, upstream, sha)
                    if ahead == 0 and behind == 0:
                        status = "up-to-date"
                    elif behind == 0:
                        status = "ahead"
                    elif ahead == 0:
                        status = "behind"
                    else:
                        status = "diverged"
                        unique = ctx.patches(upstream, sha)
                        if unique == 0:
                            status = "rewritten-upstream"
            else:
                status = "foreign-upstream"
                if upstream.startswith("refs/remotes/"):
                    upstream_remote = upstream.split("/")[2]
                upstream_branch = upstream.split("/", 3)[-1]

        merge_state = ctx.merge.classify(sha)
        merged = merge_state in ("ancestor", "noop")
        timestamp = item["commit_time"]
        age = age_days(timestamp)
        protected = is_protected(name, default_branch, protected_extra)
        checked_out_path = worktree_map.get(name)
        if checked_out_path and same_path(checked_out_path, repo.path):
            checked_out_path = None
        is_current = name == current_branch
        blockers: list[str] = []
        if protected:
            blockers.append("protected branch")
        if is_current:
            blockers.append("current branch")
        if checked_out_path:
            blockers.append(f"checked out in {checked_out_path}")
        if not merged:
            if merge_state == "conflict":
                blockers.append("merging into the default branch conflicts")
            elif merge_state == "unrelated":
                blockers.append(UNRELATED_BLOCKER)
            elif merge_state == "unavailable":
                blockers.append("merge detection unavailable; branch is treated as unmerged")
            else:
                blockers.append("unmerged content")
        open_prs = pr_map.get(name, [])
        if open_prs:
            blockers.append("open pull request " + ", ".join(f"#{number}" for number in open_prs))

        local_records.append(
            {
                "name": name,
                "sha": sha,
                "upstream": upstream,
                "upstream_remote": upstream_remote,
                "upstream_branch": upstream_branch,
                "status": status,
                "ahead": ahead,
                "behind": behind,
                "unique_patches": unique,
                "merge_state": merge_state,
                "merged": merged,
                "protected": protected,
                "current": is_current,
                "checked_out": checked_out_path,
                "commit_time": timestamp,
                "commit_date": iso_date(timestamp),
                "age_days": age,
                "stale": age is not None and age >= stale_days,
                "open_prs": open_prs,
                "cleanup_candidate": merged and not blockers,
                "review_candidate": (not merged) and age is not None and age >= stale_days,
                "blockers": blockers,
                "archive_ref": archive_ref(name, sha) if merged else None,
            }
        )

    remote_records: list[dict[str, Any]] = []
    for name in sorted(heads):
        sha = heads[name]
        available = commit_available(git, sha)
        merge_state = ctx.merge.classify(sha) if available else "unavailable"
        merged = merge_state in ("ancestor", "noop")
        timestamp = ctx.timestamp(sha) if available else None
        age = age_days(timestamp)
        protected = is_protected(name, default_branch, protected_extra)
        open_prs = pr_map.get(name, [])
        checked_out_path = worktree_map.get(name)
        if checked_out_path and same_path(checked_out_path, repo.path):
            checked_out_path = None
        is_current = name == current_branch
        blockers: list[str] = []
        if protected:
            blockers.append("protected branch")
        if is_current:
            blockers.append("current branch")
        if checked_out_path:
            blockers.append(f"checked out in {checked_out_path}")
        if not available:
            blockers.append("commit is not available locally; fetch the branch first")
        if not merged:
            if merge_state == "conflict":
                blockers.append("merging into the default branch conflicts")
            elif merge_state == "unrelated":
                blockers.append(UNRELATED_BLOCKER)
            elif merge_state == "unavailable":
                blockers.append("merge detection unavailable; branch is treated as unmerged")
            else:
                blockers.append("unmerged content")
        if open_prs:
            blockers.append("open pull request " + ", ".join(f"#{number}" for number in open_prs))
        remote_records.append(
            {
                "name": name,
                "sha": sha,
                "available": available,
                "merge_state": merge_state,
                "merged": merged,
                "protected": protected,
                "current": is_current,
                "checked_out": checked_out_path,
                "open_prs": open_prs,
                "commit_time": timestamp,
                "commit_date": iso_date(timestamp),
                "age_days": age,
                "stale": age is not None and age >= stale_days,
                "cleanup_candidate": merged and not blockers,
                "review_candidate": (not merged) and age is not None and age >= stale_days,
                "blockers": blockers,
                "archive_ref": archive_ref(name, sha) if available else None,
            }
        )

    local_status: dict[str, int] = {}
    for record in local_records:
        local_status[record["status"]] = local_status.get(record["status"], 0) + 1
    cleanup_local = [record["name"] for record in local_records if record["cleanup_candidate"]]
    cleanup_remote = [record["name"] for record in remote_records if record["cleanup_candidate"]]
    review = [record["name"] for record in local_records if record["review_candidate"]]
    review += [record["name"] for record in remote_records if record["review_candidate"]]

    findings: list[str] = []
    if facts["detached"]:
        findings.append(f"HEAD is detached at {short_sha(facts['head_sha'])}")
    if facts["dirty"]["tracked"]:
        findings.append(f"worktree has {facts['dirty']['tracked']} tracked change(s)")
    if facts["in_progress"]:
        findings.append(f"a {facts['in_progress']} operation is in progress")
    for record in local_records:
        if record["status"] == "behind":
            findings.append(f"local branch {record['name']} is behind {record['behind']} commit(s)")
        elif record["status"] == "diverged":
            findings.append(f"local branch {record['name']} has diverged history")
        elif record["status"] == "rewritten-upstream":
            findings.append(f"local branch {record['name']} tracks a rewritten upstream")
        elif record["status"] == "upstream-gone":
            findings.append(f"local branch {record['name']} has no upstream branch")
        elif record["status"] == "foreign-upstream":
            findings.append(f"local branch {record['name']} tracks another remote")
        if record["review_candidate"]:
            findings.append(f"local branch {record['name']} is stale and unmerged")
    if cleanup_local:
        findings.append(f"{len(cleanup_local)} local branch(es) can be pruned")
    if cleanup_remote:
        findings.append(f"{len(cleanup_remote)} remote branch(es) can be pruned")
    for record in remote_records:
        if record["review_candidate"]:
            findings.append(f"remote branch {record['name']} is stale and unmerged")
    if facts["shallow"]:
        findings.append("repository is shallow; cleanup is disabled unless --allow-shallow is given")
    if stale_tracking:
        findings.append(f"{len(stale_tracking)} stale remote-tracking ref(s); sync --apply prunes them")

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "offline": offline,
        "repo": {
            "path": str(repo.path),
            "remote": repo.remote,
            "default_branch": default_branch,
            "default_sha": default_sha,
            "detected_default_branch": detected_default,
            "protected_patterns": list(DEFAULT_PROTECTED_PATTERNS) + [default_branch] + list(protected_extra),
            **facts,
        },
        "fetch": fetch_info,
        "stale_tracking": stale_tracking,
        "open_prs": {"checked": check_prs, "count": sum(len(v) for v in pr_map.values())},
        "local_branches": local_records,
        "remote_branches": remote_records,
        "summary": {
            "local_branches": len(local_records),
            "remote_branches": len(remote_records),
            "statuses": local_status,
            "diverged": local_status.get("diverged", 0),
            "rewritten": local_status.get("rewritten-upstream", 0),
            "upstream_gone": local_status.get("upstream-gone", 0),
            "behind": local_status.get("behind", 0),
            "merged_local": sum(1 for record in local_records if record["merged"]),
            "merged_remote": sum(1 for record in remote_records if record["merged"]),
            "cleanup_local": cleanup_local,
            "cleanup_remote": cleanup_remote,
            "review": review,
            "open_prs_checked": check_prs,
        },
        "findings": findings,
    }


def status_label(record: dict[str, Any]) -> str:
    status = record["status"]
    if status == "behind":
        return f"behind {record['behind']}"
    if status == "ahead":
        return f"ahead {record['ahead']}"
    if status == "diverged":
        return f"diverged +{record['ahead']}/-{record['behind']}"
    if status == "rewritten-upstream":
        return "upstream rewritten"
    if status == "upstream-gone":
        return "upstream gone"
    if status == "foreign-upstream":
        return f"tracks {record['upstream']}"
    return status


def merge_label(record: dict[str, Any]) -> str:
    state = record["merge_state"]
    return {
        "ancestor": "merged",
        "noop": "merged (squash)",
        "changes": "unmerged",
        "conflict": "conflict",
        "unrelated": "unrelated history",
        "unavailable": "unknown",
    }.get(state, state)


def render_audit(snapshot: dict[str, Any]) -> str:
    repo = snapshot["repo"]
    lines = [
        f"Repository: {repo['path']}",
        f"Remote: {repo['remote']}   Default: {repo['default_branch']} ({short_sha(repo['default_sha'])})",
    ]
    state_bits = []
    state_bits.append("detached" if repo["detached"] else f"on {repo['current_branch'] or '-'}")
    dirty = repo["dirty"]
    if dirty["tracked"] or dirty["untracked"]:
        state_bits.append(f"dirty ({dirty['tracked']} tracked, {dirty['untracked']} untracked)")
    else:
        state_bits.append("worktree clean")
    state_bits.append(f"{repo['stashes']} stash(es)")
    if repo["in_progress"]:
        state_bits.append(f"{repo['in_progress']} in progress")
    if repo["shallow"]:
        state_bits.append("shallow")
    lines.append("State: " + "; ".join(state_bits))
    fetch = snapshot["fetch"]
    if snapshot["offline"]:
        lines.append("Fetch: skipped (offline)")
    elif fetch["performed"]:
        lines.append(f"Fetch: {len(fetch['updated'])} updated, {len(fetch['pruned'])} pruned")
    if snapshot["stale_tracking"]:
        lines.append("Stale remote-tracking refs: " + ", ".join(snapshot["stale_tracking"]))

    locals_ = snapshot["local_branches"]
    lines.append("")
    lines.append(f"Local branches ({len(locals_)})")
    width = min(max([len(item["name"]) for item in locals_] + [8]), 36)
    for record in locals_:
        flags = []
        if record["current"]:
            flags.append("current")
        if record["protected"]:
            flags.append("protected")
        if record["checked_out"]:
            flags.append("worktree")
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"  {record['name']:<{width}}  {status_label(record):<26} {merge_label(record):<16}{suffix}".rstrip()
        )

    remotes = snapshot["remote_branches"]
    lines.append("")
    lines.append(f"Remote branches ({len(remotes)})")
    width = min(max([len(item["name"]) for item in remotes] + [8]), 36)
    for record in remotes:
        age = f"{record['age_days']}d" if record["age_days"] is not None else "-"
        flags = []
        if record["protected"]:
            flags.append("protected")
        if record.get("current"):
            flags.append("current")
        if record.get("checked_out"):
            flags.append("worktree")
        if record["open_prs"]:
            flags.append("PR " + ",".join(f"#{number}" for number in record["open_prs"]))
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        lines.append(f"  {record['name']:<{width}}  {age:>6}  {merge_label(record):<16}{suffix}".rstrip())

    local_cleanup = [record["name"] for record in locals_ if record["cleanup_candidate"]]
    remote_cleanup = [record["name"] for record in remotes if record["cleanup_candidate"]]
    review = [record["name"] for record in locals_ if record["review_candidate"]]
    review += [record["name"] for record in remotes if record["review_candidate"]]
    if local_cleanup or remote_cleanup:
        lines.append("")
        lines.append("Cleanup candidates (merged, unprotected, not checked out)")
        for name in local_cleanup:
            lines.append(f"  local   {name}")
        for name in remote_cleanup:
            lines.append(f"  remote  {name}")
    if review:
        lines.append("")
        lines.append("Stale and unmerged (review only; never deleted in bulk)")
        for name in review:
            lines.append(f"  {name}")

    if snapshot["findings"]:
        lines.append("")
        lines.append("Attention")
        for finding in snapshot["findings"]:
            lines.append(f"  - {finding}")
    return "\n".join(lines)


def build_sync_actions(snapshot: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    repo = snapshot["repo"]
    dirty_tracked = repo["dirty"]["tracked"]
    remote_by_name = {record["name"]: record for record in snapshot["remote_branches"]}
    actions: list[dict[str, Any]] = []
    records = sorted(
        snapshot["local_branches"],
        key=lambda record: (record["name"] != repo["default_branch"], record["name"]),
    )
    for record in records:
        name = record["name"]
        status = record["status"]
        upstream_branch = record["upstream_branch"]
        upstream = remote_by_name.get(upstream_branch) if upstream_branch else None
        upstream_sha = upstream["sha"] if upstream else None

        if status in ("up-to-date", "unpublished", "foreign-upstream", "ahead"):
            continue
        if status == "upstream-gone":
            actions.append(
                {
                    "kind": "blocked",
                    "branch": name,
                    "status": "blocked",
                    "reason": "upstream branch no longer exists; archive and prune it locally or re-publish it",
                }
            )
            continue
        if record["checked_out"]:
            actions.append(
                {
                    "kind": "skip",
                    "branch": name,
                    "status": "skipped",
                    "reason": f"checked out in {record['checked_out']}",
                }
            )
            continue
        if upstream_sha is None or not upstream["available"]:
            actions.append(
                {
                    "kind": "blocked",
                    "branch": name,
                    "status": "blocked",
                    "reason": "upstream commit is not available; fetch the branch first",
                }
            )
            continue

        if record["current"]:
            if dirty_tracked and status in ("behind", "diverged", "rewritten-upstream"):
                actions.append(
                    {
                        "kind": "blocked",
                        "branch": name,
                        "status": "blocked",
                        "reason": f"worktree has {dirty_tracked} tracked change(s); commit or stash them first",
                    }
                )
                continue
            if status == "behind":
                actions.append(
                    {
                        "kind": "fast-forward",
                        "branch": name,
                        "upstream_branch": upstream_branch,
                        "from": record["sha"],
                        "to": upstream_sha,
                        "method": "merge",
                        "status": "planned",
                        "reason": f"behind {record['behind']} commit(s)",
                    }
                )
            elif status in ("diverged", "rewritten-upstream"):
                if args.rebase_current:
                    actions.append(
                        {
                            "kind": "rebase",
                            "branch": name,
                            "upstream_branch": upstream_branch,
                            "from": record["sha"],
                            "to": upstream_sha,
                            "method": "rebase",
                            "status": "planned",
                            "reason": "local commits are replayed on the upstream tip",
                        }
                    )
                else:
                    actions.append(
                        {
                            "kind": "blocked",
                            "branch": name,
                            "status": "blocked",
                            "reason": "history diverged; re-run with --rebase-current or resolve manually",
                        }
                    )
        else:
            if status == "behind":
                actions.append(
                    {
                        "kind": "fast-forward",
                        "branch": name,
                        "upstream_branch": upstream_branch,
                        "from": record["sha"],
                        "to": upstream_sha,
                        "method": "update-ref",
                        "status": "planned",
                        "reason": f"behind {record['behind']} commit(s)",
                    }
                )
            elif status == "rewritten-upstream":
                if args.reset_rewritten:
                    actions.append(
                        {
                            "kind": "reset-rewritten",
                            "branch": name,
                            "upstream_branch": upstream_branch,
                            "from": record["sha"],
                            "to": upstream_sha,
                            "method": "update-ref",
                            "status": "planned",
                            "reason": "every local patch is already upstream after a rewrite",
                        }
                    )
                else:
                    actions.append(
                        {
                            "kind": "blocked",
                            "branch": name,
                            "status": "blocked",
                            "reason": "upstream was rewritten; re-run with --reset-rewritten",
                        }
                    )
            elif status == "diverged":
                actions.append(
                    {
                        "kind": "blocked",
                        "branch": name,
                        "status": "blocked",
                        "reason": "history diverged; resolve it manually on this branch",
                    }
                )
    return actions


def apply_sync_actions(
    repo: Repository,
    remote: str,
    actions: list[dict[str, Any]],
) -> None:
    git = repo.git
    for action in actions:
        if action["status"] != "planned":
            continue
        branch = action["branch"]
        ref = f"refs/heads/{branch}"
        upstream_branch = action["upstream_branch"]
        try:
            if action["kind"] == "fast-forward" and action["method"] == "merge":
                current = git.run("symbolic-ref", "--short", "-q", "HEAD", check=False)
                if current.returncode != 0 or current.stdout.strip() != branch:
                    raise GitError("the checked-out branch changed after planning; nothing was applied")
                result = git.run(
                    "merge", "--ff-only", f"refs/remotes/{remote}/{upstream_branch}", check=False
                )
                if result.returncode != 0:
                    detail = one_line(result.stderr or result.stdout)
                    raise GitError(detail or "fast-forward merge failed")
                if git.out("rev-parse", "HEAD") != action["to"]:
                    raise GitError("fast-forward merge did not reach the audited upstream commit")
            elif action["kind"] in ("fast-forward", "reset-rewritten"):
                if action["kind"] == "reset-rewritten":
                    action["archive_ref"] = archive_tip(git, branch, action["from"])
                git.run("update-ref", ref, action["to"], action["from"])
            elif action["kind"] == "rebase":
                current = git.run("symbolic-ref", "--short", "-q", "HEAD", check=False)
                if current.returncode != 0 or current.stdout.strip() != branch:
                    raise GitError("the checked-out branch changed after planning; nothing was applied")
                action["archive_ref"] = archive_tip(git, branch, action["from"])
                rebase = git.run(
                    "rebase",
                    f"refs/remotes/{remote}/{upstream_branch}",
                    check=False,
                    extra_env={
                        "GIT_EDITOR": "true",
                        "GIT_SEQUENCE_EDITOR": "true",
                        "GIT_MERGE_AUTOEDIT": "no",
                    },
                )
                if rebase.returncode != 0:
                    conflicts = [
                        line
                        for line in git.run(
                            "diff", "--name-only", "--diff-filter=U", check=False
                        ).stdout.splitlines()
                        if line
                    ]
                    aborted = git.run("rebase", "--abort", check=False)
                    detail = one_line(rebase.stderr or rebase.stdout)
                    if aborted.returncode != 0:
                        if operation_in_progress(git) is None:
                            # The commonest cause is a checkout that never started,
                            # so --abort has nothing to undo. Telling the user to
                            # resolve a rebase invites destructive guesswork.
                            raise GitError(
                                "rebase failed and left no rebase in progress; nothing to abort: "
                                + detail
                            )
                        raise GitError(
                            "rebase failed and --abort also failed; resolve the rebase before retrying: "
                            + detail
                        )
                    raise GitError(
                        "rebase conflicted and was aborted; original branch restored"
                        + (f" (conflicts: {', '.join(conflicts)})" if conflicts else "")
                    )
                landed = git.run(
                    "merge-base",
                    "--is-ancestor",
                    f"refs/remotes/{remote}/{upstream_branch}",
                    "HEAD",
                    check=False,
                )
                if landed.returncode != 0:
                    raise GitError("rebase finished but the upstream commit is not an ancestor of HEAD")
            else:
                raise GitError(f"unknown action {action['kind']}")
            action["status"] = "applied"
        except GitError as error:
            action["status"] = "failed"
            action["error"] = str(error)
            if action["kind"] == "rebase" and action.get("archive_ref"):
                if operation_in_progress(git) is None:
                    current = git.run("rev-parse", "--verify", "HEAD", check=False)
                    if current.returncode == 0 and current.stdout.strip() != action["from"]:
                        restored = git.run("reset", "--hard", action["from"], check=False)
                        if restored.returncode == 0:
                            action["error"] += " (branch restored to the archived tip)"
                action["conflicts"] = [
                    line
                    for line in git.run(
                        "diff", "--name-only", "--diff-filter=U", check=False
                    ).stdout.splitlines()
                    if line
                ]


def render_sync(actions: list[dict[str, Any]], snapshot: dict[str, Any], *, apply: bool) -> str:
    title = "Sync results" if apply else "Sync plan (dry run; add --apply to execute)"
    lines = [title]
    ahead = snapshot["summary"]["statuses"].get("ahead", 0)
    if not actions:
        if ahead:
            lines.append(
                f"  pull side is up to date; {ahead} local branch(es) are ahead and need publishing"
            )
        else:
            lines.append("  already clean; no branch needs updating")
        return "\n".join(lines)
    width = min(max([len(item["branch"]) for item in actions] + [8]), 36)
    for action in actions:
        kind = action["kind"]
        branch = action["branch"]
        if action["status"] == "planned":
            if kind == "fast-forward":
                lines.append(
                    f"  {branch:<{width}}  fast-forward {short_sha(action['from'])} -> "
                    f"{short_sha(action['to'])}  ({action['reason']})"
                )
            elif kind == "rebase":
                lines.append(
                    f"  {branch:<{width}}  rebase onto {short_sha(action['to'])}  (old tip archived)"
                )
            elif kind == "reset-rewritten":
                lines.append(
                    f"  {branch:<{width}}  reset to rewritten upstream {short_sha(action['to'])}  "
                    "(old tip archived)"
                )
            else:
                lines.append(f"  {branch:<{width}}  {kind}  ({action['reason']})")
        elif action["status"] == "applied":
            extra = f"  archive {action['archive_ref']}" if action.get("archive_ref") else ""
            lines.append(f"  {branch:<{width}}  applied {kind}{extra}")
        elif action["status"] == "failed":
            lines.append(f"  {branch:<{width}}  FAILED  {action.get('error', 'unknown error')}")
        elif action["status"] == "blocked":
            lines.append(f"  {branch:<{width}}  blocked  {action['reason']}")
        elif action["status"] == "skipped":
            lines.append(f"  {branch:<{width}}  skipped  {action['reason']}")
    if ahead:
        lines.append("")
        lines.append(f"  note: {ahead} local branch(es) are ahead; publishing is separate")
    if snapshot["findings"]:
        lines.append("")
        lines.append("Attention")
        for finding in snapshot["findings"]:
            lines.append(f"  - {finding}")
    return "\n".join(lines)


def prune_records(snapshot: dict[str, Any], target: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if target in ("local", "all"):
        records.extend({**record, "target": "local"} for record in snapshot["local_branches"])
    if target in ("remote", "all"):
        records.extend({**record, "target": "remote"} for record in snapshot["remote_branches"])
    return records


def build_prune_plan(snapshot: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    explicit = set(args.branch)
    select_merged = args.merged or not (
        args.merged or args.gone or args.stale_days is not None or explicit
    )

    records = prune_records(snapshot, args.target)
    names = {record["name"] for record in records}
    plan: list[dict[str, Any]] = []

    for record in records:
        name = record["name"]
        if explicit and name not in explicit:
            continue
        if not explicit and record["protected"]:
            continue
        selected = (
            (explicit and name in explicit)
            or (select_merged and record["merged"])
            or (args.gone and record.get("status") == "upstream-gone")
            or (args.stale_days is not None and record["stale"])
        )
        if not selected:
            continue

        blockers = list(record["blockers"])
        if args.allow_unmerged and explicit:
            blockers = [
                blocker
                for blocker in blockers
                if blocker
                not in {
                    "unmerged content",
                    "merging into the default branch conflicts",
                    "merge detection unavailable; branch is treated as unmerged",
                    UNRELATED_BLOCKER,
                }
            ]
        elif not record["merged"] and "unmerged content" not in blockers and not any(
            "merge" in blocker for blocker in blockers
        ):
            blockers.append("unmerged content")

        plan.append(
            {
                "target": record["target"],
                "name": name,
                "sha": record["sha"],
                "merged": record["merged"],
                "merge_state": record["merge_state"],
                "age_days": record["age_days"],
                "blockers": blockers,
                "action": "delete" if not blockers else "skip",
                "archive_ref": record.get("archive_ref") or archive_ref(name, record["sha"]),
            }
        )

    if explicit:
        for name in sorted(explicit - names):
            plan.append(
                {
                    "target": "unknown",
                    "name": name,
                    "sha": None,
                    "merged": False,
                    "merge_state": "unknown",
                    "age_days": None,
                    "blockers": ["branch not found in the selected target"],
                    "action": "skip",
                    "archive_ref": None,
                }
            )
    plan.sort(key=lambda item: (item["target"], item["name"]))
    return plan


def delete_local_branch(git: Git, name: str, sha: str) -> None:
    result = git.run("update-ref", "-d", f"refs/heads/{name}", sha, check=False)
    if result.returncode != 0:
        detail = one_line(result.stderr or result.stdout)
        raise GitError(f"branch {name} moved or could not be deleted: {detail}")
    if git.run("show-ref", "--verify", "--quiet", f"refs/heads/{name}", check=False).returncode == 0:
        raise GitError(f"branch {name} still exists after deletion")
    git.run("config", "--remove-section", f"branch.{name}", check=False)


def delete_remote_branch(git: Git, remote: str, name: str, sha: str) -> None:
    result = git.run(
        "push",
        f"--force-with-lease=refs/heads/{name}:{sha}",
        "--delete",
        remote,
        f"refs/heads/{name}",
        check=False,
    )
    if result.returncode != 0:
        detail = one_line(result.stderr or result.stdout)
        raise GitError(f"remote branch {name} was not deleted (moved or protected): {detail}")
    remaining = git.run("ls-remote", "--heads", remote, f"refs/heads/{name}", check=False)
    if remaining.returncode != 0:
        raise GitError(f"could not verify deletion of {remote}/{name}: {remaining.stderr.strip()}")
    if remaining.stdout.strip():
        raise GitError(f"remote branch {name} still exists after deletion")
    # The branch is gone remotely; drop its local tracking ref so the same clone
    # does not keep reporting a branch it just deleted.
    git.run("update-ref", "-d", f"refs/remotes/{remote}/{name}", check=False)


def apply_prune_plan(
    repo: Repository,
    snapshot: dict[str, Any],
    plan: list[dict[str, Any]],
    *,
    apply: bool,
    target: str,
) -> dict[str, Any]:
    remote = snapshot["repo"]["remote"]
    result: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "command": "prune",
        "apply": apply,
        "target": target,
        "deleted": [],
        "skipped": [],
        "failed": [],
        "archives": [],
    }
    if not apply:
        result["plan"] = plan
        return result

    for item in plan:
        if item["action"] != "delete":
            result["skipped"].append(item)
            continue
        try:
            ref = archive_tip(repo.git, item["name"], item["sha"])
            item["archive_ref"] = ref
            if item["target"] == "local":
                delete_local_branch(repo.git, item["name"], item["sha"])
            else:
                delete_remote_branch(repo.git, remote, item["name"], item["sha"])
            item["action"] = "deleted"
            result["deleted"].append(item)
            result["archives"].append(ref)
        except GitError as error:
            item["action"] = "failed"
            item["error"] = str(error)
            result["failed"].append(item)
    return result


def render_prune(result: dict[str, Any], plan: list[dict[str, Any]]) -> str:
    apply = result["apply"]
    title = "Prune results" if apply else "Prune plan (dry run; add --apply to delete)"
    lines = [title]
    if not plan:
        lines.append("  no branches matched the selection")
        return "\n".join(lines)
    width = min(max([len(item["name"]) for item in plan] + [8]), 36)
    for item in plan:
        if item["action"] == "delete":
            state = "merged" if item["merged"] else "unmerged (explicit)"
            lines.append(
                f"  DELETE  {item['target']:<6} {item['name']:<{width}}  "
                f"{state}; archive {item['archive_ref']}"
            )
        elif item["action"] == "deleted":
            lines.append(
                f"  DELETED {item['target']:<6} {item['name']:<{width}}  "
                f"archive {item['archive_ref']}"
            )
        elif item["action"] == "failed":
            lines.append(f"  FAILED  {item['target']:<6} {item['name']:<{width}}  {item['error']}")
        else:
            lines.append(
                f"  SKIP    {item['target']:<6} {item['name']:<{width}}  {'; '.join(item['blockers'])}"
            )
    if result.get("deleted"):
        lines.append("")
        lines.append(f"Deleted {len(result['deleted'])} branch(es); restore any of them with:")
        for item in result["deleted"]:
            lines.append(
                f"  python <skill>/scripts/repo_sync.py restore {item['archive_ref']} "
                f"--branch {item['name']}"
            )
    return "\n".join(lines)


def render_archives(archives: list[dict[str, Any]]) -> str:
    lines = [f"Archived branch tips ({len(archives)})"]
    if not archives:
        lines.append("  none")
        return "\n".join(lines)
    width = min(max([len(item["branch"]) for item in archives] + [8]), 36)
    for item in archives:
        lines.append(
            f"  {item['branch']:<{width}}  {short_sha(item['sha'])}  "
            f"{item['commit_date'] or '-'}  {item['ref']}"
        )
    return "\n".join(lines)


def cmd_audit(args: argparse.Namespace) -> int:
    repo = resolve_repository(args)
    snapshot = build_snapshot(
        repo,
        offline=args.offline,
        prune_remote_refs=False,
        stale_days=args.stale_days,
        check_prs=args.check_prs,
        protected_extra=args.protect,
        default_branch_override=args.default_branch,
    )
    if args.json:
        emit(json.dumps(snapshot, indent=2, ensure_ascii=False))
    else:
        emit(render_audit(snapshot))
    return 2 if args.strict and snapshot["findings"] else 0


def cmd_prune(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.allow_unmerged and not args.branch:
        parser.error("--allow-unmerged requires one or more --branch names")
    if args.gone and args.target == "remote":
        parser.error("--gone applies to local branches")
    if args.target in ("remote", "all") and args.offline:
        parser.error("--offline cannot delete remote branches")
    if args.stale_days is not None and args.stale_days < 0:
        parser.error("--stale-days must be zero or greater")
    stale_days = args.stale_days if args.stale_days is not None else 90

    repo = resolve_repository(args)
    for name in args.branch:
        check_branch_name(repo.git, name)
    facts = base_facts(repo.git)
    if args.apply:
        if facts["in_progress"]:
            raise Refusal(f"refusing to delete branches during a {facts['in_progress']} operation")
        if facts["shallow"] and not args.allow_shallow:
            raise Refusal(
                "refusing to delete branches in a shallow clone; pass --allow-shallow to override"
            )
    snapshot = build_snapshot(
        repo,
        offline=args.offline,
        prune_remote_refs=args.target in ("remote", "all"),
        stale_days=stale_days,
        check_prs=args.check_prs,
        protected_extra=args.protect,
        default_branch_override=args.default_branch,
    )
    plan = build_prune_plan(snapshot, args)
    if args.apply and operation_in_progress(repo.git):
        raise Refusal("a repository operation started after planning; nothing was deleted")
    result = apply_prune_plan(repo, snapshot, plan, apply=args.apply, target=args.target)
    if args.json:
        emit(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        emit(render_prune(result, plan))
    unknown = any(item["target"] == "unknown" for item in plan)
    if not args.apply:
        has_candidates = any(item["action"] == "delete" for item in plan)
        return 2 if unknown or (args.strict and has_candidates) else 0
    explicit = set(args.branch)
    explicit_skips = any(
        item["name"] in explicit and item["action"] in ("skip", "failed") for item in plan
    )
    return 2 if result["failed"] or unknown or explicit_skips else 0


def cmd_sync(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.apply and args.offline:
        parser.error("--apply cannot be combined with --offline")
    repo = resolve_repository(args)
    facts = base_facts(repo.git)
    if args.apply and facts["in_progress"]:
        raise Refusal(f"refusing to change branches during a {facts['in_progress']} operation")
    snapshot = build_snapshot(
        repo,
        offline=args.offline,
        prune_remote_refs=True,
        stale_days=90,
        check_prs=False,
        protected_extra=args.protect,
        default_branch_override=args.default_branch,
    )
    actions = build_sync_actions(snapshot, args)
    if not args.apply:
        payload = {
            "schema": SCHEMA_VERSION,
            "command": "sync",
            "apply": False,
            "actions": actions,
            "summary": snapshot["summary"],
        }
        if args.json:
            emit(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            emit(render_sync(actions, snapshot, apply=False))
        return 0

    if operation_in_progress(repo.git):
        raise Refusal("a repository operation started after planning; nothing was changed")
    apply_sync_actions(repo, repo.remote, actions)
    post: dict[str, Any] | None = None
    post_error: str | None = None
    try:
        post = build_snapshot(
            repo,
            offline=True,
            prune_remote_refs=False,
            stale_days=90,
            check_prs=False,
            protected_extra=args.protect,
            default_branch_override=args.default_branch,
        )
    except GitError as error:
        post_error = str(error)
    payload = {
        "schema": SCHEMA_VERSION,
        "command": "sync",
        "apply": True,
        "actions": actions,
        "post": (
            {"summary": post["summary"], "findings": post["findings"]}
            if post
            else {"error": post_error}
        ),
    }
    if args.json:
        emit(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        emit(render_sync(actions, post or snapshot, apply=True))
    return 2 if any(action["status"] in ("blocked", "failed") for action in actions) else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_sync.py",
        description="Audit and reconcile a Git clone with its remote; read-only by default.",
        epilog=(
            "Run `audit` first, then `sync --apply` for fast-forwards and "
            "`prune --apply` for merged branches. Destructive commands archive every "
            "deleted tip under refs/repo-sync/archive/."
        ),
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=".", help="worktree path (default: current directory)")
    common.add_argument("--remote", default=None, help="remote name (default: origin, or the only remote)")
    common.add_argument("--default-branch", default=None, help="default branch override")
    common.add_argument("--offline", action="store_true", help="use existing refs; do not fetch")
    common.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    common.add_argument("--protect", action="append", default=[], help="extra protected branch glob")

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", parents=[common], help="report drift and cleanup candidates")
    audit.add_argument("--stale-days", type=int, default=90, help="age in days for stale review (default: 90)")
    audit.add_argument("--check-prs", action="store_true", help="ask gh for open PRs; fails closed")
    audit.add_argument("--strict", action="store_true", help="exit 2 when findings exist")

    sync = subparsers.add_parser("sync", parents=[common], help="fast-forward safe branches")
    sync.add_argument("--apply", action="store_true", help="execute the plan (default: dry run)")
    sync.add_argument(
        "--rebase-current",
        action="store_true",
        help="replay the current branch's local commits on its upstream after archiving the old tip",
    )
    sync.add_argument(
        "--reset-rewritten",
        action="store_true",
        help="move non-current branches whose patches are already upstream after a rewrite",
    )

    prune = subparsers.add_parser("prune", parents=[common], help="delete merged branches after archiving")
    prune.add_argument("--target", choices=("local", "remote", "all"), default="local")
    prune.add_argument("--merged", action="store_true", help="select branches merged into the default branch")
    prune.add_argument("--gone", action="store_true", help="select local branches whose upstream is gone")
    prune.add_argument("--stale-days", type=int, default=None, help="select branches older than N days")
    prune.add_argument("--branch", action="append", default=[], help="explicit branch name (repeatable)")
    prune.add_argument(
        "--allow-unmerged",
        action="store_true",
        help="allow deleting explicitly named unmerged branches (requires --branch)",
    )
    prune.add_argument("--allow-shallow", action="store_true", help="allow cleanup in a shallow clone")
    prune.add_argument("--apply", action="store_true", help="execute the plan (default: dry run)")
    prune.add_argument("--check-prs", action="store_true", help="ask gh for open PRs; fails closed")
    prune.add_argument("--strict", action="store_true", help="exit 2 when a plan has candidates")

    archive = subparsers.add_parser("archive", parents=[common], help="list archived branch tips")
    archive.add_argument("action", nargs="?", default="list", choices=("list",))

    restore = subparsers.add_parser("restore", parents=[common], help="recreate a branch from an archive ref")
    restore.add_argument("reference", help="archive ref or original branch name")
    restore.add_argument("--branch", default=None, help="target branch name (default: archived name)")

    args = parser.parse_args(argv)

    if getattr(args, "check_prs", False) and args.offline:
        parser.error("--check-prs cannot be combined with --offline")

    try:
        if args.command == "audit":
            if args.stale_days < 0:
                parser.error("--stale-days must be zero or greater")
            return cmd_audit(args)
        if args.command == "sync":
            return cmd_sync(args, parser)
        if args.command == "prune":
            return cmd_prune(args, parser)
        if args.command == "archive":
            repo = resolve_repository(args)
            archives = list_archives(repo.git)
            if args.json:
                emit(
                    json.dumps(
                        {"schema": SCHEMA_VERSION, "command": "archive", "archives": archives},
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            else:
                emit(render_archives(archives))
            return 0
        if args.command == "restore":
            repo = resolve_repository(args)
            active = operation_in_progress(repo.git)
            if active:
                raise Refusal(f"refusing to create a branch during a {active} operation")
            archives = list_archives(repo.git)
            matches = [
                item
                for item in archives
                if item["ref"] == args.reference or item["branch"] == args.reference
            ]
            if not matches:
                raise GitError(f"no archive found for {args.reference!r}")
            chosen = matches[0]
            target = args.branch or chosen["branch"]
            check_branch_name(repo.git, target)
            if repo.git.run(
                "show-ref", "--verify", "--quiet", f"refs/heads/{target}", check=False
            ).returncode == 0:
                raise GitError(f"branch {target!r} already exists; choose another --branch")
            repo.git.run("update-ref", f"refs/heads/{target}", chosen["sha"])
            payload = {
                "schema": SCHEMA_VERSION,
                "command": "restore",
                "branch": target,
                "sha": chosen["sha"],
                "archive_ref": chosen["ref"],
            }
            if args.json:
                emit(json.dumps(payload, indent=2))
            else:
                emit(f"Restored {target} at {short_sha(chosen['sha'])} from {chosen['ref']}")
                emit(f"Check it out with: git switch {target}")
            return 0
    except Refusal as error:
        emit_error(f"refused: {error}")
        return 2
    except GitError as error:
        emit_error(f"error: {error}")
        return 1
    except OSError as error:
        emit_error(f"error: {error}")
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
