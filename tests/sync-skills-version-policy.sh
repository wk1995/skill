#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/skills/sync-skills/scripts/skill_sync.py"

PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT" "$ROOT" <<'PY'
import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

script = Path(sys.argv[1])
root = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("skill_sync", script)
skill_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(skill_sync)

group = {"roles": {"repo": str(root / "skills" / "sync-skills")}}
current = {
    "repo": {"version": "0.0.2", "digest": "repo-digest", "path": str(root / "skills" / "sync-skills")},
    "local": {"version": "0.0.3", "digest": "local-digest", "path": str(root / "skills" / "sync-skills")},
}

with patch.object(skill_sync, "git_current_branch", return_value="master"), patch.object(skill_sync, "git_default_branch", return_value="main"):
    assert skill_sync.choose_source_by_version_on_mainline(group, current) == "local"

with patch.object(skill_sync, "git_current_branch", return_value="main"), patch.object(skill_sync, "git_default_branch", return_value="main"):
    assert skill_sync.choose_source_by_version_on_mainline(group, current) == "local"

with patch.object(skill_sync, "git_current_branch", return_value="feature/test"), patch.object(skill_sync, "git_default_branch", return_value="main"):
    assert skill_sync.choose_source_by_version_on_mainline(group, current) is None

conflicting = {
    "repo": {"version": "0.0.3", "digest": "repo-digest", "path": str(root / "skills" / "sync-skills")},
    "local": {"version": "0.0.3", "digest": "local-digest", "path": str(root / "skills" / "sync-skills")},
    "project": {"version": "0.0.2", "digest": "project-digest", "path": str(root / "skills" / "sync-skills")},
}

with patch.object(skill_sync, "git_current_branch", return_value="master"), patch.object(skill_sync, "git_default_branch", return_value="main"):
    try:
        skill_sync.choose_source_by_version_on_mainline(group, conflicting)
    except SystemExit as exc:
        assert "multiple roles have the highest version" in str(exc)
    else:
        raise AssertionError("expected highest-version digest conflict")

assert skill_sync.parse_version("v1.2.3") > skill_sync.parse_version("1.2.3-alpha")
assert skill_sync.parse_version("1.0.0-alpha.10") > skill_sync.parse_version("1.0.0-alpha.2")
assert skill_sync.parse_version("1.0.0-alpha.1") < skill_sync.parse_version("1.0.0-alpha.beta")
assert skill_sync.parse_version("1.2.3+build.7") == skill_sync.parse_version("1.2.3")

metadata = skill_sync.read_skill_metadata(root / "skills" / "sync-skills")
assert metadata["sync_id"] == "sync-skills"

registry = {"groups": {}}
key, created = skill_sync.get_or_create_group(registry, "stable-skill-id", "display-name")
assert key == "stable-skill-id"
assert created["sync_id"] == "stable-skill-id"
assert registry["groups"].keys() == {"stable-skill-id"}

with tempfile.TemporaryDirectory() as temp:
    state_dir = Path(temp)
    old_snapshot = state_dir / "snapshots" / "old-skill-name" / "20260904T000000Z"
    old_snapshot.mkdir(parents=True)
    registry = {
        "groups": {
            "old-skill-name": {
                "roles": {},
                "snapshots": ["20260904T000000Z"],
            }
        }
    }
    skill_sync.save_registry(state_dir, registry)
    skill_sync.command_rename(
        type(
            "Args",
            (),
            {
                "state_dir": str(state_dir),
                "group": "old-skill-name",
                "to": "stable-skill-id",
                "name": "new-skill-name",
            },
        )()
    )
    migrated = skill_sync.load_registry(state_dir)
    assert set(migrated["groups"]) == {"stable-skill-id"}
    migrated_group = migrated["groups"]["stable-skill-id"]
    assert migrated_group["sync_id"] == "stable-skill-id"
    assert migrated_group["name"] == "new-skill-name"
    assert "old-skill-name" in migrated_group["aliases"]
    assert (state_dir / "snapshots" / "stable-skill-id" / "20260904T000000Z").is_dir()

with tempfile.TemporaryDirectory() as temp:
    state_dir = Path(temp)
    registry = {
        "groups": {
            "stable-skill-id": {
                "sync_id": "stable-skill-id",
                "name": "stable-skill",
                "roles": {"repo": str(root / "skills" / "sync-skills")},
                "snapshots": [],
            }
        }
    }
    skill_sync.save_registry(state_dir, registry)
    try:
        skill_sync.command_rename(
            type(
                "Args",
                (),
                {
                    "state_dir": str(state_dir),
                    "group": "stable-skill-id",
                    "to": "another-stable-id",
                    "name": "renamed-skill",
                },
            )()
        )
    except SystemExit as exc:
        assert "immutable sync ID" in str(exc)
    else:
        raise AssertionError("changing an existing stable sync ID must fail")
    unchanged = skill_sync.load_registry(state_dir)
    assert set(unchanged["groups"]) == {"stable-skill-id"}
    assert unchanged["groups"]["stable-skill-id"]["sync_id"] == "stable-skill-id"

print("PASS: sync-skills version policy")
PY
