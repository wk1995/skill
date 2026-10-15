"""Regression coverage for PR 24's policy publication and identity boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = Path(os.environ.get("POLICY_REGRESSION_CLI", ROOT / "skills/sync-skills/scripts/skill_sync.py"))
sys.path.insert(0, str(CLI.parent))
import skill_sync as sync
import skill_relationships as relationships


class PolicyBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review-policy-boundaries-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        shutil.copytree(ROOT / "platforms", self.project / "platforms")
        self.home = self.root / "home"
        self.legacy = self.home / ".codex/skills/pr-review-loop/pr-review-loop.yml"
        self.legacy.parent.mkdir(parents=True)
        self.payload = b"comment: false\nmax_rounds: 2\n"
        self.legacy.write_bytes(self.payload)
        self.legacy.chmod(0o640)
        self.shared = self.root / "xdg/skill/pr-review-loop.yml"
        self.shared.parent.mkdir(parents=True)
        self.environment = dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.root / "xdg"))
        self.adapters = [{"local_skill_roots": [{"path": str(self.legacy.parent.parent), "status": "resolved"}]}]

    def upgrade_cli(self):
        result = subprocess.run(
            [sys.executable, str(CLI), "--project-root", str(self.project),
             "--state-dir", str(self.root / "state"), "upgrade-machine-policy"],
            env=self.environment, cwd=self.root, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_public_upgrade_does_not_follow_or_replace_preexisting_staging(self):
        temporary = self.shared.with_name(".pr-review-loop.yml.upgrade")
        victim = self.root / "unrelated.yml"
        for kind in ("regular", "symlink"):
            with self.subTest(kind=kind):
                victim.write_bytes(b"unrelated content\n")
                if kind == "symlink":
                    temporary.symlink_to(victim)
                else:
                    temporary.write_bytes(b"unowned temporary content\n")
                try:
                    self.assertEqual(self.upgrade_cli()["status"], "upgraded")
                    self.assertEqual(victim.read_bytes(), b"unrelated content\n")
                    self.assertEqual(temporary.is_symlink(), kind == "symlink")
                    self.assertEqual(temporary.read_bytes(), victim.read_bytes() if kind == "symlink" else b"unowned temporary content\n")
                    self.assertFalse(self.shared.is_symlink())
                    self.assertEqual(self.shared.read_bytes(), self.payload)
                    self.assertEqual(stat.S_IMODE(self.shared.stat().st_mode), 0o640)
                    self.assertEqual(self.legacy.read_bytes(), self.payload)
                    self.assertEqual(self.upgrade_cli()["status"], "shared-present")
                finally:
                    temporary.unlink(missing_ok=True)
                    self.shared.unlink(missing_ok=True)

    def test_publish_preserves_a_shared_policy_created_after_preflight(self):
        original_link, original_replace = os.link, os.replace
        def racing_publisher(operation):
            def publish(source, destination, *args, **kwargs):
                if Path(destination) == self.shared:
                    Path(destination).write_bytes(b"comment: true\n")
                return operation(source, destination, *args, **kwargs)
            return publish
        with patch.dict(os.environ, self.environment), \
                patch.object(sync.os, "link", side_effect=racing_publisher(original_link)), \
                patch.object(sync.os, "replace", side_effect=racing_publisher(original_replace)):
            result = sync.upgrade_shared_machine_policy(self.adapters)
        self.assertEqual(result["status"], "shared-present")
        self.assertEqual(self.shared.read_bytes(), b"comment: true\n")
        self.assertEqual(self.legacy.read_bytes(), self.payload)
        self.assertEqual(sorted(p.name for p in self.shared.parent.iterdir()), [self.shared.name])

    def test_staging_failure_leaves_sources_and_destination_unchanged(self):
        with patch.dict(os.environ, self.environment), patch.object(sync.shutil, "copy2", side_effect=OSError("staging fault")):
            with self.assertRaises(OSError):
                sync.upgrade_shared_machine_policy(self.adapters)
        self.assertFalse(self.shared.exists())
        self.assertEqual(self.legacy.read_bytes(), self.payload)
        self.assertEqual(list(self.shared.parent.iterdir()), [])

    def test_changed_staged_policy_is_rejected_before_publication(self):
        original_copy = shutil.copy2
        def changed_copy(source, destination):
            original_copy(source, destination)
            Path(destination).write_bytes(b"changed after validation\n")
        with patch.dict(os.environ, self.environment), patch.object(sync.shutil, "copy2", side_effect=changed_copy):
            with self.assertRaisesRegex(SystemExit, "changed during migration"):
                sync.upgrade_shared_machine_policy(self.adapters)
        self.assertFalse(self.shared.exists())
        self.assertEqual(self.legacy.read_bytes(), self.payload)
        self.assertEqual(list(self.shared.parent.iterdir()), [])

    def test_public_upgrade_needs_no_git_and_rejects_shared_symlinks(self):
        self.environment["PATH"] = str(self.root / "empty-path")
        self.assertEqual(self.upgrade_cli()["status"], "upgraded")
        self.shared.unlink()
        self.shared.symlink_to(self.legacy)
        with patch.dict(os.environ, self.environment):
            with self.assertRaisesRegex(SystemExit, "regular file"):
                sync.upgrade_shared_machine_policy(self.adapters)
        self.assertTrue(self.shared.is_symlink())
        self.assertEqual(self.legacy.read_bytes(), self.payload)

    def test_builder_and_consumers_use_stable_identity_for_every_adapter(self):
        spec = importlib.util.spec_from_file_location("policy_boundary_builder", ROOT / "scripts/agent_build.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.ROOT = self.project
        builder.SKILLS_DIR = self.project / "skills"
        builder.PLATFORMS_DIR = self.project / "platforms"
        builder.DEFAULT_OUTPUT_DIR = self.project / "dist"
        for name, identity in (("reviewer", "pr-review-loop"), ("pr-review-loop", "unrelated-skill")):
            skill = builder.SKILLS_DIR / name
            (skill / "agent-builds").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Test policy identity.\nmetadata:\n"
                f"  sync_id: {identity}\n  version: 1.0.0\n---\n\n# Test\n"
            )
            (skill / "pr-review-loop.yml").write_bytes(self.payload)
            nested = skill / "references/pr-review-loop/pr-review-loop.yml"
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b"ordinary nested content\n")
        adapters, issues = relationships.load_adapters(self.project, [], self.environment)
        self.assertEqual(issues, [])
        for adapter in adapters:
            with self.subTest(agent=adapter["id"]):
                output = builder.build(adapter["id"], [], None, False)
                skills = output / adapter["skills_path"]
                self.assertFalse((skills / "reviewer/pr-review-loop.yml").exists())
                self.assertEqual((skills / "pr-review-loop/pr-review-loop.yml").read_bytes(), self.payload)
                self.assertEqual((skills / "reviewer/references/pr-review-loop/pr-review-loop.yml").read_bytes(), b"ordinary nested content\n")
                before = (output / ".agent-build.json").read_bytes()
                (builder.SKILLS_DIR / "reviewer/pr-review-loop.yml").write_bytes(b"comment: true\n")
                builder.build(adapter["id"], [], None, True)
                self.assertEqual((output / ".agent-build.json").read_bytes(), before)
        builds, issues, _sources = relationships.read_builds(self.project, adapters)
        self.assertEqual(issues, [])
        self.assertEqual(set(builds["pr-review-loop"]), {adapter["id"] for adapter in adapters})


if __name__ == "__main__":
    unittest.main()
