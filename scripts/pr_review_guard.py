#!/usr/bin/env python3
"""Check PR tree changes that are unsafe regardless of implementation details."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROTECTED_PATHS = (".skill-sync/",)


def git(
    *args: str,
    check: bool = True,
    binary: bool = False,
    env: dict[str, str] | None = None,
    input_data: str | bytes | None = None,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=not binary,
        env=env,
        input=input_data,
    )
    if check and result.returncode != 0:
        stderr = os.fsdecode(result.stderr) if binary else result.stderr
        raise RuntimeError(stderr.strip() or f"git {' '.join(args)} failed")
    return result


def changed_paths(base: str, result_tree: str, *extra: str) -> list[str]:
    result = git("diff", "--name-only", "-z", base, result_tree, "--", *extra, binary=True)
    return [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]


def unexpected_tracked_ignored_paths(result_tree: str) -> list[str]:
    """Return paths that are tracked and ignored in the simulated merge tree."""
    with tempfile.TemporaryDirectory(prefix="pr-review-guard-") as raw_tmp:
        worktree = Path(raw_tmp) / "tree"
        worktree.mkdir()

        checkout_env = os.environ.copy()
        checkout_env["GIT_INDEX_FILE"] = str(Path(raw_tmp) / "index")
        checkout_env["GIT_WORK_TREE"] = str(worktree)
        git("read-tree", result_tree, env=checkout_env)
        git("checkout-index", "--all", f"--prefix={worktree}{os.sep}", env=checkout_env)

        deterministic_env = os.environ.copy()
        deterministic_env["GIT_CONFIG_GLOBAL"] = os.devnull
        deterministic_env["GIT_CONFIG_NOSYSTEM"] = "1"
        git("-C", str(worktree), "init", "-q", env=deterministic_env)

        tracked = git("ls-tree", "-r", "--name-only", "-z", result_tree, binary=True).stdout
        result = git(
            "-C",
            str(worktree),
            "check-ignore",
            "--no-index",
            "-z",
            "--stdin",
            check=False,
            binary=True,
            env=deterministic_env,
            input_data=tracked,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(os.fsdecode(result.stderr).strip() or "git check-ignore failed")
        paths = [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]
        return [path for path in paths if not path.startswith(PROTECTED_PATHS)]


def merge_tree(base: str, head: str) -> str:
    result = git("merge-tree", "--write-tree", base, head, check=False)
    if result.returncode != 0:
        details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise RuntimeError(f"base and head cannot be merged cleanly\n{details}")
    tree = result.stdout.splitlines()[0].strip() if result.stdout else ""
    if not tree:
        raise RuntimeError("git merge-tree did not return a merged tree")
    git("cat-file", "-e", f"{tree}^{{tree}}")
    return tree


def print_review_notices(base: str, head: str) -> None:
    statuses = git("diff", "--name-status", "--find-renames", f"{base}...{head}").stdout.splitlines()
    noteworthy = [line for line in statuses if line.startswith(("D\t", "R"))]
    summary = git("diff", "--summary", f"{base}...{head}").stdout.splitlines()
    noteworthy.extend(line.strip() for line in summary if "mode change" in line)
    for line in noteworthy:
        print(f"::notice::Review noteworthy tree change: {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="base commit or ref")
    parser.add_argument("--head", default="HEAD", help="checked-out PR head commit or ref")
    args = parser.parse_args()

    try:
        base = git("rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
        head = git("rev-parse", "--verify", f"{args.head}^{{commit}}").stdout.strip()
        checked_out = git("rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
        if head != checked_out:
            raise RuntimeError("--head must resolve to the currently checked-out commit")

        print_review_notices(base, head)
        merged_tree = merge_tree(base, head)

        protected = changed_paths(base, merged_tree, *PROTECTED_PATHS)
        if protected:
            for path in protected:
                print(
                    f"::error file={path}::Protected local state changed in this PR; "
                    "use a separately designed migration instead.",
                    file=sys.stderr,
                )
            raise RuntimeError("protected .skill-sync state must have no net PR changes")

        tracked_ignored = unexpected_tracked_ignored_paths(merged_tree)
        if tracked_ignored:
            for path in tracked_ignored:
                print(
                    f"::error file={path}::Tracked files must not also be ignored by repository rules.",
                    file=sys.stderr,
                )
            raise RuntimeError("tracked ignored files outside protected legacy state are not allowed")

    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        print(f"::error::{error}", file=sys.stderr)
        return 1

    print("PASS: PR diff and simulated merge preserve protected local state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
