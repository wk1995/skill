"""Regression tests for Skill issue label synchronization.

The stub server mirrors the two GitHub behaviours the tool depends on: a label
rename keeps the label object (and therefore every issue association) while a
delete followed by a create produces a new object and loses all associations.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/skill_labels.py"
COLOR = "1D76DB"


class Store:
    def __init__(self) -> None:
        self.labels: dict[str, dict[str, object]] = {}
        self.issues: dict[int, set[int]] = {}
        self.requests: list[tuple[str, str, dict[str, object] | None]] = []
        self.next_id = 1

    def seed(self, name: str, color: str = COLOR, description: str | None = None, issues: tuple[int, ...] = ()):
        label = {
            "id": self.next_id,
            "name": name,
            "color": color,
            "description": f"Issues related to the {name} Skill." if description is None else description,
        }
        self.next_id += 1
        self.labels[name] = label
        for number in issues:
            self.issues.setdefault(number, set()).add(int(label["id"]))
        return label

    def issue_labels(self, number: int) -> list[str]:
        identifiers = self.issues.get(number, set())
        return sorted(label["name"] for label in self.labels.values() if label["id"] in identifiers)

    def mutations(self) -> list[tuple[str, str, dict[str, object] | None]]:
        return [request for request in self.requests if request[0] != "GET"]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # keep test output clean
        pass

    def _payload(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw) if raw else {}

    def _send(self, status: int, payload=None, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _label_name(self) -> str:
        suffix = urlparse(self.path).path.split("/labels/", 1)[1]
        return unquote(suffix)

    def _routed(self) -> bool:
        if urlparse(self.path).path.startswith("/repos/owner/repo/labels"):
            return True
        self._send(404, {"message": "Not Found"})
        return False

    def do_GET(self) -> None:
        if not self._routed():
            return
        store = self.server.store
        store.requests.append(("GET", self.path, None))
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        per_page = int(query.get("per_page", ["100"])[0])
        page = int(query.get("page", ["1"])[0])
        names = sorted(store.labels)
        window = names[(page - 1) * per_page : page * per_page]
        headers = {}
        if page * per_page < len(names):
            host = self.headers.get("Host", "127.0.0.1")
            headers["Link"] = (
                f'<http://{host}{parsed.path}?per_page={per_page}&page={page + 1}>; rel="next"'
            )
        self._send(200, [store.labels[name] for name in window], headers)

    def do_POST(self) -> None:
        if not self._routed():
            return
        store = self.server.store
        payload = self._payload()
        store.requests.append(("POST", self.path, payload))
        name = str(payload.get("name", ""))
        if name in store.labels:
            self._send(422, {"message": "Validation Failed", "errors": [{"code": "already_exists", "field": "name"}]})
            return
        if len(name) > 50:
            self._send(422, {"message": "Validation Failed", "errors": [{"message": "name is too long (maximum is 50 characters)"}]})
            return
        label = store.seed(name, str(payload.get("color", "")), str(payload.get("description", "")))
        self._send(201, label)

    def do_PATCH(self) -> None:
        if not self._routed():
            return
        store = self.server.store
        payload = self._payload()
        name = self._label_name()
        store.requests.append(("PATCH", self.path, payload))
        label = store.labels.get(name)
        if label is None:
            self._send(404, {"message": "Not Found"})
            return
        new_name = payload.get("new_name")
        if new_name is not None:
            new_name = str(new_name)
            if new_name in store.labels and new_name != name:
                self._send(422, {"message": "Validation Failed", "errors": [{"code": "already_exists", "field": "name"}]})
                return
            # The label keeps its id, exactly like GitHub's rename.
            store.labels[new_name] = label
            label["name"] = new_name
            if new_name != name:
                del store.labels[name]
        for key in ("color", "description"):
            if key in payload:
                label[key] = payload[key]
        self._send(200, label)

    def do_DELETE(self) -> None:
        if not self._routed():
            return
        store = self.server.store
        name = self._label_name()
        store.requests.append(("DELETE", self.path, None))
        label = store.labels.pop(name, None)
        if label is None:
            self._send(404, {"message": "Not Found"})
            return
        for identifiers in store.issues.values():
            identifiers.discard(int(label["id"]))
        self._send(204)


class SkillLabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="skill-labels-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "skills").mkdir()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.store = Store()
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.api_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    @property
    def store(self) -> Store:
        return self.server.store

    def write_skill(self, name: str, sync_id: str | None = None) -> Path:
        directory = self.root / "skills" / name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "SKILL.md"
        path.write_text(
            "---\n"
            f"name: {name}\n"
            "description: Fixture Skill used by the label tests.\n"
            "metadata:\n"
            f'  sync_id: "{sync_id or name}"\n'
            '  version: "0.1.0"\n'
            "---\n\n# Fixture\n",
            encoding="utf-8",
        )
        return path

    def init_repo(self) -> None:
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Label Test")
        self.git("config", "user.email", "labels@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True)

    def run_tool(self, *args: str, token: str | None = "test-token") -> subprocess.CompletedProcess:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"GITHUB_TOKEN", "GH_TOKEN", "GITHUB_REPOSITORY", "GITHUB_API_URL"}
        }
        if token is not None:
            environment["GITHUB_TOKEN"] = token
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.root),
                "--repository",
                "owner/repo",
                "--api-url",
                self.api_url,
                *args,
            ],
            capture_output=True,
            text=True,
            env=environment,
            timeout=120,
        )

    def test_creates_missing_labels_and_is_idempotent(self) -> None:
        self.write_skill("alpha")
        self.write_skill("beta", "beta-sync")

        missing = self.run_tool("--check")
        self.assertEqual(missing.returncode, 1, missing.stderr)

        applied = self.run_tool("--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(sorted(self.store.labels), ["alpha", "beta"])
        self.assertEqual(self.store.labels["alpha"]["description"], "Issues related to the alpha Skill.")
        self.assertEqual(self.store.labels["beta"]["color"], COLOR)

        self.store.requests.clear()
        again = self.run_tool("--apply")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.store.mutations(), [])
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_rename_keeps_issue_associations(self) -> None:
        self.write_skill("new-skill", "stable-identity")
        self.store.seed("old-skill", issues=(7,))

        result = self.run_tool("--apply", "--rename", "old-skill=new-skill")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(self.store.labels), ["new-skill"])
        self.assertEqual(self.store.issue_labels(7), ["new-skill"])
        self.assertEqual([request[0] for request in self.store.mutations()], ["PATCH"])
        self.assertEqual(
            self.store.labels["new-skill"]["description"], "Issues related to the new-skill Skill."
        )

    def test_base_detects_rename(self) -> None:
        self.write_skill("old-name", "kept-identity")
        self.init_repo()
        self.git("add", "-A")
        self.git("commit", "-qm", "add old-name")
        (self.root / "skills" / "old-name").rename(self.root / "skills" / "new-name")
        (self.root / "skills" / "new-name" / "SKILL.md").write_text(
            (self.root / "skills" / "new-name" / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("name: old-name", "name: new-name"),
            encoding="utf-8",
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "rename to new-name")
        self.store.seed("old-name", issues=(11,))

        result = self.run_tool("--apply", "--base", "HEAD^")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(self.store.labels), ["new-name"])
        self.assertEqual(self.store.issue_labels(11), ["new-name"])

    def test_base_that_is_not_a_predecessor_skips_rename_detection(self) -> None:
        self.write_skill("old-name", "kept-identity")
        self.init_repo()
        self.git("add", "-A")
        self.git("commit", "-qm", "add old-name")
        self.git("checkout", "-q", "-b", "side")
        (self.root / "skills" / "old-name" / "SKILL.md").write_text(
            (self.root / "skills" / "old-name" / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("Fixture Skill used", "Side branch edit of the"),
            encoding="utf-8",
        )
        self.git("commit", "-qam", "side edit")
        self.git("checkout", "-q", "main")
        (self.root / "skills" / "old-name").rename(self.root / "skills" / "new-name")
        (self.root / "skills" / "new-name" / "SKILL.md").write_text(
            (self.root / "skills" / "new-name" / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("name: old-name", "name: new-name"),
            encoding="utf-8",
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "rename to new-name")
        self.store.seed("old-name", issues=(21,))

        result = self.run_tool("--apply", "--base", "side")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not an ancestor", result.stdout)
        self.assertEqual(sorted(self.store.labels), ["new-name", "old-name"])
        self.assertEqual(self.store.issue_labels(21), ["old-name"])

    def test_prune_never_deletes_a_rename_source(self) -> None:
        self.write_skill("old-name", "kept-identity")
        self.init_repo()
        self.git("add", "-A")
        self.git("commit", "-qm", "add old-name")
        (self.root / "skills" / "old-name").rename(self.root / "skills" / "new-name")
        (self.root / "skills" / "new-name" / "SKILL.md").write_text(
            (self.root / "skills" / "new-name" / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("name: old-name", "name: new-name"),
            encoding="utf-8",
        )
        self.git("add", "-A")
        self.git("commit", "-qm", "rename to new-name")
        self.store.seed("old-name", issues=(13,))

        result = self.run_tool("--apply", "--prune", "--base", "HEAD^")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.store.issue_labels(13), ["new-name"])
        self.assertNotIn(("DELETE", "/repos/owner/repo/labels/old-name", None), self.store.requests)

    def test_rename_onto_an_existing_label_is_rejected_without_mutation(self) -> None:
        self.write_skill("new-skill", "stable-identity")
        self.store.seed("old-skill", issues=(3,))
        self.store.seed("new-skill", description="Hand written label")

        result = self.run_tool("--apply", "--rename", "old-skill=new-skill")

        self.assertEqual(result.returncode, 1)
        self.assertIn("already uses that name", result.stderr)
        self.assertEqual(self.store.mutations(), [])
        self.assertEqual(self.store.issue_labels(3), ["old-skill"])

    def test_removed_skill_label_is_kept_until_prune(self) -> None:
        self.write_skill("live-skill")
        self.store.seed("gone-skill", issues=(5,))

        kept = self.run_tool("--apply")

        self.assertEqual(kept.returncode, 0, kept.stderr)
        self.assertIn("KEEP", kept.stdout)
        self.assertIn("gone-skill", self.store.labels)
        self.assertEqual(self.store.issue_labels(5), ["gone-skill"])

        pruned = self.run_tool("--apply", "--prune")

        self.assertEqual(pruned.returncode, 0, pruned.stderr)
        self.assertNotIn("gone-skill", self.store.labels)
        self.assertEqual(self.store.issue_labels(5), [])

    def test_empty_skills_tree_is_rejected_before_deletion(self) -> None:
        self.store.seed("live-skill", issues=(9,))

        result = self.run_tool("--apply", "--prune")

        self.assertEqual(result.returncode, 1)
        self.assertIn("no Skill", result.stderr)
        self.assertEqual(self.store.mutations(), [])
        self.assertIn("live-skill", self.store.labels)

    def test_overlong_skill_name_is_rejected_before_any_request(self) -> None:
        self.write_skill("x" * 60, "unique-identity")

        result = self.run_tool("--apply")

        self.assertEqual(result.returncode, 1)
        self.assertIn("50", result.stderr)
        self.assertEqual(self.store.requests, [])

    def test_duplicate_sync_id_is_rejected_before_any_request(self) -> None:
        self.write_skill("alpha", "shared")
        self.write_skill("beta", "shared")

        result = self.run_tool("--apply")

        self.assertEqual(result.returncode, 1)
        self.assertIn("already used by", result.stderr)
        self.assertEqual(self.store.requests, [])

    def test_matching_label_is_adopted_and_normalized_only_on_request(self) -> None:
        self.write_skill("demo")
        self.store.seed("demo", color="FFFFFF", description="")

        checked = self.run_tool("--check")

        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("NOTE", checked.stdout)
        self.assertEqual(self.store.mutations(), [])

        normalized = self.run_tool("--apply", "--normalize")

        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        self.assertEqual(self.store.labels["demo"]["color"], COLOR)
        self.assertEqual(self.store.labels["demo"]["description"], "Issues related to the demo Skill.")
        self.assertEqual(self.run_tool("--check", "--normalize").returncode, 0)

    def test_case_variant_label_is_renamed_not_duplicated(self) -> None:
        self.write_skill("demo")
        self.store.seed("Demo", issues=(17,))

        result = self.run_tool("--apply")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(self.store.labels), ["demo"])
        self.assertEqual(self.store.issue_labels(17), ["demo"])
        self.assertEqual([request[0] for request in self.store.mutations()], ["PATCH"])

    def test_pagination_reads_every_page(self) -> None:
        for name in ("alpha", "beta", "gamma"):
            self.write_skill(name)
            self.store.seed(name)

        result = self.run_tool("--apply", "--per-page", "1")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.store.mutations(), [])

    def test_apply_requires_a_token(self) -> None:
        self.write_skill("alpha")

        result = self.run_tool("--apply", token=None)

        self.assertEqual(result.returncode, 1)
        self.assertIn("token", result.stderr)
        self.assertEqual(self.store.requests, [])

    def test_api_errors_are_reported(self) -> None:
        self.write_skill("alpha")
        self.store.seed("alpha", color="FFFFFF", description="")

        result = self.run_tool("--apply", "--normalize", "--api-url", self.api_url + "/missing")

        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub API", result.stderr)


if __name__ == "__main__":
    unittest.main()
