#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

root = Path(sys.argv[1])
path = root / "skills/android-code-release-train/scripts/code_release_train.py"
spec = importlib.util.spec_from_file_location("android_code_release_train", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


responses = {
    (
        "gh",
        "api",
        "--paginate",
        "repos/acme/demo/git/matching-refs/heads/feature/",
        "--jq",
        ".[].ref",
    ): "refs/heads/feature/login\nrefs/heads/feature/login\n",
    (
        "gh",
        "api",
        "--paginate",
        "repos/acme/demo/git/matching-refs/heads/bugfix/",
        "--jq",
        ".[].ref",
    ): "refs/heads/bugfix/crash\n",
}
calls = []


def fake_run(*args):
    calls.append(args)
    return responses[args]


module.run = fake_run
branches = module.list_branches("acme/demo")
assert branches == [
    "bugfix/crash",
    "feature/login",
], branches
assert all(call[3].startswith("repos/acme/demo/") for call in calls)


module.find_pr = lambda repo, branch: {
    "state": "CLOSED",
    "isDraft": False,
    "baseRefName": "dev/1.4.0",
    "reviewDecision": "APPROVED",
    "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
    "url": "https://example.invalid/pr/1",
}
closed = module.inspect("acme/demo", "feature/login")
assert closed.state == "development", closed


resolved_repos = []


def fake_resolve_repo(explicit):
    return explicit or "acme/demo"


def fake_list_branches(repo):
    resolved_repos.append(repo)
    return ["feature/login"]


module.resolve_repo = fake_resolve_repo
module.list_branches = fake_list_branches
module.inspect = lambda repo, branch: module.BranchStatus(
    branch, "development", "-", "-", "-", ""
)
module.select(
    Namespace(
        repo="acme/demo",
        version="1.4.0",
        branches="feature/login",
        require_ready=False,
    )
)
assert resolved_repos == ["acme/demo"], resolved_repos
PY

printf 'PASS: android-code-release-train script contracts\n'
