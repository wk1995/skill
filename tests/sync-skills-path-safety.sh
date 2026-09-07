#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/skills/sync-skills/scripts/skill_sync.py"

PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT" <<'PY'
import argparse
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path

script = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("skill_sync", script)
skill_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(skill_sync)


def skill(path: Path, name: str = "demo", sync_id=None) -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test fixture\nmetadata:\n"
        f"  sync_id: \"{sync_id or name}\"\n  version: \"0.0.1\"\n---\n",
        encoding="utf-8",
    )
    return path


def run(argv: list[str]) -> tuple[int, str]:
    args = skill_sync.build_parser().parse_args(argv)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = args.func(args)
    return result, output.getvalue()


def rejects(argv: list[str], expected: str) -> None:
    try:
        run(argv)
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection containing {expected!r}: {argv}")


with tempfile.TemporaryDirectory() as raw_tmp:
    tmp = Path(raw_tmp)
    repo = skill(tmp / "repo")
    linked = tmp / "repo-linked"
    os.symlink(repo, linked)
    state = tmp / "link-state"

    run(["--state-dir", str(state), "link", "demo", "--repo", str(repo)])
    rejects(
        ["--state-dir", str(state), "link", "demo", "--local", str(linked)],
        "roles resolve to the same path",
    )

    parent = skill(tmp / "parent", "nested")
    child = skill(parent / "child", "nested")
    nested_state = tmp / "nested-state"
    run(["--state-dir", str(nested_state), "link", "nested", "--repo", str(parent)])
    rejects(
        ["--state-dir", str(nested_state), "link", "nested", "--local", str(child)],
        "is inside role",
    )

    source = skill(tmp / "source", sync_id="convert")
    existing = skill(tmp / "existing", sync_id="convert")
    convert_state = tmp / "convert-state"
    run(["--state-dir", str(convert_state), "link", "convert", "--external", str(existing)])
    rejects(
        [
            "--state-dir", str(convert_state), "convert", "convert",
            "--source-role", "repo", "--target-role", "local",
            "--source-path", str(source), "--target-path", str(existing),
        ],
        "roles resolve to the same path",
    )

    registry = skill_sync.load_registry(convert_state)
    registry["groups"]["convert"]["roles"]["local"] = str(existing.resolve())
    skill_sync.save_registry(convert_state, registry)
    status_code, status_output = run(["--state-dir", str(convert_state), "status", "convert"])
    status = json.loads(status_output)
    assert status_code == 2
    assert status["clean"] is False
    assert status["path_issues"]

    dangerous_parent = skill(tmp / "dangerous-parent", "dangerous")
    dangerous_source = skill(dangerous_parent / "source", "dangerous")
    dangerous_state = tmp / "dangerous-state"
    skill_sync.save_registry(
        dangerous_state,
        {
            "groups": {
                "dangerous": {
                    "sync_id": "dangerous",
                    "name": "dangerous",
                    "roles": {
                        "repo": str(dangerous_source.resolve()),
                        "local": str(dangerous_parent.resolve()),
                    },
                }
            }
        },
    )
    rejects(
        ["--state-dir", str(dangerous_state), "sync", "dangerous", "--source", "repo"],
        "is inside role",
    )
    assert (dangerous_source / "SKILL.md").is_file(), "sync rejection must preserve the nested source"

    try:
        skill_sync.copy_skill_tree(dangerous_source, dangerous_parent)
    except SystemExit as exc:
        assert "source" in str(exc) and "inside" in str(exc), str(exc)
    else:
        raise AssertionError("copy_skill_tree must reject a source nested inside its target")
    assert (dangerous_source / "SKILL.md").is_file(), "copy rejection must preserve the nested source"

print("PASS: sync-skills rejects persisted, symlinked, and nested path conflicts")
PY
