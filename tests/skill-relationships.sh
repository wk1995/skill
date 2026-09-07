#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SYNC="$ROOT/skills/sync-skills/scripts/skill_sync.py"
RELATIONSHIPS="$ROOT/skills/sync-skills/scripts/skill_relationships.py"
BUILD="$ROOT/scripts/agent_build.py"

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" "$SYNC" "$RELATIONSHIPS" "$BUILD" <<'PY'
import contextlib
import copy
import fcntl
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

repository_root = Path(sys.argv[1])
sync_path = Path(sys.argv[2])
relationships_path = Path(sys.argv[3])
build_path = Path(sys.argv[4])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skill_sync = load("skill_sync_relationship_tests", sync_path)
relationships = sys.modules["skill_relationships"]
agent_build = load("agent_build_relationship_tests", build_path)


def write_skill(path, name, version, sync_id=None, extra=""):
    path.mkdir(parents=True, exist_ok=True)
    (path / "agent-builds").mkdir(exist_ok=True)
    sync_line = f'  sync_id: "{sync_id or name}"\n' if sync_id is not False else ""
    (path / "SKILL.md").write_text(
        f"""---
name: {name}
description: Test {name} relationship behavior.
metadata:
{sync_line}  version: "{version}"
---

# {name}

{extra}
""",
        encoding="utf-8",
    )


def write_adapter(project, agent_id, skills_path, local_path):
    platform = project / "platforms" / agent_id
    platform.mkdir(parents=True)
    (platform / "adapter.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": agent_id,
                "version": "1.0.0",
                "artifact_version": "1.0.0",
                "skills_path": skills_path,
                "skill_append": "SKILL.append.md",
                "local_skill_roots": [{"type": "env", "name": local_path, "required": True}],
            }
        ),
        encoding="utf-8",
    )
    (platform / "SKILL.append.md").write_text(
        f"## {agent_id} adaptation\n",
        encoding="utf-8",
    )
    (platform / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-09-07\n\n- Initial adapter.\n",
        encoding="utf-8",
    )


def configure_builder(project):
    agent_build.ROOT = project
    agent_build.SKILLS_DIR = project / "skills"
    agent_build.PLATFORMS_DIR = project / "platforms"
    agent_build.DEFAULT_OUTPUT_DIR = project / "dist"


def run_command(argv):
    args = skill_sync.build_parser().parse_args(argv)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = args.func(args)
    value = json.loads(output.getvalue()) if output.getvalue() else None
    return code, value


def rejects(argv, fragment):
    try:
        run_command(argv)
    except SystemExit as error:
        assert fragment in str(error), str(error)
    else:
        raise AssertionError(f"expected rejection containing {fragment!r}: {argv}")


with tempfile.TemporaryDirectory() as raw_tmp:
    temp = Path(raw_tmp).resolve()
    project = temp / "skill-project"
    project.mkdir()
    (project / ".git").mkdir()
    codex_local = temp / "home" / ".codex" / "skills"
    workbuddy_local = temp / "home" / ".agents" / "skills"
    codex_local.mkdir(parents=True)
    workbuddy_local.mkdir(parents=True)
    environment = {
        "HOME": str(temp / "home"),
        "CODEX_TEST_SKILLS": str(codex_local),
        "WORKBUDDY_TEST_SKILLS": str(workbuddy_local),
    }
    write_adapter(project, "codex", "skills", "CODEX_TEST_SKILLS")
    write_adapter(project, "workbuddy", ".", "WORKBUDDY_TEST_SKILLS")

    write_skill(project / "skills" / "alpha", "alpha", "1.0.0")
    write_skill(project / "skills" / "gamma", "gamma", "0.9.0")
    configure_builder(project)
    with patch.dict(os.environ, environment, clear=False):
        agent_build.build("workbuddy", [], None, False)

    write_skill(project / "skills" / "gamma", "gamma", "1.0.0", extra="Portable update.")
    write_skill(project / "skills" / "beta", "beta", "2.0.0")
    with patch.dict(os.environ, environment, clear=False):
        agent_build.build("codex", [], None, False)

    shutil.copytree(project / "dist" / "codex" / "skills" / "alpha", codex_local / "alpha")
    shutil.copytree(project / "dist" / "codex" / "skills" / "gamma", codex_local / "gamma")
    gamma_skill = codex_local / "gamma" / "SKILL.md"
    gamma_skill.write_text(
        gamma_skill.read_text(encoding="utf-8").replace('  sync_id: "gamma"\n', "") + "Local-only change.\n",
        encoding="utf-8",
    )
    write_skill(codex_local / "unlinked", "unlinked", "1.2.3")

    related_root = temp / "app-a" / "skills"
    shutil.copytree(project / "skills" / "alpha", related_root / "alpha")
    second_related_root = temp / "app-b" / "skills"
    shutil.copytree(project / "skills" / "alpha", second_related_root / "alpha")
    unregistered_root = temp / "projects" / "unregistered" / "skills"
    write_skill(unregistered_root / "never-scan", "never-scan", "1.0.0")

    state = temp / "state"
    registry = {
        "groups": {
            "alpha": {
                "sync_id": "alpha",
                "name": "alpha",
                "roles": {"repo": str(project / "skills" / "alpha")},
                "snapshots": [],
            },
            "gamma": {
                "sync_id": "gamma",
                "name": "gamma",
                "roles": {
                    "repo": str(project / "skills" / "gamma"),
                    "local": str(codex_local / "gamma"),
                },
                "locations": {
                    "local:codex": {
                        "kind": "local",
                        "agent_id": "codex",
                        "derived_from": "build:codex",
                        "path": str(codex_local / "gamma"),
                    }
                },
                "snapshots": [],
            },
        }
    }
    state.mkdir()
    registry_path = state / "registry.json"
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry_before = registry_path.read_bytes()

    with patch.dict(os.environ, environment, clear=False):
        report, paths = relationships.generate_and_write(
            project_root=project,
            state_dir=state,
            registry=copy.deepcopy(registry),
            project_args=[f"app-a={related_root}", f"app-b={second_related_root}"],
        )
    assert registry_path.read_bytes() == registry_before, "report generation must not mutate registry"
    assert [builder["id"] for builder in report["agent_builders"]] == ["codex", "workbuddy"]
    skills = {skill["sync_id"]: skill for skill in report["skills"]}
    assert skills["alpha"]["statuses"] == ["synced"]
    assert set(skills["beta"]["statuses"]) == {"agent-build-partial", "project-only"}
    assert "agent-version-diverged" in skills["gamma"]["statuses"]
    assert "agent-build-stale" in skills["gamma"]["statuses"]
    assert "missing-sync-id" in skills["gamma"]["statuses"]
    assert "agent-install-diverged" in skills["gamma"]["statuses"]
    assert {item["name"] for item in report["unlinked_local_skills"]} == {"unlinked"}
    assert "never-scan" not in skills
    assert report["summary"]["related_project_count"] == 2
    assert {location["project_id"] for location in skills["alpha"]["locations"]} == {"app-a", "app-b"}
    assert report["summary"]["local_skill_count"] == 3
    for output_path in paths.values():
        assert stat.S_IMODE(Path(output_path).stat().st_mode) == 0o600
    assert stat.S_IMODE((state / "reports").stat().st_mode) == 0o700
    markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
    assert "| Sync ID |" in markdown and "| codex | workbuddy |" in markdown
    assert sum(line.startswith("| ---") for line in markdown.splitlines()) == 1, "Markdown must have one regular table"
    assert str(codex_local / "gamma") in markdown

    # Format selection and supplemental local roots affect only the requested report files.
    supplemental_root = temp / "supplemental-codex-skills"
    write_skill(supplemental_root / "override-only", "override-only", "1.0.0")
    json_only = temp / "json-only"
    with patch.dict(os.environ, environment, clear=False):
        supplemental_report, supplemental_paths = relationships.generate_and_write(
            project_root=project,
            state_dir=state,
            registry=copy.deepcopy(registry),
            local_root_args=[f"codex={supplemental_root}"],
            output_dir=json_only,
            output_format="json",
        )
    assert set(supplemental_paths) == {"json"}
    assert not (json_only / "skill-relationships.md").exists()
    assert "override-only" in {item["name"] for item in supplemental_report["unlinked_local_skills"]}

    markdown_only = temp / "markdown-only"
    with patch.dict(os.environ, environment, clear=False):
        _, markdown_paths = relationships.generate_and_write(
            project_root=project,
            state_dir=state,
            registry=copy.deepcopy(registry),
            output_dir=markdown_only,
            output_format="markdown",
        )
    assert set(markdown_paths) == {"markdown"}
    assert not (markdown_only / "skill-relationships.json").exists()

    # Required env roots and legacy build manifests fail closed as inventory inputs.
    try:
        relationships.load_adapters(project, [], {"HOME": environment["HOME"]})
    except relationships.RelationshipError as error:
        assert "required adapter root environment variable" in str(error)
    else:
        raise AssertionError("missing required Agent root environment variable must fail")

    codex_manifest_path = project / "dist" / "codex" / ".agent-build.json"
    codex_manifest_bytes = codex_manifest_path.read_bytes()
    legacy_manifest = json.loads(codex_manifest_bytes)
    legacy_manifest["schema_version"] = 1
    codex_manifest_path.write_text(json.dumps(legacy_manifest), encoding="utf-8")
    with patch.dict(os.environ, environment, clear=False):
        legacy_report = relationships.build_report(project, state, copy.deepcopy(registry))
    assert any(
        issue["code"] == "agent-build-invalid" and issue.get("agent_id") == "codex"
        for issue in legacy_report["issues"]
    )
    assert all(not cell["present"] for skill in legacy_report["skills"] for agent, cell in skill["agent_builds"].items() if agent == "codex")
    codex_manifest_path.write_bytes(codex_manifest_bytes)

    # The CLI returns strict findings after still writing a complete report.
    with patch.dict(os.environ, environment, clear=False):
        code, cli_result = run_command(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "relationships",
                "--project", f"app-a={related_root}",
                "--strict",
            ]
        )
    assert code == 2 and cli_result["report_status"] == "fresh"

    # A report path inside the repository is rejected before it is created.
    with patch.dict(os.environ, environment, clear=False):
        rejects(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "relationships",
                "--output-dir", str(project / "reports"),
            ],
            "protected path",
        )
    assert not (project / "reports").exists()

    # Symlinked output directories, special report targets, and a held writer lock fail closed.
    symlink_output = temp / "symlink-output"
    symlink_output.symlink_to(state / "reports", target_is_directory=True)
    try:
        relationships.write_reports(
            report,
            output_dir=symlink_output,
            state_dir=state,
            project_root=project,
            output_format="both",
        )
    except relationships.RelationshipError as error:
        assert "symlink" in str(error) or "protected path" in str(error)
    else:
        raise AssertionError("symlinked report output must be rejected")

    fifo_output = temp / "fifo-output"
    fifo_output.mkdir()
    fifo_target = fifo_output / "skill-relationships.json"
    os.mkfifo(fifo_target)
    try:
        relationships.write_reports(
            report,
            output_dir=fifo_output,
            state_dir=state,
            project_root=project,
            output_format="json",
        )
    except relationships.RelationshipError as error:
        assert "regular file" in str(error)
    else:
        raise AssertionError("FIFO report target must be rejected")

    lock_path = state / ".relationships.lock"
    with lock_path.open("a+", encoding="utf-8") as held_lock:
        fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            relationships.write_reports(
                report,
                output_dir=state / "reports",
                state_dir=state,
                project_root=project,
                output_format="both",
            )
        except relationships.RelationshipError as error:
            assert "already running" in str(error)
        else:
            raise AssertionError("concurrent report writer must be rejected")

    # Failure while replacing the second report restores the first report too.
    original_json = (state / "reports" / "skill-relationships.json").read_bytes()
    original_markdown = (state / "reports" / "skill-relationships.md").read_bytes()
    changed = copy.deepcopy(report)
    changed["generated_at"] = "2026-09-07T09:00:00Z"
    real_replace = relationships.os.replace
    failure = {"raised": False}

    def fail_markdown_once(source, target):
        if str(target).endswith("skill-relationships.md") and not failure["raised"]:
            failure["raised"] = True
            raise OSError("simulated Markdown replacement failure")
        return real_replace(source, target)

    with patch.object(relationships.os, "replace", side_effect=fail_markdown_once):
        try:
            relationships.write_reports(
                changed,
                output_dir=state / "reports",
                state_dir=state,
                project_root=project,
                output_format="both",
            )
        except OSError as error:
            assert "simulated" in str(error)
        else:
            raise AssertionError("injected report replacement failure must escape")
    assert (state / "reports" / "skill-relationships.json").read_bytes() == original_json
    assert (state / "reports" / "skill-relationships.md").read_bytes() == original_markdown

    # Register a related project explicitly; the persisted project root is scanned on refresh.
    with patch.dict(os.environ, environment, clear=False):
        code, linked = run_command(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "link-location", "alpha",
                "--location-id", "project:app-a",
                "--kind", "project",
                "--project-id", "app-a",
                "--path", str(related_root / "alpha"),
            ]
        )
    assert code == 0 and linked["report_status"] == "fresh"
    persisted = json.loads(registry_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert persisted["groups"]["alpha"]["locations"]["project:app-a"]["project_id"] == "app-a"
    assert persisted["projects"]["app-a"]["skill_roots"] == [str(related_root)]

    # Portable repo sync must fail before snapshotting an Agent installation directory.
    persisted["groups"]["alpha"]["roles"]["local"] = str(codex_local / "alpha")
    registry_path.write_text(json.dumps(persisted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    snapshots_before = list((state / "snapshots" / "alpha").glob("*")) if (state / "snapshots" / "alpha").exists() else []
    with patch.dict(os.environ, environment, clear=False):
        rejects(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "sync", "alpha", "--source", "repo",
            ],
            "repair-agent-install",
        )
    snapshots_after = list((state / "snapshots" / "alpha").glob("*")) if (state / "snapshots" / "alpha").exists() else []
    assert snapshots_after == snapshots_before

    # A divergent/incomplete install is preserved without explicit replacement authorization.
    with patch.dict(os.environ, environment, clear=False):
        rejects(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "repair-agent-install", "gamma", "--agent", "codex",
            ],
            "existing copy was preserved",
        )
    assert 'sync_id: "gamma"' not in gamma_skill.read_text(encoding="utf-8")
    gamma_snapshots = state / "snapshots" / "gamma"
    assert not gamma_snapshots.exists()

    with patch.dict(os.environ, environment, clear=False):
        code, repaired = run_command(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "repair-agent-install", "gamma", "--agent", "codex",
                "--discard-local-changes",
            ]
        )
    assert code == 0 and repaired["status"] == "reinstalled"
    assert repaired["snapshot"]
    assert skill_sync.read_skill_metadata(codex_local / "gamma")["sync_id"] == "gamma"
    assert relationships.digest_tree(codex_local / "gamma") == relationships.digest_tree(project / "dist" / "codex" / "skills" / "gamma")
    snapshot_names = sorted(path.name for path in gamma_snapshots.iterdir())

    with patch.dict(os.environ, environment, clear=False):
        code, repeated = run_command(
            [
                "--state-dir", str(state),
                "--project-root", str(project),
                "repair-agent-install", "gamma", "--agent", "codex",
            ]
        )
    assert code == 0 and repeated["status"] == "already-current" and repeated["snapshot"] is None
    assert sorted(path.name for path in gamma_snapshots.iterdir()) == snapshot_names

    # A successful sync is retained when automatic report refresh fails.
    external = temp / "external-alpha"
    shutil.copytree(project / "skills" / "alpha", external)
    (external / "old.txt").write_text("old\n", encoding="utf-8")
    persisted = json.loads(registry_path.read_text(encoding="utf-8"))
    persisted["groups"]["alpha"]["roles"] = {
        "repo": str(project / "skills" / "alpha"),
        "external": str(external),
    }
    registry_path.write_text(json.dumps(persisted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with patch.dict(os.environ, environment, clear=False):
        with patch.object(skill_sync, "generate_and_write", side_effect=relationships.RelationshipError("injected refresh failure")):
            code, stale = run_command(
                [
                    "--state-dir", str(state),
                    "--project-root", str(project),
                    "sync", "alpha", "--source", "repo",
                ]
            )
    assert code == 2 and stale["report_status"] == "stale"
    assert "relationships" in stale["report_retry_command"]
    assert skill_sync.digest_skill_dir(external) == skill_sync.digest_skill_dir(project / "skills" / "alpha")
    assert json.loads(registry_path.read_text(encoding="utf-8"))["groups"]["alpha"]["last_sync"]

print("PASS: relationship discovery, reporting, refresh, safety, and Agent install repair")
PY
