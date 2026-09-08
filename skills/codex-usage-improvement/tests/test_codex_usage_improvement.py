from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex_usage_improvement.py"


class CodexUsageImprovementTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def write_session(self, root: Path) -> None:
        path = root / "2026" / "09" / "08" / "rollout-2026-09-08T01-00-00-12345678-1234-1234-1234-123456789abc.jsonl"
        path.parent.mkdir(parents=True)
        events = [
            {
                "timestamp": "2026-09-08T01:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": "12345678-1234-1234-1234-123456789abc",
                    "timestamp": "2026-09-08T01:00:00Z",
                    "cwd": "/work/example",
                    "source": "desktop",
                },
            },
            {
                "timestamp": "2026-09-08T01:00:01Z",
                "type": "turn_context",
                "payload": {"model": "gpt-test"},
            },
            {
                "timestamp": "2026-09-08T01:00:02Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "functions.exec",
                    "input": "super-secret-input",
                },
            },
            {
                "timestamp": "2026-09-08T01:00:03Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {
                        "type": "UserMessage",
                        "content": "super-secret-user-message",
                    },
                },
            },
            {
                "timestamp": "2026-09-08T01:00:04Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {
                        "type": "CommandExecution",
                        "status": "failed",
                        "exit_code": 1,
                        "command": "echo super-secret-command",
                        "stdout": "super-secret-output",
                    },
                },
            },
            {
                "timestamp": "2026-09-08T01:00:05Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {"type": "ContextCompaction"},
                },
            },
            {
                "timestamp": "2026-09-08T01:00:05Z",
                "type": "compacted",
                "payload": {"window_id": "window-2"},
            },
            {
                "timestamp": "2026-09-08T01:00:05Z",
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "duration_ms": 1200,
                    "time_to_first_token_ms": 90,
                },
            },
            {
                "timestamp": "2026-09-08T01:00:06Z",
                "type": "token_usage_record",
                "payload": {
                    "thread_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 40,
                        "output_tokens": 25,
                        "reasoning_output_tokens": 5,
                        "total_tokens": 130,
                    }
                },
            },
        ]
        with path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event) + "\n")
            handle.write("not-json\n")

    def test_review_aggregates_metadata_without_leaking_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory) / "sessions"
            self.write_session(sessions)
            result = self.run_script(
                "review",
                "--sessions-root",
                str(sessions),
                "--since",
                "2026-09-08T00:00:00Z",
                "--until",
                "2026-09-09T00:00:00Z",
                "--format",
                "json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["totals"]["sessions"], 1)
            self.assertEqual(report["totals"]["user_messages"], 1)
            self.assertEqual(report["totals"]["task_runs"], 1)
            self.assertEqual(report["totals"]["duration_ms"], 1200)
            self.assertEqual(report["totals"]["compactions"], 1)
            self.assertEqual(report["totals"]["token_usage"]["total_tokens"], 130)
            self.assertEqual(report["failed_work_items"]["CommandExecution"], 1)
            self.assertEqual(report["agent_tool_calls"]["functions.exec"], 1)
            self.assertNotIn("super-secret", result.stdout)
            self.assertIn("malformed JSONL", result.stdout)

    def test_record_is_idempotent_and_list_uses_latest_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = (
                "record",
                "--state-dir",
                directory,
                "--scope",
                "project",
                "--project",
                "example",
                "--status",
                "confirmed",
                "--lesson",
                "Use a bounded review window.",
                "--evidence",
                "session abc: two broad scans",
            )
            first = self.run_script(*common)
            second = self.run_script(*common)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_payload = json.loads(first.stdout)
            self.assertTrue(first_payload["changed"])
            self.assertFalse(json.loads(second.stdout)["changed"])

            journal = Path(directory) / "learnings.jsonl"
            self.assertEqual(len(journal.read_text(encoding="utf-8").splitlines()), 1)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(journal.stat().st_mode), 0o600)

            learning_id = first_payload["record"]["id"]
            rejected = self.run_script(
                "record",
                "--state-dir",
                directory,
                "--id",
                learning_id,
                "--scope",
                "project",
                "--project",
                "example",
                "--status",
                "rejected",
                "--lesson",
                "Use a bounded review window.",
                "--evidence",
                "user rejected this as too narrow",
            )
            self.assertEqual(rejected.returncode, 0, rejected.stderr)
            listing = self.run_script("list", "--state-dir", directory, "--format", "json")
            self.assertEqual(listing.returncode, 0, listing.stderr)
            records = json.loads(listing.stdout)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "rejected")

    def test_malformed_journal_fails_closed_before_recording(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "learnings.jsonl"
            original = "not-json\n"
            journal.write_text(original, encoding="utf-8")
            result = self.run_script(
                "record",
                "--state-dir",
                directory,
                "--scope",
                "global",
                "--lesson",
                "Never overwrite malformed state.",
                "--evidence",
                "controlled malformed fixture",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("malformed journal", result.stderr)
            self.assertEqual(journal.read_text(encoding="utf-8"), original)

    def test_invalid_existing_record_fails_closed_before_recording(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "learnings.jsonl"
            original = json.dumps({"schema_version": 1, "id": "bad", "status": "invented"}) + "\n"
            journal.write_text(original, encoding="utf-8")
            result = self.run_script(
                "record",
                "--state-dir",
                directory,
                "--scope",
                "global",
                "--lesson",
                "Validate the whole journal before appending.",
                "--evidence",
                "controlled invalid fixture",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid journal record", result.stderr)
            self.assertEqual(journal.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
