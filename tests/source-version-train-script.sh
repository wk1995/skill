#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import importlib.util
import io
import json
import sys
from argparse import Namespace
from pathlib import Path

root = Path(sys.argv[1])
path = root / "skills/source-version-train/scripts/code_release_train.py"
spec = importlib.util.spec_from_file_location("source_version_train", path)
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
    "baseRefName": "dev_1.4.0",
    "reviewDecision": "APPROVED",
    "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
    "url": "https://example.invalid/pr/1",
}
closed = module.inspect("acme/demo", "feature/login")
assert closed.state == "development", closed

module.find_pr = lambda repo, branch: {
    "state": "OPEN",
    "isDraft": False,
    "baseRefName": "dev/1.4.0",
    "reviewDecision": "APPROVED",
    "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
    "url": "https://example.invalid/pr/2",
}
slash = module.inspect("acme/demo", "feature/login")
assert slash.state == "misrouted" and slash.target == "dev/1.4.0", slash

module.find_pr = lambda repo, branch: {
    "state": "OPEN",
    "isDraft": False,
    "baseRefName": "dev_1.4.0",
    "reviewDecision": "APPROVED",
    "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
    "url": "https://example.invalid/pr/3",
}
underscore = module.inspect("acme/demo", "feature/login")
assert underscore.state == "ready" and underscore.target == "dev_1.4.0", underscore


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

for rejected in ("latest", "dev", "1", "1.4", "1.4.0-rc.1", "01.4.0", "1.01.0", "1.", ""):
    try:
        module.require_numeric_version(rejected)
    except RuntimeError:
        continue
    raise AssertionError(f"accepted version {rejected!r}")
for accepted in ("0.1.0", "1.4.0", "5.1.3", "10.20.30"):
    assert module.require_numeric_version(accepted) == accepted

for command in ("initialize", "reuse", "tag"):
    try:
        module.accept_version(Namespace(command=command, version="latest"))
    except RuntimeError:
        pass
    else:
        raise AssertionError(f"{command} accepted a named version")
    buffer = io.StringIO()
    stdout = sys.stdout
    sys.stdout = buffer
    try:
        assert getattr(module, command)(Namespace(command=command, version="1.4.0")) == 0
    finally:
        sys.stdout = stdout
    payload = json.loads(buffer.getvalue())
    assert payload["action"] == command and payload["version"] == "1.4.0", payload
PY

printf 'PASS: source-version-train script contracts\n'
