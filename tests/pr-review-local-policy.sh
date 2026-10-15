#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" "$tmp" <<'PY'
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
temp = Path(sys.argv[2]).resolve()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("agent_build_local_policy_test", root / "scripts/agent_build.py")
sys.path.insert(0, str(root / "skills/sync-skills/scripts"))
sync = load("skill_sync_local_policy_test", root / "skills/sync-skills/scripts/skill_sync.py")
relationships = sys.modules["skill_relationships"]

project = temp / "project"
skill = project / "skills/pr-review-loop"
(skill / "agent-builds").mkdir(parents=True)
(skill / "SKILL.md").write_text(
    '---\nname: pr-review-loop\ndescription: Review a PR.\nmetadata:\n'
    '  sync_id: "pr-review-loop"\n  version: "0.2.0"\n---\n\n# Review\n'
)
policy = skill / "pr-review-loop.yml"
policy.write_text("comment: true\nmax_rounds: 3\n")
(skill / "references").mkdir()
(skill / "references/pr-review-loop.yml").write_text("portable example\n")
(project / ".gitignore").write_text("/skills/pr-review-loop/pr-review-loop.yml\n")
subprocess.run(["git", "init", "-q", str(project)], check=True)
assert subprocess.run(["git", "check-ignore", "-q", str(policy)], cwd=project).returncode == 0
subprocess.run(["git", "add", ".gitignore", "skills/pr-review-loop/SKILL.md"], cwd=project, check=True)
assert not subprocess.check_output(["git", "ls-files", "--", str(policy)], cwd=project)
assert subprocess.run(["git", "add", str(policy)], cwd=project, capture_output=True).returncode != 0

platform = project / "platforms/demo"
platform.mkdir(parents=True)
(platform / "adapter.json").write_text(json.dumps({
    "schema_version": 1, "id": "demo", "version": "1.0.0",
    "artifact_version": "1.0.0", "skills_path": "skills",
    "local_skill_roots": [{"type": "home-relative", "path": ".demo/skills"}],
}))
(platform / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0] - 2026-09-24\n")
builder.ROOT = project
builder.SKILLS_DIR = project / "skills"
builder.PLATFORMS_DIR = project / "platforms"
builder.DEFAULT_OUTPUT_DIR = project / "dist"
output = builder.build("demo", [], None, False)
manifest = (output / ".agent-build.json").read_bytes()
assert not (output / "skills/pr-review-loop/pr-review-loop.yml").exists()
assert (output / "skills/pr-review-loop/references/pr-review-loop.yml").read_text() == "portable example\n"

policy.write_text("comment: false\nmax_rounds: 1\n")
builder.build("demo", [], None, True)
assert (output / ".agent-build.json").read_bytes() == manifest
assert not (output / "skills/pr-review-loop/pr-review-loop.yml").exists()

target = temp / "other-project/pr-review-loop"
target.mkdir(parents=True)
(target / "SKILL.md").write_text("old source\n")
target_policy = target / "pr-review-loop.yml"
target_policy.write_text("comment: true\nmax_rounds: 7\n")
source_digest = sync.digest_skill_dir(skill)
portable_digest = relationships.digest_tree(skill, portable=True)
sync.copy_skill_tree(skill, target)
assert target_policy.read_text() == "comment: true\nmax_rounds: 7\n"

# Repair and rollback use the same installer and must retain an installation's
# own machine policy through replacement and failed validation.
built_skill = output / "skills/pr-review-loop"
built_digest = relationships.digest_tree(built_skill)
sync.atomic_install_build(built_skill, target, "pr-review-loop", built_digest)
assert target_policy.read_text() == "comment: true\nmax_rounds: 7\n"
assert relationships.digest_tree(target) == built_digest
sync.atomic_install_build(built_skill, target, "pr-review-loop", built_digest)
assert target_policy.read_text() == "comment: true\nmax_rounds: 7\n"
try:
    sync.atomic_install_build(built_skill, target, "pr-review-loop", "wrong digest")
except SystemExit as error:
    assert "digest" in str(error)
else:
    raise AssertionError("invalid build digest must be rejected")
assert target_policy.read_text() == "comment: true\nmax_rounds: 7\n"
assert relationships.digest_tree(target) == built_digest
target_policy.unlink()
target_policy.symlink_to(policy)
try:
    sync.atomic_install_build(built_skill, target, "pr-review-loop", built_digest)
except SystemExit as error:
    assert "regular file" in str(error)
else:
    raise AssertionError("symlinked local policy must be rejected")
assert target_policy.is_symlink()
target_policy.unlink()
target_policy.write_text("comment: true\nmax_rounds: 7\n")
assert (target / "SKILL.md").read_bytes() == (skill / "SKILL.md").read_bytes()
assert sync.digest_skill_dir(target) == source_digest
assert relationships.digest_tree(target, portable=True) == portable_digest
assert policy.read_text() == "comment: false\nmax_rounds: 1\n"
sync.copy_skill_tree(skill, target)
assert target_policy.read_text() == "comment: true\nmax_rounds: 7\n"

# Removing the default ignore rule permits a shared policy to be committed.
(project / ".gitignore").write_text("")
subprocess.run(["git", "add", ".gitignore", "skills/pr-review-loop/pr-review-loop.yml"], cwd=project, check=True)
assert subprocess.check_output(["git", "ls-files", "--", str(policy)], cwd=project).strip()
builder.build("demo", [], None, True)
assert (output / ".agent-build.json").read_bytes() == manifest
assert not (output / "skills/pr-review-loop/pr-review-loop.yml").exists()
print("PASS: project policy can be private or tracked, but never enters builds or Skill copies")
PY
