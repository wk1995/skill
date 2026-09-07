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

    case_root = tmp / "case-probe"
    case_lower = skill(case_root / "lower", "case-demo")
    case_variant = case_root / "LOWER"
    original_samefile = skill_sync.os.path.samefile
    simulated_case_insensitive = not case_variant.exists()
    if simulated_case_insensitive:
        skill(case_variant, "case-demo")
        aliased_paths = {str(case_lower.resolve()), str(case_variant.resolve())}

        def case_insensitive_samefile(first, second):
            resolved = {str(Path(first).resolve()), str(Path(second).resolve())}
            if resolved == aliased_paths:
                return True
            return original_samefile(first, second)

        skill_sync.os.path.samefile = case_insensitive_samefile
    else:
        assert original_samefile(case_lower, case_variant)

    case_sentinel = case_lower / "must-survive.txt"
    case_sentinel.write_text("preserve case-aliased source\n", encoding="utf-8")
    case_issues = skill_sync.role_path_issues(
        {"repo": str(case_lower), "local": str(case_variant)}
    )
    assert any("roles resolve to the same path" in issue for issue in case_issues), case_issues
    assert skill_sync.path_is_within(case_variant / "child", case_lower)
    try:
        skill_sync.copy_skill_tree(case_lower, case_variant)
    except SystemExit as exc:
        assert "onto itself" in str(exc), str(exc)
    else:
        raise AssertionError("copy_skill_tree must reject case-aliased paths")
    assert case_sentinel.read_text(encoding="utf-8") == "preserve case-aliased source\n"

    case_state = tmp / "case-state"
    skill_sync.save_registry(
        case_state,
        {
            "groups": {
                "case-demo": {
                    "sync_id": "case-demo",
                    "name": "case-demo",
                    "roles": {"repo": str(case_lower), "local": str(case_variant)},
                }
            }
        },
    )
    case_status_code, case_status_output = run(
        ["--state-dir", str(case_state), "status", "case-demo"]
    )
    case_status = json.loads(case_status_output)
    assert case_status_code == 2
    assert case_status["clean"] is False
    assert any("same path" in issue for issue in case_status["path_issues"])
    skill_sync.os.path.samefile = original_samefile

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

    rollback_snapshot = dangerous_state / "snapshots" / "dangerous" / "rollback-fixture"
    skill(rollback_snapshot / "local", "dangerous")
    unselected_content = dangerous_source / "unselected.txt"
    unselected_content.write_text("must survive rejected rollback\n", encoding="utf-8")
    rejects(
        [
            "--state-dir", str(dangerous_state), "rollback", "dangerous",
            "--snapshot", "rollback-fixture", "--roles", "local",
        ],
        "is inside role",
    )
    assert unselected_content.read_text(encoding="utf-8") == "must survive rejected rollback\n"
    assert {path.name for path in rollback_snapshot.parent.iterdir()} == {"rollback-fixture"}, (
        "rollback rejection must happen before creating a pre-rollback snapshot"
    )

    try:
        skill_sync.copy_skill_tree(dangerous_source, dangerous_parent)
    except SystemExit as exc:
        assert "source" in str(exc) and "inside" in str(exc), str(exc)
    else:
        raise AssertionError("copy_skill_tree must reject a source nested inside its target")
    assert (dangerous_source / "SKILL.md").is_file(), "copy rejection must preserve the nested source"

print("PASS: sync-skills rejects persisted, symlinked, case-aliased, and nested path conflicts")
PY
