"""HTML presentation, public format selection and transactional report regressions."""
import base64
import copy
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import skill_relationship_regressions as fixtures

rel, sync = fixtures.rel, fixtures.sync


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.tags, self.text = [], []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class HtmlReports(unittest.TestCase):
    # Reuse disposable public-CLI fixtures without inheriting their test methods.
    setUp = fixtures.ReviewRegressions.setUp
    save = fixtures.ReviewRegressions.save
    run_cli = fixtures.ReviewRegressions.run_cli
    report = fixtures.ReviewRegressions.report

    def write(self, report=None, output=None, format_name="all"):
        return rel.write_reports(
            self.report() if report is None else report,
            output_dir=output or self.state / "reports",
            state_dir=self.state, project_root=self.project, output_format=format_name,
        )

    def test_escaped_text_all_surfaces_and_static_script_policy(self):
        report = json.loads((fixtures.ROOT / "tests/fixtures/skill-relationships/valid.json").read_text())
        payload = '</script><img src="https://invalid.example/x" onerror="alert(1)">&\'中文'
        report["project"]["id"] = payload
        report["skills"][0]["name"] = payload
        report["skills"][0]["aliases"] = [payload]
        report["skills"][0]["portable"]["path"] = "/source/" + payload
        report["skills"][0]["local_installs"][0]["path"] = "/install/" + payload
        report["skills"][0]["agent_builds"]["codex"]["path"] = "/build/" + payload
        report["skills"][0]["locations"][0]["path"] = "/related/" + payload
        report["unlinked_local_skills"][0]["name"] = payload
        report["issues"][0]["message"] = payload
        report["scan_sources"][0]["path"] = "/scan/" + payload
        report["agent_builders"][0]["adapter_version"] = payload
        original = copy.deepcopy(report)
        rendered = rel.html_report(report)
        self.assertEqual(report, original)
        doc = Document(rendered)
        self.assertNotIn("img", [tag for tag, _ in doc.tags])
        self.assertEqual([tag for tag, _ in doc.tags].count("script"), 1)
        self.assertGreaterEqual("".join(doc.text).count(payload), 10)
        for _, attrs in doc.tags:
            self.assertFalse(any(key.startswith("on") or key == "src" for key in attrs))
            if "href" in attrs:
                self.assertTrue(attrs["href"].startswith("#"))
        script = re.search(r"<script>(.*?)</script>", rendered, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        csp = next(attrs["content"] for tag, attrs in doc.tags if attrs.get("http-equiv") == "Content-Security-Policy")
        self.assertIn("'sha256-" + digest + "'", csp)
        self.assertNotIn(payload, script)

    def test_multiple_installs_without_build_and_dynamic_builder(self):
        report = self.report()
        skill = report["skills"][0]
        second = copy.deepcopy(skill["local_installs"][0])
        second["path"] = str(self.local / "nested/second-alpha")
        skill["local_installs"].append(second)
        skill["agent_builds"]["codex"] = {"present": False}
        report["agent_builders"].append({"id": "future-agent", "adapter_version": "1.0.0", "artifact_version": "1.0.0"})
        for item in report["skills"]:
            item["agent_builds"]["future-agent"] = {"present": False}
        text = "".join(Document(rel.html_report(report)).text)
        self.assertIn(second["path"], text)
        self.assertIn(str(self.target), text)
        self.assertIn("future-agent", text)
        self.assertIn("构建缺失", text)
        report["skills"] = []
        rendered = rel.html_report(report)
        self.assertIn('<p id="empty-results">', rendered)

    def test_formats_private_permissions_and_repeat(self):
        report = self.report()
        before = (self.state / "registry.json").read_bytes()
        formats = {"html": {"html"}, "all": {"json", "markdown", "html"},
                   "both": {"json", "markdown"}, "json": {"json"}, "markdown": {"markdown"}}
        for name, expected in formats.items():
            with self.subTest(format=name):
                output = self.root / ("out-" + name)
                paths = self.write(report, output, name)
                self.assertEqual(set(paths), expected)
                self.assertEqual({p.name for p in output.iterdir()}, {Path(p).name for p in paths.values()})
                contents = {p: Path(p).read_bytes() for p in paths.values()}
                self.assertEqual(paths, self.write(report, output, name))
                self.assertEqual(contents, {p: Path(p).read_bytes() for p in paths.values()})
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
                for path in paths.values():
                    self.assertEqual(stat.S_IMODE(Path(path).stat().st_mode), 0o600)
        self.assertEqual(before, (self.state / "registry.json").read_bytes())

    def test_reject_html_targets_before_any_output_or_lock_mutation(self):
        victim = self.root / "victim"
        victim.write_text("preserve")
        for target_type in ("symlink", "directory"):
            with self.subTest(target_type=target_type):
                output = self.root / target_type
                output.mkdir()
                target = output / rel.REPORT_FILENAMES["html"]
                target.symlink_to(victim) if target_type == "symlink" else target.mkdir()
                sentinel = output / rel.REPORT_FILENAMES["json"]
                sentinel.write_text("old json")
                mode = output.stat().st_mode
                with self.assertRaises(rel.RelationshipError):
                    self.write(output=output)
                self.assertEqual(sentinel.read_text(), "old json")
                self.assertEqual(victim.read_text(), "preserve")
                self.assertEqual(output.stat().st_mode, mode)
                self.assertFalse((self.state / ".relationships.lock").exists())
                self.assertEqual(len(list(output.iterdir())), 2)

    def test_html_protected_paths_and_unknown_formats(self):
        report = self.report()
        alias = self.root / "project-alias"
        alias.symlink_to(self.project, target_is_directory=True)
        for output in (self.project, self.project / "nested/reports", self.target / "reports", alias / "reports"):
            with self.subTest(output=output):
                with self.assertRaises(rel.RelationshipError):
                    self.write(report, output, "html")
                self.assertFalse((output / rel.REPORT_FILENAMES["html"]).exists())
        for function in (self.write, lambda format_name: rel.generate_and_write(
                project_root=self.project, state_dir=self.state, registry=self.registry, output_format=format_name)):
            with self.assertRaises(rel.RelationshipError):
                function(format_name="invalid")
        self.assertFalse((self.state / ".relationships.lock").exists())

    def test_failure_at_each_format_restores_complete_set(self):
        report = self.report()
        for existing in (False, True, "legacy"):
            for extension in ("json", "md", "html"):
                with self.subTest(existing=existing, extension=extension):
                    output = self.root / f"failure-{existing}-{extension}"
                    paths = self.write(report, output, "both" if existing == "legacy" else "all") if existing else {}
                    before = {path: Path(path).read_bytes() for path in paths.values()}
                    changed = copy.deepcopy(report)
                    changed["generated_at"] = "2026-09-11T13:00:00Z"
                    real_replace = rel.os.replace
                    failed = False

                    def fail_once(source, target):
                        nonlocal failed
                        if not failed and str(target).endswith("." + extension):
                            failed = True
                            raise OSError("injected format replacement failure")
                        return real_replace(source, target)

                    with patch.object(rel.os, "replace", side_effect=fail_once):
                        with self.assertRaises(OSError):
                            self.write(changed, output)
                    self.assertTrue(failed)
                    self.assertEqual(before, {str(p): p.read_bytes() for p in output.iterdir()})
                    self.assertEqual(len(self.write(changed, output)), 3)

    def test_public_default_html_both_refresh_and_stale_retry(self):
        code, default = self.run_cli("relationships")
        self.assertEqual(code, 0)
        self.assertEqual(set(default["report_paths"]), {"json", "markdown", "html"})
        code, only = self.run_cli("relationships", "--format", "html")
        self.assertEqual(set(only["report_paths"]), {"html"})
        code, both = self.run_cli("relationships", "--format", "both")
        self.assertEqual(set(both["report_paths"]), {"json", "markdown"})
        original = {p: Path(p).read_bytes() for p in default["report_paths"].values()}
        real_replace = rel.os.replace
        failed = False

        def fail_html(source, target):
            nonlocal failed
            if not failed and str(target).endswith(".html"):
                failed = True
                raise OSError("injected HTML refresh failure")
            return real_replace(source, target)

        with patch.object(rel.os, "replace", side_effect=fail_html):
            code, stale = self.run_cli("link", "alpha", "--repo", str(self.project / "skills/alpha"))
        self.assertEqual(code, 2)
        self.assertEqual(stale["report_status"], "stale")
        self.assertEqual(set(stale["previous_report_paths"]), {"json", "markdown", "html"})
        self.assertEqual(original, {p: Path(p).read_bytes() for p in original})
        self.assertIn("relationships", stale["report_retry_command"])
        retried = subprocess.run(shlex.split(stale["report_retry_command"]), capture_output=True, text=True)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        fresh = json.loads(retried.stdout)
        self.assertEqual(set(fresh["report_paths"]), {"json", "markdown", "html"})
        code, linked = self.run_cli("link", "alpha", "--repo", str(self.project / "skills/alpha"))
        self.assertEqual(code, 0)
        self.assertIn("html", linked["report_paths"])

    def test_public_and_generator_reject_unsafe_html_output(self):
        output = self.root / "protected-html"
        output.mkdir()
        target = output / rel.REPORT_FILENAMES["html"]
        target.symlink_to(self.target / "SKILL.md")
        original = (self.target / "SKILL.md").read_bytes()
        registry_before = (self.state / "registry.json").read_bytes()
        with self.assertRaises(rel.RelationshipError):
            rel.generate_and_write(project_root=self.project, state_dir=self.state,
                                   registry=self.registry, output_dir=output, output_format="html")
        with self.assertRaises(SystemExit):
            self.run_cli("relationships", "--format", "all", "--output-dir", str(output))
        self.assertEqual(original, (self.target / "SKILL.md").read_bytes())
        self.assertEqual(registry_before, (self.state / "registry.json").read_bytes())
        self.assertTrue(target.is_symlink())
        self.assertEqual(list(output.iterdir()), [target])
        self.assertFalse((self.state / ".relationships.lock").exists())


if __name__ == "__main__":
    unittest.main()
