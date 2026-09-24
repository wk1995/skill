#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" "$tmp" <<'PY'
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
temp = Path(sys.argv[2]).resolve()
project = temp / "project"
skill = project / "skills/pr-review-loop"
(skill / "agent-builds").mkdir(parents=True)
(skill / "SKILL.md").write_text(
    '---\nname: pr-review-loop\nmetadata:\n  sync_id: "pr-review-loop"\n'
    '  version: "0.2.0"\n---\n\n# Review\n'
)
(project / "platforms/demo").mkdir(parents=True)
(project / "platforms/demo/adapter.json").write_text(json.dumps({
    "schema_version": 1, "id": "demo", "version": "1.0.0",
    "artifact_version": "1.0.0", "skills_path": "skills",
    "local_skill_roots": [{"type": "home-relative", "path": ".demo/skills"}],
}))
(project / "platforms/demo/CHANGELOG.md").write_text("## [1.0.0] - 2026-09-24\n")

cli = Path(os.environ.get("POLICY_REGRESSION_CLI", str(root / "skills/sync-skills/scripts/skill_sync.py")))
env = dict(os.environ, HOME=str(temp / "home"), PYTHONDONTWRITEBYTECODE="1")
builder_path = root / "scripts/agent_build.py"
spec = importlib.util.spec_from_file_location("policy_regression_builder", builder_path)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
builder.ROOT = project
builder.SKILLS_DIR = project / "skills"
builder.PLATFORMS_DIR = project / "platforms"
builder.DEFAULT_OUTPUT_DIR = project / "dist"
builder.build("demo", [], None, False)
built = project / "dist/demo/skills/pr-review-loop"
sys.path.insert(0, str(cli.parent))
import skill_sync as sync_module
import skill_relationships as relationships


def run(state, *arguments):
    result = subprocess.run(
        [sys.executable, str(cli), "--project-root", str(project),
         "--state-dir", str(state), *map(str, arguments)],
        cwd=temp, env=env, text=True, capture_output=True,
    )
    assert result.returncode == 0, (arguments, result.returncode, result.stderr, result.stdout)
    return json.loads(result.stdout)


def register(case, target, *, role=False):
    state = temp / case / "state"
    state.mkdir(parents=True)
    group = {"sync_id": "pr-review-loop", "name": "pr-review-loop", "snapshots": []}
    if role:
        group["roles"] = {"external": str(target)}
    else:
        group["roles"] = {}
        group["locations"] = {"install": {
            "kind": "local", "agent_id": "demo", "path": str(target),
            "derived_from": "build:demo",
        }}
    (state / "registry.json").write_text(json.dumps({"groups": {"pr-review-loop": group}}))
    return state


def installed(case, name="pr-review-loop", *, incomplete=False):
    target = temp / "home/.demo/skills" / case / name
    shutil.copytree(built, target)
    if incomplete:
        skill_file = target / "SKILL.md"
        skill_file.write_text(skill_file.read_text().replace('  sync_id: "pr-review-loop"\n', ""))
    policy = target / "pr-review-loop.yml"
    policy.write_text("comment: false\n")
    return target, policy


# A registered, incomplete Agent install is repairable. Its snapshot contains
# no local policy; rollback must keep the one in the current installation.
target, policy = installed("incomplete", incomplete=True)
state = register("incomplete", target)
repair = run(state, "repair-agent-install", "pr-review-loop", "--agent", "demo",
             "--discard-local-changes")
assert repair["snapshot"]
assert policy.read_text() == "comment: false\n"
run(state, "rollback", "pr-review-loop", "--snapshot", repair["snapshot"])
assert policy.read_text() == "comment: false\n"
repeat = run(state, "rollback", "pr-review-loop", "--snapshot", repair["snapshot"])
assert repeat["status"] == "already-current"


# A registered alias with incomplete metadata still has a stable registry ID.
# Inventory must not treat edits to its local policy as managed content edits.
target, policy = installed("incomplete-alias", "reviewer", incomplete=True)
state = register("incomplete-alias", target)
first = run(state, "relationships")
first_report = json.loads(Path(first["report_paths"]["json"]).read_text())
first_digest = first_report["skills"][0]["local_installs"][0]["digest"]
policy.write_text("comment: true\n")
second = run(state, "relationships")
second_report = json.loads(Path(second["report_paths"]["json"]).read_text())
assert second_report["skills"][0]["local_installs"][0]["digest"] == first_digest
repair = run(state, "repair-agent-install", "pr-review-loop", "--agent", "demo",
             "--discard-local-changes")
run(state, "rollback", "pr-review-loop", "--snapshot", repair["snapshot"])
assert policy.read_text() == "comment: true\n"


# An explicit Agent location can have a path independent of its stable ID.
target, policy = installed("alias", "reviewer")
state = register("alias", target)
(target / "SKILL.md").write_text((target / "SKILL.md").read_text() + "local edit\n")
run(state, "repair-agent-install", "pr-review-loop", "--agent", "demo",
    "--discard-local-changes")
assert policy.read_text() == "comment: false\n"
assert relationships.digest_tree(target) == relationships.digest_tree(built)
repeat = run(state, "repair-agent-install", "pr-review-loop", "--agent", "demo")
assert repeat["status"] == "already-current" and policy.read_text() == "comment: false\n"


# A pre-upgrade Agent snapshot includes the local policy in its digest. Restore
# managed Skill content from it while retaining the current local policy.
target, policy = installed("legacy-agent")
state = register("legacy-agent", target)
snapshot = state / "snapshots/pr-review-loop/20260924T000000Z"
payload = snapshot / "local-demo"
shutil.copytree(target, payload)
policy.write_text("comment: false\nmax_rounds: 2\n")
(target / "SKILL.md").write_text((target / "SKILL.md").read_text() + "local edit\n")
(snapshot / "manifest.json").write_text(json.dumps({
    "group": "pr-review-loop", "operation": "repair-agent-install",
    "agent_id": "demo", "original_path": relationships.normalized_absolute(target),
    "original_digest": relationships.digest_tree(payload, include_local_policy=True),
}))
payload_policy = (payload / "pr-review-loop.yml").read_bytes()
registry_before = (state / "registry.json").read_bytes()
snapshots_before = {path.name for path in snapshot.parent.iterdir()}
invalid = json.loads((snapshot / "manifest.json").read_text())
invalid["original_digest"] = "0" * 64
(snapshot / "manifest.json").write_text(json.dumps(invalid))
rejected = subprocess.run(
    [sys.executable, str(cli), "--project-root", str(project), "--state-dir", str(state),
     "rollback", "pr-review-loop", "--snapshot", snapshot.name],
    cwd=temp, env=env, text=True, capture_output=True,
)
assert rejected.returncode != 0 and "snapshot failed digest verification" in rejected.stderr
assert policy.read_text() == "comment: false\nmax_rounds: 2\n"
assert (state / "registry.json").read_bytes() == registry_before
assert {path.name for path in snapshot.parent.iterdir()} == snapshots_before
invalid["original_digest"] = relationships.digest_tree(payload, include_local_policy=True)
(snapshot / "manifest.json").write_text(json.dumps(invalid))
run(state, "rollback", "pr-review-loop", "--snapshot", snapshot.name)
assert policy.read_text() == "comment: false\nmax_rounds: 2\n"
assert (target / "SKILL.md").read_bytes() == (payload / "SKILL.md").read_bytes()
assert (payload / "pr-review-loop.yml").read_bytes() == payload_policy


# Role snapshots use a different restore path; old policy bytes must not replace
# a location's current setting.
target = temp / "roles/pr-review-loop"
shutil.copytree(built, target)
policy = target / "pr-review-loop.yml"
policy.write_text("comment: false\n")
state = register("legacy-role", target, role=True)
snapshot = state / "snapshots/pr-review-loop/20260924T000000Z"
shutil.copytree(target, snapshot / "external")
(snapshot / "external/pr-review-loop.yml").write_text("comment: true\n")
(snapshot / "manifest.json").write_text(json.dumps({"operation": "sync", "group": "pr-review-loop"}))
run(state, "rollback", "pr-review-loop", "--snapshot", snapshot.name)
assert policy.read_text() == "comment: false\n"
case_alias = target.parent / "PR-REVIEW-LOOP"
if case_alias.exists() and case_alias.samefile(target):
    sync_module.copy_skill_tree(built, case_alias)
    assert policy.read_text() == "comment: false\n"


# Same-named examples below a references directory are ordinary Skill files.
source = temp / "nested/source/demo"
source.mkdir(parents=True)
(source / "SKILL.md").write_text('---\nname: demo\nmetadata:\n  sync_id: demo\n  version: 1.0.0\n---\n')
example = source / "references/pr-review-loop/pr-review-loop.yml"
example.parent.mkdir(parents=True)
example.write_text("portable example\n")
destination = temp / "nested/target/demo"
state = temp / "nested/state"
run(state, "convert", "demo", "--source-path", source, "--source-role", "external",
    "--target-path", destination, "--target-role", "project")
assert (destination / example.relative_to(source)).read_bytes() == example.read_bytes()
sync = run(state, "sync", "demo", "--source", "external")
for role in ("external", "project"):
    preserved = state / "snapshots/demo" / sync["snapshot"] / role / example.relative_to(source)
    assert preserved.read_bytes() == example.read_bytes()
assert relationships.digest_tree(source, portable=True) == relationships.digest_tree(destination, portable=True)
print("PASS: public repair, rollback, convert, and sync preserve only the local root policy")
PY
