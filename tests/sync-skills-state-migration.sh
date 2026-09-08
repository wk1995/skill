#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/skills/sync-skills/scripts/skill_sync.py"

PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT" <<'PY'
import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

script = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("skill_sync", script)
skill_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(skill_sync)


def run(argv: list[str]) -> tuple[int, dict]:
    args = skill_sync.build_parser().parse_args(argv)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = args.func(args)
    return result, json.loads(output.getvalue())


def rejects(argv: list[str], expected: str) -> None:
    try:
        run(argv)
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection containing {expected!r}: {argv}")


with tempfile.TemporaryDirectory() as raw_tmp:
    tmp = Path(raw_tmp)
    repo = tmp / "demo repo"
    nested = repo / "skills" / "demo"
    nested.mkdir(parents=True)
    (repo / ".git").mkdir()
    xdg = tmp / "xdg-state"
    expected_default = skill_sync.default_state_dir(
        nested,
        {"HOME": str(tmp / "home"), "XDG_STATE_HOME": str(xdg)},
    )
    expected_suffix = skill_sync.hashlib.sha256(os.fsencode(str(repo.resolve()))).hexdigest()[:16]
    assert expected_default.parent == xdg.resolve() / "sync-skills"
    assert expected_default.name == f"demo-repo-{expected_suffix}"

    try:
        skill_sync.default_state_dir(repo, {"HOME": str(tmp), "XDG_STATE_HOME": "relative"})
    except SystemExit as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("relative XDG_STATE_HOME must be rejected")

    try:
        skill_sync.default_state_dir(repo, {"HOME": str(tmp), "XDG_STATE_HOME": str(repo / ".state")})
    except SystemExit as exc:
        assert "outside the repository" in str(exc)
    else:
        raise AssertionError("a repository-internal default state directory must be rejected")

    legacy = repo / ".skill-sync"
    snapshot = legacy / "snapshots" / "demo" / "20260907T000000Z"
    snapshot.mkdir(parents=True)
    (legacy / "registry.json").write_text('{"groups": malformed-but-preserved}\n', encoding="utf-8")
    executable = snapshot / "restore.sh"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o751)
    destination = tmp / "external-state"
    before = skill_sync.state_tree_manifest(legacy)

    rejects([
        "--state-dir", str(legacy), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ], "are the same")

    linked_destination = tmp / "linked-destination"
    os.symlink(legacy, linked_destination)
    rejects([
        "--state-dir", str(linked_destination), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ], "are the same")

    code, first = run([
        "--state-dir", str(destination), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ])
    assert code == 0
    assert first["status"] == "migrated"
    assert first["source_preserved"] is True
    assert skill_sync.state_tree_manifest(legacy) == before
    assert skill_sync.state_tree_manifest(destination) == before
    assert stat.S_IMODE((destination / executable.relative_to(legacy)).stat().st_mode) == 0o751

    code, second = run([
        "--state-dir", str(destination), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ])
    assert code == 0
    assert second["status"] == "already-migrated"
    assert skill_sync.state_tree_manifest(legacy) == before
    assert skill_sync.state_tree_manifest(destination) == before

    (destination / "conflict.txt").write_text("do not overwrite\n", encoding="utf-8")
    conflict_before = skill_sync.state_tree_manifest(destination)
    rejects([
        "--state-dir", str(destination), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ], "different content")
    assert skill_sync.state_tree_manifest(legacy) == before
    assert skill_sync.state_tree_manifest(destination) == conflict_before
    assert not list(destination.parent.glob(".sync-skills-migrate-*"))

    file_target = tmp / "state-file"
    file_target.write_text("preserve\n", encoding="utf-8")
    rejects([
        "--state-dir", str(file_target), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ], "not a directory")
    assert file_target.read_text(encoding="utf-8") == "preserve\n"

    rejects([
        "--state-dir", str(legacy / "nested-target"), "migrate-state",
        "--legacy-state-dir", str(legacy),
    ], "inside the legacy state directory")

    outer = tmp / "outer-state"
    inner_legacy = outer / "legacy"
    inner_legacy.mkdir(parents=True)
    (inner_legacy / "registry.json").write_text("{}\n", encoding="utf-8")
    rejects([
        "--state-dir", str(outer), "migrate-state",
        "--legacy-state-dir", str(inner_legacy),
    ], "inside the destination state directory")
    assert (inner_legacy / "registry.json").read_text(encoding="utf-8") == "{}\n"

    linked_source = tmp / "linked-source"
    os.symlink(legacy, linked_source)
    rejects([
        "--state-dir", str(tmp / "linked-copy"), "migrate-state",
        "--legacy-state-dir", str(linked_source),
    ], "must not be a symlink")

    source_with_link = tmp / "source-with-link"
    source_with_link.mkdir()
    os.symlink(legacy / "registry.json", source_with_link / "registry.json")
    rejects([
        "--state-dir", str(tmp / "linked-entry-copy"), "migrate-state",
        "--legacy-state-dir", str(source_with_link),
    ], "contains a symlink")
    assert not (tmp / "linked-entry-copy").exists()

    case_source = tmp / "case-state"
    case_destination = tmp / "CASE-STATE"
    case_source.mkdir()
    (case_source / "registry.json").write_text("{}\n", encoding="utf-8")
    original_samefile = skill_sync.os.path.samefile
    simulated_case_insensitive = not case_destination.exists()
    if simulated_case_insensitive:
        case_destination.mkdir()
        case_paths = {str(case_source.resolve()), str(case_destination.resolve())}

        def case_insensitive_samefile(first, second):
            resolved = {str(Path(first).resolve()), str(Path(second).resolve())}
            if resolved == case_paths:
                return True
            return original_samefile(first, second)

        skill_sync.os.path.samefile = case_insensitive_samefile
    else:
        assert original_samefile(case_source, case_destination)
    rejects([
        "--state-dir", str(case_destination), "migrate-state",
        "--legacy-state-dir", str(case_source),
    ], "are the same")
    if simulated_case_insensitive:
        skill_sync.os.path.samefile = original_samefile
    assert (case_source / "registry.json").read_text(encoding="utf-8") == "{}\n"

    failed_destination = tmp / "failed-copy"

    def fail_during_copy(source, target, **kwargs):
        target.mkdir()
        (target / "partial.txt").write_text("partial\n", encoding="utf-8")
        raise OSError("simulated copy failure")

    with patch.object(skill_sync.shutil, "copytree", side_effect=fail_during_copy):
        try:
            skill_sync.migrate_state_tree(legacy, failed_destination)
        except OSError as exc:
            assert "simulated copy failure" in str(exc)
        else:
            raise AssertionError("copy failure must be reported")
    assert not failed_destination.exists()
    assert skill_sync.state_tree_manifest(legacy) == before
    assert not list(tmp.glob(".sync-skills-migrate-*"))

    rejects([
        "--state-dir", str(tmp / "missing-copy"), "migrate-state",
        "--legacy-state-dir", str(tmp / "missing"),
    ], "does not exist")

print("PASS: sync-skills external state migration is verified, non-destructive, and idempotent")
PY

MIGRATION_FIXTURE="$(mktemp -d)"
cleanup() {
  rm -rf -- "$MIGRATION_FIXTURE"
}
trap cleanup EXIT

mkdir -p "$MIGRATION_FIXTURE/legacy"
printf '{"groups": {}}\n' > "$MIGRATION_FIXTURE/legacy/registry.json"
PYTHON_BIN="$(command -v python3)"
PATH="$MIGRATION_FIXTURE/no-tools" PYTHONDONTWRITEBYTECODE=1 \
  "$PYTHON_BIN" "$SCRIPT" \
  --state-dir "$MIGRATION_FIXTURE/external" \
  migrate-state --legacy-state-dir "$MIGRATION_FIXTURE/legacy" >/dev/null
test -f "$MIGRATION_FIXTURE/external/registry.json"

echo "PASS: sync-skills state migration does not depend on optional executables"
