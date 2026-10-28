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

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
contract = (root / "skills/source-version-train/references/code-train-contract.md").read_text()
# Run the actual documented check, so the distributed instructions are tested.
checks = re.findall(r"```bash\n(verify_tagged_source\(\).*?)\n```", contract, re.S)
assert len(checks) == 1, "expected one executable finalization check"
bash = shutil.which("bash")
assert bash
env = os.environ.copy()
env.update({
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "Train test",
    "GIT_AUTHOR_EMAIL": "train@example.invalid",
    "GIT_COMMITTER_NAME": "Train test",
    "GIT_COMMITTER_EMAIL": "train@example.invalid",
})


def run(*args, cwd=None, input=None):
    result = subprocess.run(args, cwd=cwd, env=env, input=input, text=True, capture_output=True)
    assert result.returncode == 0, (args, result.stderr)
    return result.stdout.strip()


scenarios = [
    ("fast-forward", True),
    ("merge-commit", True),
    ("later-default-descendant", True),
    ("stale-local-tag", True),
    ("fetch-map-heads", True),
    ("fetch-map-tags", True),
    ("fetch-prune-tags", True),
    ("replace-ancestry", False),
    ("graft-ancestry", False),
    ("graft-env-ancestry", False),
    ("unmerged", False),
    ("squash", False),
    ("rebase-and-merge", False),
    ("cherry-pick", False),
    ("wrong-remote-tag", False),
    ("wrong-published-sha", False),
    ("missing-tag", False),
    ("missing-default", False),
    ("unreachable-remote", False),
    ("shallow", False),
    ("missing-git", False),
]
for tag_kind in ("lightweight", "annotated"):
    for scenario, expected in scenarios:
        with tempfile.TemporaryDirectory(prefix="train-finalization-") as raw:
            tmp = Path(raw)
            remote, local = tmp / "remote.git", tmp / "local"
            run("git", "init", "--bare", "-q", str(remote))
            tree = run("git", "-C", str(remote), "mktree", input="")

            def commit(message, *parents):
                args = ["git", "-C", str(remote), "commit-tree", tree]
                for parent in parents:
                    args.extend(["-p", parent])
                return run(*args, input=message + "\n")

            base = commit("base")
            candidate = commit("published", base)
            advanced = commit("default advanced", base)
            merged = commit("merge original candidate", advanced, candidate)
            tips = {
                "fast-forward": candidate,
                "later-default-descendant": commit("later work", merged),
                "unmerged": advanced,
                "replace-ancestry": advanced,
                "graft-ancestry": advanced,
                "graft-env-ancestry": advanced,
                # Equal trees deliberately cannot substitute for commit ancestry.
                "squash": commit("squashed publication", advanced),
                "rebase-and-merge": commit("rebased publication", advanced),
                "cherry-pick": commit("cherry-picked publication", advanced),
            }
            if scenario != "missing-default":
                run("git", "-C", str(remote), "update-ref", "refs/heads/trunk", tips.get(scenario, merged))
            for branch in ("dev_1.4.0", "publish_1.4.0", "release-candidate/1.4.0/1"):
                run("git", "-C", str(remote), "update-ref", f"refs/heads/{branch}", candidate)
            if scenario != "missing-tag":
                tagged = base if scenario == "wrong-remote-tag" else candidate
                args = ["git", "-C", str(remote), "tag"]
                if tag_kind == "annotated":
                    args.extend(["-a", "-m", "published release"])
                run(*args, "v1.4.0", tagged)

            if scenario == "shallow":
                run("git", "clone", "-q", "--depth=1", "--no-tags", "--branch", "trunk", remote.as_uri(), str(local))
            else:
                run("git", "init", "-q", str(local))
                run("git", "-C", str(local), "remote", "add", "origin", str(remote))
                run("git", "-C", str(local), "fetch", "-q", "--no-tags", "origin", "refs/heads/dev_1.4.0")
                # Misleading local success evidence must not hide a remote failure.
                run("git", "-C", str(local), "update-ref", "refs/heads/trunk", candidate)
                run("git", "-C", str(local), "tag", "v1.4.0", base if scenario == "stale-local-tag" else candidate)

            if scenario == "fetch-map-heads":
                run("git", "-C", str(local), "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*")
            if scenario == "fetch-map-tags":
                run("git", "-C", str(local), "config", "remote.origin.fetch", "+refs/tags/*:refs/tags/*")
            if scenario == "fetch-prune-tags":
                run("git", "-C", str(local), "tag", "private-local", candidate)
                run("git", "-C", str(local), "config", "fetch.prune", "true")
                run("git", "-C", str(local), "config", "fetch.pruneTags", "true")
            if scenario == "replace-ancestry":
                run("git", "-C", str(local), "fetch", "-q", "--no-tags", "origin", "refs/heads/trunk")
                forged = run("git", "-C", str(local), "commit-tree", tree, "-p", candidate, input="local replacement\n")
                run("git", "-C", str(local), "replace", advanced, forged)
                # The ordinary local traversal is false evidence for remote ancestry.
                run("git", "-C", str(local), "merge-base", "--is-ancestor", candidate, advanced)
            if scenario in ("graft-ancestry", "graft-env-ancestry"):
                run("git", "-C", str(local), "fetch", "-q", "--no-tags", "origin", "refs/heads/trunk")
                graft_file = local / ".git/info/grafts" if scenario == "graft-ancestry" else tmp / "custom-grafts"
                graft_file.parent.mkdir(parents=True, exist_ok=True)
                graft_file.write_text(f"{advanced} {candidate}\n")

            def refs(repo):
                return run("git", "-C", str(repo), "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags", "refs/replace")

            before_remote, before_local = refs(remote), refs(local)
            check_env = env.copy()
            if scenario == "graft-env-ancestry":
                check_env["GIT_GRAFT_FILE"] = str(graft_file)
            if scenario == "missing-git":
                empty_bin = tmp / "empty-bin"
                empty_bin.mkdir()
                check_env["PATH"] = str(empty_bin)
            remote_arg = str(tmp / "absent.git") if scenario == "unreachable-remote" else "origin"
            expected_sha = base if scenario == "wrong-published-sha" else candidate
            for attempt in range(2):
                result = subprocess.run(
                    [bash, "-c", checks[0] + '\nverify_tagged_source "$1" "$2" "$3" "$4"',
                     "verify", remote_arg, "trunk", "v1.4.0", expected_sha],
                    cwd=local, env=check_env, text=True, capture_output=True,
                )
                assert (result.returncode == 0) == expected, (tag_kind, scenario, attempt, result.stdout, result.stderr)
                assert ("verified candidate=" in result.stdout) == expected, (scenario, result.stdout)
                assert refs(remote) == before_remote, (scenario, "remote refs changed")
                assert refs(local) == before_local, (scenario, "local branch or tag changed")
            print(f"PASS: {tag_kind} {scenario} (repeat preserves branches and tags)")
PY

printf 'PASS: source-version-train script contracts\n'
