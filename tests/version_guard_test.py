"""Release guard integration tests using disposable, committed Git histories."""

from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/version_guard.py"
sys.path.insert(0, str(ROOT / "scripts"))
import version_guard


class VersionGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="version-guard-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Version Guard Test")
        self.git("config", "user.email", "version-guard@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)
        self.skill = self.root / "skills/demo/SKILL.md"
        self.adapter = self.root / "platforms/demo/adapter.json"
        self.write(self.skill, '---\nname: demo\nmetadata:\n  sync_id: demo\n  version: "1.2.3"\n---\n# Demo\n')
        self.write(self.adapter, json.dumps({"id": "demo", "version": "1.2.3", "artifact_version": "1.2.3"}))
        self.write(self.skill.with_name("CHANGELOG.md"), '# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n\n- Old release.\n')
        self.write(self.adapter.with_name("CHANGELOG.md"), '# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n\n- Old adapter.\n\n## [artifact 1.2.3] - 2026-01-01\n\n- Old artifact.\n')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "[codex] Version guard fixture")
        return self.git("rev-parse", "HEAD")

    def reset(self):
        # Only ever called in this test's disposable fixture repository.
        self.git("reset", "--hard", self.base)
        self.git("clean", "-fd")

    def set_version(self, kind, value):
        if kind == "skill":
            content = self.skill.read_text()
            content = re.sub(r'^  version: .*$', f'  version: "{value}"', content, flags=re.M)
            self.skill.write_text(content)
        else:
            content = json.loads(self.adapter.read_text())
            content["version" if kind == "adapter" else "artifact_version"] = value
            self.adapter.write_text(json.dumps(content))

    def add_release(self, kind, value, change_type, extra="", date="2026-01-02"):
        path = (self.skill if kind == "skill" else self.adapter).with_name("CHANGELOG.md")
        prefix = "artifact " if kind == "artifact" else ""
        entry = (f'## [{prefix}{value}] - {date}\n\n- Change-Type: {change_type}\n'
                 '- Summary: A concrete release summary.\n'
                 '- Compatibility: Existing usage remains valid unless described below.\n' + extra + '\n')
        path.write_text(path.read_text().replace('## [Unreleased]\n\n', '## [Unreleased]\n\n' + entry, 1))

    def snapshot(self):
        files = {}
        for p in self.root.rglob("*"):
            if ".git" in p.relative_to(self.root).parts:
                continue
            if p.is_symlink():
                files[str(p.relative_to(self.root))] = ("link", os.readlink(p))
            elif p.is_file():
                files[str(p.relative_to(self.root))] = (p.stat().st_mode, p.read_bytes())
        return self.git("status", "--porcelain"), self.git("write-tree"), self.git("show-ref"), files

    def run_guard(self, expected=None, base=None, env=None, head=None):
        before = self.snapshot()
        command = [sys.executable, str(GUARD), "--base", base or self.base]
        if head:
            command.extend(["--head", head])
        result = subprocess.run(command, cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(before, self.snapshot(), "guard must preserve checkout, index and refs")
        output = result.stdout + result.stderr
        if expected is None:
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("PASS: version format", output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(expected, output)
            self.assertIn("::error::", output)
        return output

    def test_all_owners_reject_invalid_formats(self):
        for kind in ("skill", "adapter", "artifact"):
            for value in ("01.2.3", "1.02.3", "1.2.03", "1.2", "1.2.3.4", "v1.2.3",
                          "1.2.3-alpha", "1.2.3+build", "-1.2.3", "١.2.3"):
                with self.subTest(kind=kind, version=value):
                    self.reset()
                    self.set_version(kind, value)
                    self.commit()
                    self.run_guard("canonical MAJOR.MINOR.PATCH")

    def test_all_owners_accept_each_release_level(self):
        for kind in ("skill", "adapter", "artifact"):
            for value, change_type, extra in (
                ("1.2.4", "fix", ""), ("1.3.0", "feature", ""),
                ("2.0.0", "breaking", "- Breaking-Change: Old command removed; use new command.\n- Migration: Replace old calls with new calls.\n"),
            ):
                with self.subTest(kind=kind, change=change_type):
                    self.reset()
                    self.set_version(kind, value)
                    self.add_release(kind, value, change_type, extra)
                    self.commit()
                    self.run_guard()
                    self.run_guard()  # repeated checks are idempotent

    def test_all_owners_reject_wrong_increments(self):
        for kind in ("skill", "adapter", "artifact"):
            for value, change_type in (("1.2.2", "fix"), ("1.2.5", "fix"), ("2.0.0", "fix"),
                                       ("1.3.1", "feature"), ("2.1.0", "breaking"),
                                       ("3.0.0", "breaking"), ("2.0.0", "stable")):
                with self.subTest(kind=kind, version=value, change=change_type):
                    self.reset()
                    self.set_version(kind, value)
                    self.add_release(kind, value, change_type)
                    self.commit()
                    self.run_guard("does not match Change-Type")

    def test_all_owners_require_new_changelog_and_breaking_evidence(self):
        for kind in ("skill", "adapter", "artifact"):
            with self.subTest(kind=kind):
                self.reset()
                self.set_version(kind, "2.0.0")
                self.commit()
                self.run_guard("require one new release entry")
                self.add_release(kind, "2.0.0", "breaking")
                self.commit()
                self.run_guard("Breaking-Change")
                log = (self.skill if kind == "skill" else self.adapter).with_name("CHANGELOG.md")
                log.write_text(log.read_text().replace("- Summary:", "- Breaking-Change: Old input removed.\n- Summary:"))
                self.commit()
                self.run_guard("Migration")
                log.write_text(log.read_text().replace("- Summary:", "- Migration: Switch to the documented new input.\n- Summary:"))
                self.commit()
                self.run_guard()

    def test_no_bump_and_unreleased_changes_need_no_declarations(self):
        self.write(self.root / "README.md", "Documentation only.\n")
        log = self.skill.with_name("CHANGELOG.md")
        log.write_text(log.read_text().replace("## [Unreleased]", "## [Unreleased]\n\n- Pending feature."))
        self.commit()
        self.run_guard()

    def test_three_versions_upgrade_independently(self):
        self.set_version("adapter", "1.2.4")
        self.add_release("adapter", "1.2.4", "fix")
        self.set_version("artifact", "1.3.0")
        self.add_release("artifact", "1.3.0", "feature")
        self.commit()
        self.assertIn("2 release declaration(s)", self.run_guard())

    def test_artifact_cannot_borrow_adapter_entry(self):
        self.set_version("artifact", "1.2.4")
        self.add_release("adapter", "1.2.4", "fix")
        self.commit()
        self.run_guard("[artifact 1.2.4]")

    def test_changelog_fields_and_dates(self):
        for bad_date in ("2026-02-30", "2999-01-01", "2026-1-2"):
            with self.subTest(date=bad_date):
                self.reset()
                self.set_version("skill", "1.2.4")
                self.add_release("skill", "1.2.4", "fix", date=bad_date)
                self.commit()
                self.run_guard("FAIL:")
        for field in ("Change-Type", "Summary", "Compatibility"):
            for value in ("", "TBD"):
                with self.subTest(field=field, value=value):
                    self.reset()
                    self.set_version("skill", "1.2.4")
                    self.add_release("skill", "1.2.4", "fix")
                    log = self.skill.with_name("CHANGELOG.md")
                    log.write_text(re.sub(r"^- " + field + r":.*$", f"- {field}: {value}", log.read_text(), flags=re.M))
                    self.commit()
                    self.run_guard(field)

    def test_reused_or_duplicate_release_entry_is_rejected(self):
        self.add_release("skill", "1.2.4", "fix")
        baseline = self.commit()
        self.set_version("skill", "1.2.4")
        self.commit()
        self.run_guard("cannot reuse existing release", base=baseline)
        self.add_release("skill", "1.2.4", "fix")
        self.commit()
        self.run_guard("require one new release entry")

    def test_early_versions_and_first_stable(self):
        for kind in ("skill", "adapter", "artifact"):
            for value, change_type, extra in (
                ("0.2.4", "fix", ""), ("0.3.0", "feature", ""),
                ("1.0.0", "breaking", "- Breaking-Change: Input renamed.\n- Migration: Rename input.\n"),
                ("1.0.0", "stable", "- Stable-Contract: Documented inputs and outputs.\n- Readiness: Supported workflows tested.\n"),
            ):
                with self.subTest(kind=kind, change=change_type):
                    self.reset()
                    self.set_version(kind, "0.2.3")
                    baseline = self.commit()
                    self.set_version(kind, value)
                    self.add_release(kind, value, change_type, extra)
                    self.commit()
                    self.run_guard(base=baseline)
                    if change_type == "stable":
                        log = (self.skill if kind == "skill" else self.adapter).with_name("CHANGELOG.md")
                        log.write_text(log.read_text().replace("- Readiness: Supported workflows tested.\n", ""))
                        self.commit()
                        self.run_guard("Readiness", base=baseline)

    def test_initial_components(self):
        # Removing the fixture owners gives all three independent fields an initial release.
        shutil.rmtree(self.root / "skills")
        shutil.rmtree(self.root / "platforms")
        self.git("commit", "-qam", "[codex] Empty component baseline")
        baseline = self.git("rev-parse", "HEAD")
        for value in ("0.1.0", "1.0.0", "0.0.1"):
            with self.subTest(version=value):
                self.git("reset", "--hard", baseline)
                self.git("checkout", self.base, "--", "skills", "platforms")
                for kind in ("skill", "adapter", "artifact"):
                    self.set_version(kind, value)
                    self.add_release(kind, value, "initial", "- Stable-Contract: Supported inputs.\n- Readiness: Workflows tested.\n")
                self.commit()
                self.run_guard(None if value != "0.0.1" else "new components require", base=baseline)

    def test_numeric_parts_do_not_carry_at_nine(self):
        for kind in ("skill", "adapter", "artifact"):
            for old, new, change in (("1.2.9", "1.2.10", "fix"), ("1.9.7", "1.10.0", "feature")):
                with self.subTest(kind=kind, version=old):
                    self.reset()
                    self.set_version(kind, old)
                    baseline = self.commit()
                    self.set_version(kind, new)
                    self.add_release(kind, new, change)
                    self.commit()
                    self.run_guard(base=baseline)
        self.assertEqual(version_guard.increment("9" * 5000), "1" + "0" * 5000)
        self.assertEqual(version_guard.version_parts("9" * 5000 + ".0.0", "test")[1:], ("0", "0"))

    def test_skill_rename_preserves_version_history(self):
        self.set_version("skill", "1.2.5")
        self.add_release("skill", "1.2.5", "fix")
        self.skill.parent.rename(self.skill.parent.with_name("renamed"))
        self.commit()
        self.run_guard("does not match Change-Type")
        moved = self.root / "skills/renamed/SKILL.md"
        moved.write_text(moved.read_text().replace("1.2.5", "1.2.4"))
        log = moved.with_name("CHANGELOG.md")
        log.write_text(log.read_text().replace("1.2.5", "1.2.4"))
        self.commit()
        self.run_guard()

    def test_skill_identity_cannot_change_or_duplicate(self):
        self.skill.write_text(self.skill.read_text().replace("sync_id: demo", "sync_id: other"))
        self.commit()
        self.run_guard("sync_id is immutable")
        self.reset()
        shutil.copytree(self.skill.parent, self.skill.parent.with_name("duplicate"))
        self.commit()
        self.run_guard("duplicate skill identity")

    def test_scoped_metadata_and_malformed_inputs(self):
        self.skill.write_text(self.skill.read_text().replace('  version: "1.2.3"', '  version: "01.2.3"\n  urls:\n    version: "1.2.3"'))
        self.commit()
        self.run_guard("canonical MAJOR.MINOR.PATCH")
        for replacement in ('  version: "1.2.3"\n  version: "1.2.4"', '  version: [1, 2, 3]'):
            self.reset()
            self.skill.write_text(self.skill.read_text().replace('  version: "1.2.3"', replacement))
            self.commit()
            self.run_guard("metadata.version")
        self.reset()
        self.adapter.write_text('{"id":"demo","version":"1.2.3","version":"1.2.4","artifact_version":"1.2.3"}')
        self.commit()
        self.run_guard("duplicate JSON key")

    def test_symlinked_metadata_or_changelog_is_rejected(self):
        for kind, filename in (("skill", "SKILL.md"), ("adapter", "adapter.json"), ("skill", "CHANGELOG.md")):
            with self.subTest(kind=kind, file=filename):
                self.reset()
                self.set_version("skill", "1.2.4")
                self.add_release("skill", "1.2.4", "fix")
                path = (self.skill if kind == "skill" else self.adapter).with_name(filename)
                original = path.with_name("actual-" + filename)
                path.rename(original)
                path.symlink_to(original.name)
                self.commit()
                self.run_guard("tracked regular file")

    def test_component_directory_alias_cannot_hide_versions(self):
        for owner in ("skills", "platforms"):
            with self.subTest(owner=owner):
                self.reset()
                original = self.root / owner / "demo"
                target = self.root / f"external-{owner}"
                original.rename(target)
                original.symlink_to(target, target_is_directory=True)
                self.commit()
                self.run_guard("component directories cannot be symlinks")

    def test_advanced_base_and_merge_conflict(self):
        self.set_version("skill", "1.2.4")
        self.add_release("skill", "1.2.4", "fix")
        advanced = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write(self.root / "README.md", "Unrelated branch change.\n")
        self.commit()
        self.assertIn("0 release declaration(s)", self.run_guard(base=advanced))
        self.set_version("skill", "1.3.0")
        self.add_release("skill", "1.3.0", "feature")
        self.commit()
        self.run_guard("cannot be merged cleanly", base=advanced)

    def test_direct_invocation_reads_commits_preserves_dirty_files_and_fails_closed(self):
        self.set_version("skill", "broken-uncommitted-version")
        self.write(self.root / "untracked.txt", "Keep this draft.\n")
        self.run_guard()
        self.run_guard("FAIL:", base="missing-ref")
        self.run_guard("FAIL:", head="missing-head")
        self.run_guard("FAIL:", env={**os.environ, "PATH": str(self.root / "no-executables")})

    def test_ci_runs_validation_before_catalog_mutation(self):
        workflow = (ROOT / ".github/workflows/skill-catalog.yml").read_text()
        gate = (ROOT / "tests/pr-review-gate.sh").read_text()
        self.assertIn('run: python3 scripts/version_guard.py --base "$BASE_SHA"', workflow)
        self.assertLess(workflow.index("scripts/version_guard.py"), workflow.index("scripts/skill_catalog.py --write"))
        self.assertIn('python3 scripts/version_guard.py --base "$BASE_REF"', gate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
