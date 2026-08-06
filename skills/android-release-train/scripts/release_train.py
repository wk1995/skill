#!/usr/bin/env python3
"""Read-only GitHub branch/PR inventory for Android release trains."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


def run(*args: str) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    return result.stdout


def gh_json(*args: str) -> Any:
    return json.loads(run("gh", *args))


def resolve_repo(explicit: str | None) -> str:
    if explicit:
        return explicit
    return run("gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()


def list_branches() -> list[str]:
    refs = run("git", "ls-remote", "--heads", "origin", "feature/*", "bugfix/*")
    return sorted(line.split("refs/heads/", 1)[1] for line in refs.splitlines() if "refs/heads/" in line)


def checks_state(checks: list[dict[str, Any]] | None) -> str:
    if not checks:
        return "no-checks"
    conclusions = [str(check.get("conclusion") or "").upper() for check in checks]
    statuses = [str(check.get("status") or "").upper() for check in checks]
    if any(status and status != "COMPLETED" for status in statuses):
        return "pending"
    if all(conclusion == "SUCCESS" for conclusion in conclusions):
        return "success"
    return "failed"


def find_pr(repo: str, branch: str) -> dict[str, Any] | None:
    fields = "number,title,state,isDraft,baseRefName,reviewDecision,statusCheckRollup,url"
    prs = gh_json("pr", "list", "--repo", repo, "--head", branch, "--state", "all", "--limit", "100", "--json", fields)
    open_prs = [pr for pr in prs if pr.get("state") == "OPEN"]
    return open_prs[0] if open_prs else (prs[0] if prs else None)


@dataclass
class BranchStatus:
    branch: str
    state: str
    target: str
    review: str
    checks: str
    url: str


def inspect(repo: str, branch: str) -> BranchStatus:
    pr = find_pr(repo, branch)
    if not pr:
        return BranchStatus(branch, "development", "-", "-", "-", "")
    if pr.get("state") == "MERGED":
        return BranchStatus(branch, "merged", str(pr.get("baseRefName", "-")), "-", "-", str(pr.get("url", "")))
    review = str(pr.get("reviewDecision") or "PENDING").upper()
    checks = checks_state(pr.get("statusCheckRollup"))
    target = str(pr.get("baseRefName", "-"))
    if not target.startswith("dev/"):
        return BranchStatus(branch, "misrouted", target, review, checks, str(pr.get("url", "")))
    ready = not pr.get("isDraft") and review == "APPROVED" and checks == "success"
    state = "ready" if ready else ("blocked" if checks == "failed" else "pending")
    return BranchStatus(branch, state, target, review, checks, str(pr.get("url", "")))


def inventory(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    statuses = [inspect(repo, branch) for branch in list_branches()]
    if args.format == "json":
        print(json.dumps([status.__dict__ for status in statuses], ensure_ascii=False, indent=2))
        return 0
    print(f"Repository: {repo}")
    print("| Branch | State | PR target | Review | Checks |")
    print("| --- | --- | --- | --- | --- |")
    for item in statuses:
        branch = f"[{item.branch}]({item.url})" if item.url else item.branch
        print(f"| {branch} | {item.state} | {item.target} | {item.review} | {item.checks} |")
    return 0


def select(args: argparse.Namespace) -> int:
    if not args.version or not args.branches:
        raise RuntimeError("select requires --version and --branches")
    available = set(list_branches())
    requested = [branch.strip() for branch in args.branches.split(",") if branch.strip()]
    missing = sorted(set(requested) - available)
    if missing:
        raise RuntimeError(f"Branches not found on origin: {', '.join(missing)}")
    repo = resolve_repo(args.repo)
    statuses = [inspect(repo, branch) for branch in requested]
    expected_target = f"dev/{args.version}"
    conflicting = [item.branch for item in statuses if item.target not in ("-", expected_target)]
    if conflicting:
        raise RuntimeError(
            f"Feature branches have PRs outside {expected_target}; close or retarget them first: {', '.join(conflicting)}"
        )
    if args.require_ready:
        invalid = [item.branch for item in statuses if item.state != "ready" or item.target != expected_target]
        if invalid:
            raise RuntimeError(f"Not ready for integration into {expected_target}: {', '.join(invalid)}")
    print(json.dumps({"version": args.version, "branches": [item.__dict__ for item in statuses]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    repository_option = argparse.ArgumentParser(add_help=False)
    repository_option.add_argument("--repo", help="OWNER/REPO; defaults to the current gh repository")
    parser = argparse.ArgumentParser(description=__doc__, parents=[repository_option])
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory_parser = subparsers.add_parser(
        "inventory", parents=[repository_option], help="List feature and bugfix branch status"
    )
    inventory_parser.add_argument("--format", choices=("table", "json"), default="table")
    inventory_parser.set_defaults(handler=inventory)
    select_parser = subparsers.add_parser(
        "select", parents=[repository_option], help="Validate an explicit version-train selection"
    )
    select_parser.add_argument("--version", required=True)
    select_parser.add_argument("--branches", required=True, help="Comma-separated feature/bugfix branches")
    select_parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Require ready PRs targeting dev/<version>; use after train PRs have been created.",
    )
    select_parser.set_defaults(handler=select)
    args = parser.parse_args()
    try:
        return args.handler(args)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
