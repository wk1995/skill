#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/skills/sync-skills/scripts/skill_sync.py"

python3 - "$SCRIPT" "$ROOT" <<'PY'
import importlib.util
import sys
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

print("PASS: sync-skills version policy")
PY
