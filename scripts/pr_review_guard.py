#!/usr/bin/env python3
"""Check PR tree changes that are unsafe regardless of implementation details."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PROTECTED_PATHS = (".skill-sync/",)
SKILL_SYNC_MIGRATION_PLAN = "migrations/skill-sync-state-v1.json"
SKILL_SYNC_IGNORE_PROBES = (
    ".skill-sync/registry.json",
    ".skill-sync/snapshots/example/manifest.json",
)


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


def tree_paths(tree: str, path: str) -> list[str]:
    result = git("ls-tree", "-r", "--name-only", "-z", tree, "--", path, binary=True)
    return [os.fsdecode(item) for item in result.stdout.split(b"\0") if item]


def tree_object(tree: str, path: str) -> str | None:
    result = git("rev-parse", "--verify", f"{tree}:{path}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def read_tree_json(tree: str, path: str) -> dict[str, object]:
    result = git("show", f"{tree}:{path}", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"migration plan is missing: {path}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"migration plan is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError("migration plan must be a JSON object")
    return value


def valid_backup_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return parsed <= datetime.now(timezone.utc)


def approved_skill_sync_removal(base: str, result_tree: str, changed: list[str]) -> tuple[bool, str]:
    """Allow one exact, acknowledged removal of the legacy tracked state tree."""
    try:
        plan = read_tree_json(base, SKILL_SYNC_MIGRATION_PLAN)
    except RuntimeError as error:
        return False, str(error)

    if tree_object(base, SKILL_SYNC_MIGRATION_PLAN) != tree_object(result_tree, SKILL_SYNC_MIGRATION_PLAN):
        return False, "migration approval must already be merged into the base and remain unchanged"

    if plan.get("schema_version") != 1 or plan.get("migration") != "skill-sync-xdg-state-v1":
        return False, "migration plan identity or schema is invalid"
    if plan.get("legacy_path") != ".skill-sync":
        return False, "migration plan must target exactly .skill-sync"
    if plan.get("status") != "approved":
        return False, "migration plan is not approved"

    expected_tree = plan.get("expected_base_tree")
    actual_tree = tree_object(base, ".skill-sync")
    if not isinstance(expected_tree, str) or expected_tree != actual_tree:
        return False, "legacy state tree does not match the reviewed migration baseline"

    required = plan.get("required_backup_confirmations")
    confirmations = plan.get("backup_confirmations")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(item, str) and item for item in required)
        or len(set(required)) != len(required)
    ):
        return False, "required backup confirmations are invalid"
    if not isinstance(confirmations, dict) or set(confirmations) != set(required):
        return False, "every required collaborator must confirm an external backup"
    if not all(valid_backup_time(value) for value in confirmations.values()):
        return False, "backup confirmations must contain non-future UTC timestamps"

    evidence = plan.get("backup_evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(required):
        return False, "every backup confirmation needs base-reviewed identity evidence"
    # These links are attestations verified by maintainers in the prior approval
    # PR. The offline guard cannot authenticate a collaborator from JSON alone.
    if not all(isinstance(url, str) and re.fullmatch(
        r"https://github\.com/[^/]+/[^/]+/(?:pull|issues)/[0-9]+#(?:issuecomment-|pullrequestreview-)[0-9]+", url
    ) for url in evidence.values()):
        return False, "backup evidence must link to an attributable GitHub comment or review"

    base_paths = tree_paths(base, ".skill-sync")
    result_paths = tree_paths(result_tree, ".skill-sync")
    if not base_paths:
        return False, "migration baseline contains no tracked legacy state"
    if result_paths:
        return False, "approved migration must remove the complete legacy state tree"
    if set(changed) != set(base_paths):
        return False, "approved migration may only delete every tracked legacy state path"
    if not all(tree_ignores_path(result_tree, path) for path in SKILL_SYNC_IGNORE_PROBES):
        return False, "legacy .skill-sync state must remain ignored after migration"
    return True, "approved exact removal with complete backup confirmations"


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


def tree_ignores_path(result_tree: str, path: str) -> bool:
    """Check ignore behavior in an isolated checkout of a result tree."""
    with tempfile.TemporaryDirectory(prefix="pr-review-ignore-") as raw_tmp:
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
        probe = worktree / path
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("migration ignore probe\n", encoding="utf-8")
        result = git(
            "-C", str(worktree), "check-ignore", "--no-index", "--quiet", path,
            check=False, env=deterministic_env,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or "git check-ignore failed")
        return result.returncode == 0


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
            removal_allowed, removal_reason = approved_skill_sync_removal(base, merged_tree, protected)
            if removal_allowed:
                print(f"::notice::Approved legacy .skill-sync migration: {removal_reason}")
            else:
                for path in protected:
                    print(
                        f"::error file={path}::Protected local state changed in this PR; "
                        f"migration approval failed: {removal_reason}.",
                        file=sys.stderr,
                    )
                raise RuntimeError(
                    "protected .skill-sync state must have no net PR changes without an approved exact migration"
                )

        tracked_ignored = unexpected_tracked_ignored_paths(merged_tree)
        if tracked_ignored:
            for path in tracked_ignored:
                print(
                    f"::error file={path}::Tracked files must not also be ignored by repository rules.",
                    file=sys.stderr,
                )
            raise RuntimeError("tracked ignored files outside protected legacy state are not allowed")

    except (RuntimeError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        print(f"::error::{error}", file=sys.stderr)
        return 1

    print("PASS: PR diff and simulated merge satisfy protected state policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
