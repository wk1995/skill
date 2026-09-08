"""Stateful regressions for PR #14 review comments; all mutations use temporary data."""
import contextlib
import copy
import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = load("sync_regressions", ROOT / "skills/sync-skills/scripts/skill_sync.py")
rel = sys.modules["skill_relationships"]
builder = load("build_regressions", ROOT / "scripts/agent_build.py")


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pr14-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / "project with spaces"
        self.local = self.root / "home/skills"
        self.local.mkdir(parents=True)
        self.state = self.root / "state"
        self.env = patch.dict(os.environ, {"HOME": str(self.root / "home"), "PR14_SKILLS": str(self.local)})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ("alpha", "gamma"):
            path = self.project / "skills" / name
            (path / "agent-builds").mkdir(parents=True)
            (path / "SKILL.md").write_text(
                f'---\nname: {name}\ndescription: Fixture.\nmetadata:\n  sync_id: "{name}"\n  version: "1.0.0"\n---\n\n# {name}\n')
        adapter = self.project / "platforms/codex"
        adapter.mkdir(parents=True)
        (adapter / "adapter.json").write_text(json.dumps({
            "id": "codex", "schema_version": 1, "version": "1.0.0", "artifact_version": "1.0.0",
            "skills_path": "skills", "local_skill_roots": [{"type": "env", "name": "PR14_SKILLS", "required": True}]}))
        (adapter / "CHANGELOG.md").write_text("## [1.0.0] - 2026-09-08\n")
        for field, value in {"ROOT": self.project, "SKILLS_DIR": self.project / "skills",
                             "PLATFORMS_DIR": self.project / "platforms", "DEFAULT_OUTPUT_DIR": self.project / "dist"}.items():
            p = patch.object(builder, field, value)
            p.start()
            self.addCleanup(p.stop)
        builder.build("codex", [], None, False)
        self.target = self.local / "alpha"
        shutil.copytree(self.project / "dist/codex/skills/alpha", self.target)
        self.registry = {"groups": {name: {"sync_id": name, "roles": {"repo": str(self.project / "skills" / name)},
                                          "snapshots": []} for name in ("alpha", "gamma")}}
        self.registry["groups"]["alpha"]["roles"]["local"] = str(self.target)
        self.save()
        self.manifest_path = self.project / "dist/codex/.agent-build.json"

    def save(self):
        sync.save_registry(self.state, self.registry)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync.main(["--project-root", str(self.project), "--state-dir", str(self.state), *argv])
        return code, json.loads(out.getvalue())

    def repair(self):
        return self.run_cli("repair-agent-install", "alpha", "--agent", "codex", "--discard-local-changes")

    def snapshot_names(self):
        return sorted(p.name for p in (self.state / "snapshots/alpha").glob("*"))

    def report(self):
        return rel.build_report(self.project, self.state, sync.load_registry(self.state))

    def test_invalid_manifest_fields_report_without_aborting(self):
        original = self.manifest_path.read_text()
        invalid = {"portable_digest": ["not-a-digest", None, [], "A" * 64],
                   "output_digest": [False, ""], "core_version": ["bad", 1],
                   "path": ["../alpha", "", ".", "/tmp/alpha", "skills//alpha", "skills\\alpha", 1],
                   "sync_id": ["Bad ID", []], "name": [None]}
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    manifest = json.loads(original)
                    manifest["skills"][0][field] = value
                    self.manifest_path.write_text(json.dumps(manifest))
                    report = self.report()
                    self.assertTrue(any(i["code"] == "agent-build-invalid" for i in report["issues"]))
                    self.assertTrue(all(not s["agent_builds"]["codex"]["present"] for s in report["skills"]))
        self.manifest_path.write_text(original)
        self.assertFalse(self.report()["issues"])

    def test_corrupt_manifest_cannot_supply_repair(self):
        (self.target / "LOCAL.txt").write_text("preserve")
        before = (self.state / "registry.json").read_bytes()
        manifest = json.loads(self.manifest_path.read_text())
        manifest["skills"][1]["output_digest"] = "0" * 64
        self.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(SystemExit, "no trusted"):
            self.repair()
        self.assertEqual((self.target / "LOCAL.txt").read_text(), "preserve")
        self.assertEqual((self.state / "registry.json").read_bytes(), before)
        self.assertFalse(self.snapshot_names())

    def test_registry_metadata_identity_conflict(self):
        for metadata_id in ("alpha", "unknown"):
            with self.subTest(metadata_id=metadata_id):
                text = (self.target / "SKILL.md").read_text().replace('sync_id: "alpha"', f'sync_id: "{metadata_id}"')
                (self.target / "SKILL.md").write_text(text)
                self.registry["groups"]["alpha"]["roles"].pop("local", None)
                self.registry["groups"]["gamma"]["roles"]["local"] = str(self.target)
                self.save()
                report = self.report()
                self.assertTrue(all(not s["local_installs"] for s in report["skills"]))
                self.assertTrue(any(i["code"] == "identity-conflict" for i in report["issues"]))
                self.assertIn("identity-conflict", report["unlinked_local_skills"][0]["statuses"])
                gamma = next(s for s in report["skills"] if s["sync_id"] == "gamma")
                self.assertIn("identity-conflict", gamma["statuses"])

    def test_unknown_cross_agent_and_outside_location_rejected_before_persist(self):
        before = (self.state / "registry.json").read_bytes()
        for agent, derived, path in (("bogus", "build:bogus", self.target),
                                     ("codex", "build:workbuddy", self.target),
                                     ("codex", "build:codex", self.root / "outside"),
                                     ("codex", "build:codex", self.local)):
            with self.subTest(agent=agent, derived=derived, path=path), self.assertRaises(SystemExit):
                self.run_cli("link-location", "alpha", "--location-id", "local:codex", "--kind", "local",
                             "--agent-id", agent, "--derived-from", derived, "--path", str(path))
            self.assertEqual((self.state / "registry.json").read_bytes(), before)
        argv = ("link-location", "alpha", "--location-id", "local:codex", "--kind", "local",
                "--agent-id", "codex", "--path", str(self.target))
        self.assertEqual(self.run_cli(*argv)[0], 0)
        self.assertEqual(self.run_cli(*argv)[0], 0)
        self.assertEqual(len(sync.load_registry(self.state)["groups"]["alpha"]["locations"]), 1)

    def test_identical_symlink_install_rejected_without_state(self):
        store = self.local / ".alpha-store"
        self.target.rename(store)
        self.target.symlink_to(store, target_is_directory=True)
        before = (self.state / "registry.json").read_bytes()
        with self.assertRaisesRegex(SystemExit, "symbolic-link"):
            self.repair()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual((self.state / "registry.json").read_bytes(), before)
        self.assertFalse(self.snapshot_names())

    def test_install_recovery_fault_matrix(self):
        original_replace = os.replace
        original_digest = sync.relationship_digest_tree
        for post_install in (False, True):
            for recovery_fails in (False, True):
                with self.subTest(post_install=post_install, recovery_fails=recovery_fails):
                    if self.target.exists():
                        shutil.rmtree(self.target)
                    shutil.copytree(self.project / "dist/codex/skills/alpha", self.target)
                    (self.target / "LOCAL.txt").write_text("preserve")
                    before = (self.state / "registry.json").read_bytes()
                    installed = False
                    def replace(source, target):
                        nonlocal installed
                        if Path(source).name == "new":
                            if not post_install:
                                raise OSError("install fault")
                            installed = True
                        if Path(source).name == "previous" and recovery_fails:
                            raise OSError("recovery fault")
                        return original_replace(source, target)
                    def digest(path):
                        if post_install and installed and Path(path) == self.target:
                            return "0" * 64
                        return original_digest(path)
                    with patch.object(os, "replace", side_effect=replace), patch.object(sync, "relationship_digest_tree", side_effect=digest):
                        with self.assertRaises(SystemExit) as failure:
                            self.repair()
                    self.assertIn("snapshot:", str(failure.exception))
                    self.assertEqual((self.state / "registry.json").read_bytes(), before)
                    if recovery_fails:
                        self.assertIn("Recovery files preserved", str(failure.exception))
                        backups = list(self.local.glob(".alpha-install-*/previous/LOCAL.txt"))
                        self.assertTrue(backups)
                        self.assertTrue(all(p.read_text() == "preserve" for p in backups))
                        for directory in self.local.glob(".alpha-install-*"):
                            shutil.rmtree(directory)
                    else:
                        self.assertEqual((self.target / "LOCAL.txt").read_text(), "preserve")
                        self.assertFalse(list(self.local.glob(".alpha-install-*")))
                    snapshot = self.state / "snapshots/alpha" / self.snapshot_names()[-1] / "local-codex/LOCAL.txt"
                    self.assertEqual(snapshot.read_text(), "preserve")

    def test_repair_snapshot_can_be_rolled_back(self):
        for legacy_role in (True, False):
            with self.subTest(legacy_role=legacy_role):
                if not legacy_role:
                    registry = sync.load_registry(self.state)
                    registry["groups"]["alpha"]["roles"].pop("local")
                    sync.save_registry(self.state, registry)
                (self.target / "LOCAL.txt").write_text("restore this")
                with self.assertRaisesRegex(SystemExit, "existing copy was preserved"):
                    self.run_cli("repair-agent-install", "alpha", "--agent", "codex")
                code, repaired = self.repair()
                self.assertEqual(code, 0)
                snapshots = self.snapshot_names()
                self.assertEqual(self.repair()[1]["status"], "already-current")
                self.assertEqual(self.snapshot_names(), snapshots)
                argv = ("rollback", "alpha", "--snapshot", repaired["snapshot"], "--roles", "local")
                self.assertEqual(self.run_cli(*argv)[0], 0)
                self.assertEqual((self.target / "LOCAL.txt").read_text(), "restore this")
                snapshots = self.snapshot_names()
                self.assertEqual(self.run_cli(*argv)[1]["status"], "already-current")
                self.assertEqual(self.snapshot_names(), snapshots)

    def test_rollback_rejects_corrupt_snapshot_before_mutation(self):
        (self.target / "LOCAL.txt").write_text("original")
        _, repaired = self.repair()
        directory = self.state / "snapshots/alpha" / repaired["snapshot"]
        (directory / "local-codex/LOCAL.txt").write_text("corrupt")
        before = (self.state / "registry.json").read_bytes()
        snapshots = self.snapshot_names()
        with self.assertRaisesRegex(SystemExit, "digest verification"):
            self.run_cli("rollback", "alpha", "--snapshot", repaired["snapshot"])
        self.assertFalse((self.target / "LOCAL.txt").exists())
        self.assertEqual(self.snapshot_names(), snapshots)
        self.assertEqual((self.state / "registry.json").read_bytes(), before)

    def test_report_missing_source_with_existing_builds(self):
        self.assertEqual(self.run_cli("relationships")[0], 0)
        shutil.rmtree(self.project / "skills/alpha")
        self.assertEqual(self.run_cli("relationships")[0], 0)
        report = self.report()
        self.assertEqual(report["summary"]["build_complete_count"], 1)
        self.assertIn("missing-copy", report["skills"][0]["statuses"])

    def test_healthy_project_only_passes_strict(self):
        shutil.rmtree(self.target)
        self.registry["groups"]["alpha"]["roles"].pop("local")
        self.save()
        self.assertEqual(self.run_cli("relationships", "--strict")[0], 0)
        self.manifest_path.unlink()
        self.assertEqual(self.run_cli("relationships", "--strict")[0], 2)

    def test_output_path_identity_and_containment_matrix(self):
        related = self.root / "related/skills"
        shutil.copytree(self.project / "skills/alpha", related / "alpha")
        self.registry["projects"] = {"related": {"skill_roots": [str(related)]}}
        self.save()
        alias = self.root / "alias"
        alias.symlink_to(self.local, target_is_directory=True)
        before = rel.digest_tree(self.target)
        registry_before = (self.state / "registry.json").read_bytes()
        for output in (self.target, self.target / "reports", self.local, self.root / "home",
                       alias / "alpha/reports", related / "alpha/reports", related.parent,
                       self.project, self.project / "reports", self.state, self.state / "snapshots"):
            with self.subTest(output=output), self.assertRaisesRegex(SystemExit, "protected path"):
                self.run_cli("relationships", "--output-dir", str(output))
            self.assertEqual(rel.digest_tree(self.target), before)
            self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)
        file = self.root / "file"
        file.write_text("keep")
        with self.assertRaisesRegex(SystemExit, "regular directory"):
            self.run_cli("relationships", "--output-dir", str(file))
        self.assertEqual(file.read_text(), "keep")
        peer = self.root / "allowed"
        peer.mkdir()
        (peer / "keep").write_text("keep")
        self.assertEqual(self.run_cli("relationships", "--output-dir", str(peer))[0], 0)
        self.assertEqual(self.run_cli("relationships", "--output-dir", str(peer))[0], 0)
        self.assertEqual((peer / "keep").read_text(), "keep")

    def test_case_alias_output_protection(self):
        upper = self.local.with_name("SKILLS")
        if upper.exists():
            self.assertTrue(os.path.samefile(upper, self.local))
            with self.assertRaisesRegex(SystemExit, "protected path"):
                self.run_cli("relationships", "--output-dir", str(upper / "alpha/reports"))
        else:
            upper.mkdir()
            original = os.path.samefile
            def samefile(a, b):
                if {str(a), str(b)} == {str(upper), str(self.local)}:
                    return True
                return original(a, b)
            with patch.object(os.path, "samefile", side_effect=samefile):
                with self.assertRaises(rel.RelationshipError):
                    rel.validate_output_directory(upper / "alpha/reports", self.state, self.project, [self.local])

    def test_stale_exit_code_and_retry_are_documented_and_executable(self):
        with patch.object(sync, "generate_and_write", side_effect=rel.RelationshipError("injected")):
            code, result = self.run_cli("rename", "alpha", "--to", "alpha", "--name", "renamed")
        self.assertEqual(code, 2)
        self.assertEqual(result["report_status"], "stale")
        self.assertEqual(sync.load_registry(self.state)["groups"]["alpha"]["name"], "renamed")
        retry = subprocess.run(shlex.split(result["report_retry_command"]), capture_output=True, text=True)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        for name in ("SKILL.md", "README.md", "README.zh-CN.md"):
            text = (ROOT / "skills/sync-skills" / name).read_text()
            for token in ("2", "report_retry_command", "project-only", "--strict"):
                self.assertIn(token, text)

    def test_optional_git_missing_and_malformed_registry(self):
        with patch.dict(os.environ, {"PATH": str(self.root / "no-tools")}):
            self.assertEqual(self.run_cli("relationships")[0], 0)
        path = self.state / "registry.json"
        path.write_text("{malformed")
        before_reports = (self.state / "reports/skill-relationships.json").read_bytes()
        with self.assertRaises((ValueError, SystemExit)):
            self.run_cli("relationships")
        self.assertEqual(path.read_text(), "{malformed")
        self.assertEqual((self.state / "reports/skill-relationships.json").read_bytes(), before_reports)

    def test_installed_skill_can_generate_report(self):
        # Real adapters and real portable Skill, then execute outside the checkout
        # using only the standard library (-S) and no optional executables.
        for agent, relative in (("codex", "skills/sync-skills"), ("workbuddy", "sync-skills")):
            output = self.root / f"distribution-{agent}"
            built = subprocess.run([sys.executable, str(ROOT / "scripts/agent_build.py"), agent,
                                    "--skill", "sync-skills", "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            installed = self.root / f"installed-{agent}"
            shutil.copytree(output / relative, installed)
            shutil.rmtree(output)
            env = dict(os.environ, PATH=str(self.root / "no-tools"))
            command = [sys.executable, "-S", str(installed / "scripts/skill_sync.py"),
                       "--project-root", str(self.project), "--state-dir", str(self.state), "relationships"]
            result = subprocess.run(command, cwd=self.root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["report_status"], "fresh")

    def test_report_double_failure_preserves_backups(self):
        self.run_cli("relationships")
        output = self.state / "reports"
        before = (output / "skill-relationships.json").read_bytes()
        original = os.replace
        def replace(source, target):
            if Path(source).name in {"staged-1", "backup-0"}:
                raise OSError("report fault")
            return original(source, target)
        with patch.object(os, "replace", side_effect=replace):
            with self.assertRaisesRegex(SystemExit, "report backups preserved"):
                self.run_cli("relationships")
        backups = list(output.glob(".relationship-report-*/backup-0"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        self.assertEqual(self.run_cli("relationships")[0], 0)
        self.assertEqual(backups[0].read_bytes(), before)

    def test_direct_install_and_snapshot_path_boundaries(self):
        source = self.project / "dist/codex/skills/alpha"
        before = rel.digest_tree(source)
        for target in (source, source / "nested", source.parent):
            with self.subTest(target=target), self.assertRaises(SystemExit):
                sync.atomic_install_build(source, target, "alpha", before)
            self.assertEqual(rel.digest_tree(source), before)
        alias = self.root / "source-alias"
        alias.symlink_to(source, target_is_directory=True)
        with self.assertRaises(SystemExit):
            sync.atomic_install_build(source, alias, "alpha", before)
        file = self.local / "file"
        file.write_text("keep")
        with self.assertRaises(SystemExit):
            sync.atomic_install_build(source, file, "alpha", before)
        self.assertEqual(file.read_text(), "keep")
        for state in (self.target, self.target / "state", self.target.parent):
            with self.subTest(state=state), self.assertRaisesRegex(SystemExit, "must not overlap"):
                sync.create_agent_install_snapshot(state, "alpha", "codex", self.target, {})
        empty = self.local / "empty"
        empty.mkdir()
        sync.atomic_install_build(source, empty, "alpha", before)
        self.assertEqual(rel.digest_tree(empty), before)
        absent = self.local / "absent"
        sync.atomic_install_build(source, absent, "alpha", before)
        self.assertEqual(rel.digest_tree(absent), before)

    def test_required_git_guard_fails_closed(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/pr_review_guard.py")],
                                env=dict(os.environ, PATH=str(self.root / "no-tools")),
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git", result.stderr)
        self.assertNotIn("PASS:", result.stdout)

    def test_recursive_exclusions_in_generated_artifact(self):
        skill = self.project / "skills/alpha"
        for prefix in (Path("."), Path("nested/deep")):
            for name in ("node_modules", "dist", "__pycache__", ".git"):
                directory = skill / prefix / name
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "private.txt").write_text("transient")
            (skill / prefix / ".DS_Store").write_text("transient")
            (skill / prefix / "module.pyc").write_text("transient")
        builder.build("codex", [], None, True)
        output = self.project / "dist/codex/skills/alpha"
        self.assertFalse(list(output.rglob("private.txt")))
        self.assertFalse(list(output.rglob("*.pyc")))
        self.assertFalse(list(output.rglob(".DS_Store")))
        self.assertEqual(self.report()["summary"]["build_complete_count"], 2)

    def test_codex_official_root_and_legacy_root_share_attribution(self):
        adapters, _ = rel.load_adapters(ROOT, [], {"HOME": str(self.root / "home")})
        codex = next(a for a in adapters if a["id"] == "codex")
        paths = {r.get("path") for r in codex["local_skill_roots"]}
        self.assertIn(str(self.root / "home/.agents/skills"), paths)
        self.assertIn(str(self.root / "home/.codex/skills"), paths)
        roots = rel.deduplicate_roots(adapters)
        shared = next(r for r in roots if r.get("path") == str(self.root / "home/.agents/skills"))
        self.assertEqual(shared["agent_ids"], ["codex", "workbuddy"])


    def test_cross_group_nested_install_preserved(self):
        nested = self.target / "nested/gamma"
        shutil.copytree(self.project / "dist/codex/skills/gamma", nested)
        before = rel.digest_tree(self.target)
        registry_before = (self.state / "registry.json").read_bytes()
        with self.assertRaisesRegex(SystemExit, "must not be nested"):
            self.run_cli("link-location", "gamma", "--location-id", "local:codex", "--kind", "local",
                         "--agent-id", "codex", "--path", str(nested))
        self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)
        self.assertEqual(rel.digest_tree(self.target), before)
        self.assertFalse(self.snapshot_names())

        # Existing unsafe registries must be rejected independently of link-location.
        self.registry["groups"]["gamma"]["roles"]["local"] = str(nested)
        self.save()
        registry_before = (self.state / "registry.json").read_bytes()
        with self.assertRaisesRegex(SystemExit, "must not be nested"):
            self.repair()
        self.assertEqual(rel.digest_tree(self.target), before)
        self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)
        self.assertFalse(self.snapshot_names())
        for candidate in (nested, self.target.parent):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(SystemExit, "must not be nested"):
                sync.validate_location_identity(self.registry, "gamma", candidate)

        # After correcting the registry, the authorized repair remains idempotent.
        self.registry["groups"]["gamma"]["roles"].pop("local")
        self.save()
        code, repaired = self.repair()
        self.assertEqual(code, 0)
        self.assertEqual(self.repair()[1]["status"], "already-current")
        # The rollback entry must also protect an unselected group added later.
        shutil.copytree(self.project / "dist/codex/skills/gamma", nested)
        self.registry = sync.load_registry(self.state)
        self.registry["groups"]["gamma"]["roles"]["local"] = str(nested)
        self.save()
        before = rel.digest_tree(self.target)
        snapshots = self.snapshot_names()
        registry_before = (self.state / "registry.json").read_bytes()
        with self.assertRaisesRegex(SystemExit, "must not be nested"):
            self.run_cli("rollback", "alpha", "--snapshot", repaired["snapshot"])
        self.assertEqual(rel.digest_tree(self.target), before)
        self.assertEqual(self.snapshot_names(), snapshots)
        self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)

    def test_changed_install_identity_rejected(self):
        skill = self.target / "SKILL.md"
        original = skill.read_text()
        skill.write_text(original.replace('sync_id: "alpha"', 'sync_id: "gamma"'))
        before = rel.digest_tree(self.target)
        registry_before = (self.state / "registry.json").read_bytes()
        self.assertTrue(any(i["code"] == "identity-conflict" for i in self.report()["issues"]))
        with self.assertRaisesRegex(SystemExit, "metadata.sync_id conflicts"):
            self.repair()
        self.assertEqual(rel.digest_tree(self.target), before)
        self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)
        self.assertFalse(self.snapshot_names())
        # Missing identity is still repairable after an explicit registration.
        skill.write_text(original.replace('  sync_id: "alpha"\n', ""))
        self.assertEqual(self.repair()[0], 0)
        snapshots = self.snapshot_names()
        self.assertEqual(self.repair()[1]["status"], "already-current")
        self.assertEqual(self.snapshot_names(), snapshots)

    def test_external_identity_change_not_associated(self):
        for kind, owner_flag in (("external", "--source-id"), ("project", "--project-id")):
            with self.subTest(kind=kind):
                ext = self.root / kind / "skills/alpha"
                shutil.copytree(self.project / "skills/alpha", ext)
                self.assertEqual(self.run_cli("link-location", "alpha", "--location-id", f"{kind}:bundle",
                                             "--kind", kind, owner_flag, "bundle", "--path", str(ext))[0], 0)
                skill = ext / "SKILL.md"
                original = skill.read_text()
                skill.write_text(original.replace('sync_id: "alpha"', 'sync_id: "gamma"'))
                for _ in range(2):
                    report = self.report()
                    self.assertTrue(any(i["code"] == "identity-conflict" and i.get("path") == str(ext)
                                        for i in report["issues"]))
                    self.assertFalse(any(loc["path"] == str(ext) for s in report["skills"] for loc in s["locations"]))
                skill.write_text(original)
                self.assertTrue(any(loc["path"] == str(ext) for s in self.report()["skills"] for loc in s["locations"]))
                skill.write_text(original.replace('  sync_id: "alpha"\n', ""))
                report = self.report()
                self.assertFalse(any(loc["path"] == str(ext) for s in report["skills"] for loc in s["locations"]))
                self.assertTrue(any(i["code"] == "missing-sync-id" and i.get("path") == str(ext) for i in report["issues"]))
                skill.write_text(original)

    def test_repeated_existing_local_root(self):
        self.assertEqual(self.run_cli("relationships")[0], 0)
        alias = self.root / "alias-root"
        alias.symlink_to(self.local, target_is_directory=True)
        argv = ("relationships", "--local-root", f"codex={self.local}",
                "--local-root", f"codex={self.local}", "--local-root", f"codex={alias}")
        for _ in range(2):
            self.assertEqual(self.run_cli(*argv)[0], 0)
            report = json.loads((self.state / "reports/skill-relationships.json").read_text())
            self.assertEqual(len(report["agent_builders"][0]["local_skill_roots"]), 1)
            self.assertEqual(report["summary"]["local_skill_count"], 1)
        upper = self.local.with_name("SKILLS")
        real_samefile = os.path.samefile
        simulated = not upper.exists()
        if simulated:
            upper.mkdir()
        def samefile(a, b):
            if simulated and {str(a), str(b)} == {str(upper), str(self.local)}:
                return True
            return real_samefile(a, b)
        with patch.object(os.path, "samefile", side_effect=samefile):
            self.assertEqual(self.run_cli("relationships", "--local-root", f"codex={upper}")[0], 0)
            report = json.loads((self.state / "reports/skill-relationships.json").read_text())
            self.assertEqual(len(report["agent_builders"][0]["local_skill_roots"]), 1)

    def test_multiple_related_roots_same_project(self):
        roots = [self.root / "app/skills", self.root / "app/extra-skills"]
        for root in roots:
            shutil.copytree(self.project / "skills/alpha", root / "alpha")
        # Exercise persisted roots/locations as well as explicit root inputs.
        self.registry["projects"] = {"app": {"skill_roots": [str(r) for r in roots]}}
        self.registry["groups"]["alpha"]["locations"] = {
            f"project:app-{index}": {"kind": "project", "project_id": "app", "path": str(root / "alpha")}
            for index, root in enumerate(roots)}
        self.save()
        argv = ("relationships", "--project", f"app={roots[0]}", "--project", f"app={roots[1]}")
        for _ in range(2):
            self.assertEqual(self.run_cli(*argv)[0], 0)
            report = self.report()
            alpha = next(s for s in report["skills"] if s["sync_id"] == "alpha")
            self.assertIn("identity-conflict", alpha["statuses"])
            self.assertEqual(alpha["locations"], [])
            self.assertEqual(sum(i["code"] == "identity-conflict" for i in report["issues"]), 2)
            gamma = next(s for s in report["skills"] if s["sync_id"] == "gamma")
            self.assertNotIn("identity-conflict", gamma["statuses"])
        self.assertEqual(self.run_cli(*argv, "--strict")[0], 2)
        shutil.rmtree(roots[1] / "alpha")
        self.registry["groups"]["alpha"]["locations"].pop("project:app-1")
        self.save()
        self.assertEqual(self.run_cli(*argv, "--strict")[0], 0)
        alpha = next(s for s in self.report()["skills"] if s["sync_id"] == "alpha")
        self.assertEqual(len(alpha["locations"]), 1)

    def test_nested_agent_builds_fresh(self):
        skill = self.project / "skills/alpha"
        nested = skill / "references/example/agent-builds"
        nested.mkdir(parents=True)
        (nested / "example.json").write_text("{}")
        override = skill / "agent-builds/codex"
        override.mkdir()
        (override / "adapter.txt").write_text("overlay")
        for _ in range(2):
            builder.build("codex", [], None, True)
            output = self.project / "dist/codex/skills/alpha"
            self.assertEqual((output / "references/example/agent-builds/example.json").read_text(), "{}")
            self.assertFalse((output / "agent-builds").exists())
            self.assertEqual((output / "adapter.txt").read_text(), "overlay")
            alpha = next(s for s in self.report()["skills"] if s["sync_id"] == "alpha")
            self.assertNotIn("agent-build-stale", alpha["statuses"])
        (nested / "example.json").write_text('{"changed": true}')
        self.assertIn("agent-build-stale", self.report()["skills"][0]["statuses"])
        builder.build("codex", [], None, True)
        self.assertNotIn("agent-build-stale", self.report()["skills"][0]["statuses"])

    def test_state_lock_does_not_mutate_local_skill(self):
        before = rel.digest_tree(self.target)
        project_before = rel.digest_tree(self.project / "skills")
        registry_before = (self.state / "registry.json").read_bytes()
        output = self.root / "reports-output"
        for state in (self.target, self.target / "runtime-state", self.project / "runtime-state"):
            with self.subTest(state=state), self.assertRaisesRegex(rel.RelationshipError, "lock conflicts"):
                rel.generate_and_write(project_root=self.project, state_dir=state,
                                       registry=self.registry, output_dir=output)
            self.assertFalse(output.exists())
            self.assertFalse((state / ".relationships.lock").exists())
            self.assertEqual(rel.digest_tree(self.target), before)
            self.assertEqual(rel.digest_tree(self.project / "skills"), project_before)
            self.assertEqual((self.state / "registry.json").read_bytes(), registry_before)
        alias = self.root / "state-alias"
        alias.symlink_to(self.state, target_is_directory=True)
        file = self.root / "state-file"
        file.write_text("keep")
        for state in (alias, alias / "nested", file, file / "nested"):
            with self.subTest(state=state), self.assertRaises(rel.RelationshipError):
                rel.generate_and_write(project_root=self.project, state_dir=state,
                                       registry=self.registry, output_dir=output)
            self.assertFalse(output.exists())
        for _ in range(2):
            rel.generate_and_write(project_root=self.project, state_dir=self.state,
                                   registry=self.registry, output_dir=output)
        self.assertEqual(file.read_text(), "keep")
        self.assertEqual(rel.digest_tree(self.target), before)

    def test_missing_build_not_synced_install(self):
        manifest = self.manifest_path.read_text()
        cases = ("missing", "invalid")
        for case in cases:
            with self.subTest(case=case):
                if not self.manifest_path.exists():
                    builder.build("codex", [], None, False)
                self.manifest_path.write_text(manifest)
                if case == "missing":
                    shutil.rmtree(self.project / "dist/codex")
                else:
                    self.manifest_path.write_text("{invalid")
                report = self.report()
                alpha = next(s for s in report["skills"] if s["sync_id"] == "alpha")
                self.assertEqual(alpha["local_installs"][0]["statuses"], ["agent-build-missing"])
                invalid = copy.deepcopy(report)
                invalid["skills"][0]["local_installs"][0]["statuses"] = ["synced"]
                with self.assertRaisesRegex(rel.RelationshipError, "without a trusted build"):
                    rel.validate_contract(invalid)
                if case == "invalid":
                    self.manifest_path.write_text(manifest)
                builder.build("codex", [], None, case == "invalid")
                self.assertEqual(self.report()["skills"][0]["local_installs"][0]["statuses"], ["synced"])



if __name__ == "__main__":
    unittest.main(verbosity=2)
