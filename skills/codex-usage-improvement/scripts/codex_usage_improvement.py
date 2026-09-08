#!/usr/bin/env python3
"""Review Codex session metadata and manage a user-confirmed learning journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


JOURNAL_NAME = "learnings.jsonl"
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
STATUSES = ("candidate", "confirmed", "rejected", "superseded")
SCOPES = ("project", "global")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


class UsageError(Exception):
    """Raised for expected input, state, or session errors."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise UsageError(f"invalid ISO-8601 timestamp: {value}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def default_sessions_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home).expanduser() / "sessions" if codex_home else Path.home() / ".codex" / "sessions"


def default_state_dir() -> Path:
    override = os.environ.get("CODEX_USAGE_IMPROVEMENT_STATE_DIR")
    if override:
        return Path(override).expanduser()
    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state).expanduser() if xdg_state else Path.home() / ".local" / "state"
    return base / "codex-usage-improvement"


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def integer(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def safe_label(value: Any, fallback: str = "unknown") -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return " ".join(value.split())[:120]


def markdown_text(value: Any) -> str:
    return safe_label(value).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


@dataclass
class SessionSummary:
    session_id: str
    started_at: datetime
    cwd: str = ""
    model: str = "unknown"
    source: str = "unknown"
    user_messages: int = 0
    agent_messages: int = 0
    task_runs: int = 0
    duration_ms: int = 0
    time_to_first_token_ms: int = 0
    compactions: int = 0
    malformed_lines: int = 0
    agent_tool_calls: Counter[str] = field(default_factory=Counter)
    work_items: Counter[str] = field(default_factory=Counter)
    failed_work_items: Counter[str] = field(default_factory=Counter)
    token_usage: dict[str, int] = field(default_factory=lambda: {name: 0 for name in TOKEN_FIELDS})
    _fallback_user_messages: int = 0
    _fallback_agent_messages: int = 0
    _compacted_events: int = 0
    _compaction_items: int = 0

    @property
    def project(self) -> str:
        if not self.cwd:
            return "unknown"
        return Path(self.cwd).name or "root"

    def finish(self) -> None:
        if self.user_messages == 0:
            self.user_messages = self._fallback_user_messages
        if self.agent_messages == 0:
            self.agent_messages = self._fallback_agent_messages
        self.compactions = self._compacted_events or self._compaction_items

    def public(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": isoformat(self.started_at),
            "project": self.project,
            "model": self.model,
            "source": self.source,
            "user_messages": self.user_messages,
            "agent_messages": self.agent_messages,
            "task_runs": self.task_runs,
            "duration_ms": self.duration_ms,
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "compactions": self.compactions,
            "malformed_lines": self.malformed_lines,
            "agent_tool_calls": dict(self.agent_tool_calls.most_common()),
            "work_items": dict(self.work_items.most_common()),
            "failed_work_items": dict(self.failed_work_items.most_common()),
            "token_usage": self.token_usage,
        }


def item_failure_label(item: dict[str, Any]) -> str | None:
    status = item.get("status")
    exit_code = item.get("exit_code")
    if status == "failed" or (isinstance(exit_code, int) and exit_code != 0):
        item_type = safe_label(item.get("type"), "UnknownWorkItem")
        if item_type == "McpToolCall":
            server = safe_label(item.get("server"), "mcp")
            tool = safe_label(item.get("tool"), "unknown")
            return f"{item_type}:{server}.{tool}"
        return item_type
    return None


def token_usage_from(value: Any) -> dict[str, int]:
    data = as_dict(value)
    return {name: integer(data.get(name)) for name in TOKEN_FIELDS}


def read_session(path: Path) -> SessionSummary:
    try:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError as error:
        raise UsageError(f"cannot inspect session log {path}: {error}") from error
    summary = SessionSummary(session_id=path.stem.removeprefix("rollout-")[-36:], started_at=modified_at)
    first_timestamp_seen = False
    fallback_tokens: dict[str, int] | None = None

    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError as error:
        raise UsageError(f"cannot read session log {path}: {error}") from error

    with handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                summary.malformed_lines += 1
                continue
            if not isinstance(event, dict):
                summary.malformed_lines += 1
                continue
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str) and not first_timestamp_seen:
                try:
                    parsed = parse_timestamp(timestamp)
                except UsageError:
                    pass
                else:
                    summary.started_at = parsed
                    first_timestamp_seen = True
            payload = as_dict(event.get("payload"))
            if event.get("type") == "session_meta":
                summary.session_id = safe_label(
                    payload.get("id") or payload.get("session_id"), summary.session_id
                )
                summary.cwd = safe_label(payload.get("cwd"), "")
                summary.source = safe_label(payload.get("source"), summary.source)
                metadata_timestamp = payload.get("timestamp") or timestamp
                if isinstance(metadata_timestamp, str):
                    try:
                        summary.started_at = parse_timestamp(metadata_timestamp)
                    except UsageError:
                        pass
            elif event.get("type") == "turn_context":
                summary.model = safe_label(payload.get("model"), summary.model)
                if not summary.cwd:
                    summary.cwd = safe_label(payload.get("cwd"), "")

            event_type = event.get("type")
            payload_type = payload.get("type")
            if event_type == "compacted":
                summary._compacted_events += 1
            if payload_type == "message":
                role = payload.get("role")
                if role == "user":
                    summary._fallback_user_messages += 1
                elif role == "assistant":
                    summary._fallback_agent_messages += 1
            elif payload_type in {"custom_tool_call", "function_call"}:
                namespace = payload.get("namespace")
                name = safe_label(payload.get("name"), "unknown")
                label = f"{namespace}.{name}" if isinstance(namespace, str) and namespace else name
                summary.agent_tool_calls[label] += 1
            elif payload_type == "task_complete":
                summary.task_runs += 1
                summary.duration_ms += integer(payload.get("duration_ms"))
                summary.time_to_first_token_ms += integer(payload.get("time_to_first_token_ms"))
            elif payload_type == "item_completed":
                item = as_dict(payload.get("item"))
                item_type = safe_label(item.get("type"), "UnknownWorkItem")
                summary.work_items[item_type] += 1
                if item_type == "UserMessage":
                    summary.user_messages += 1
                elif item_type == "AgentMessage":
                    summary.agent_messages += 1
                elif item_type == "ContextCompaction":
                    summary._compaction_items += 1
                failure = item_failure_label(item)
                if failure:
                    summary.failed_work_items[failure] += 1
            if event_type == "token_usage_record":
                summary.token_usage = token_usage_from(
                    payload.get("thread_token_usage") or payload.get("usage")
                )
            elif payload_type == "token_count":
                info = as_dict(payload.get("info"))
                fallback_tokens = token_usage_from(info.get("total_token_usage"))

    if not any(summary.token_usage.values()) and fallback_tokens:
        summary.token_usage = fallback_tokens
    summary.finish()
    return summary


def is_within_project(cwd: str, project_root: Path) -> bool:
    if not cwd:
        return False
    try:
        Path(cwd).expanduser().resolve().relative_to(project_root)
    except (OSError, ValueError):
        return False
    return True


def iter_session_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise UsageError(f"sessions root does not exist: {root}")
    if not root.is_dir():
        raise UsageError(f"sessions root is not a directory: {root}")
    yield from (
        path for path in sorted(root.rglob("rollout-*.jsonl")) if path.is_file() and not path.is_symlink()
    )


def summarize_sessions(
    root: Path,
    since: datetime,
    until: datetime,
    project_root: Path | None,
) -> dict[str, Any]:
    sessions: list[SessionSummary] = []
    unreadable: list[str] = []
    for path in iter_session_files(root):
        try:
            summary = read_session(path)
        except UsageError:
            unreadable.append(path.name)
            continue
        if not since <= summary.started_at <= until:
            continue
        if project_root is not None and not is_within_project(summary.cwd, project_root):
            continue
        sessions.append(summary)

    sessions.sort(key=lambda item: item.started_at)
    totals: dict[str, Any] = {
        "sessions": len(sessions),
        "user_messages": sum(item.user_messages for item in sessions),
        "agent_messages": sum(item.agent_messages for item in sessions),
        "task_runs": sum(item.task_runs for item in sessions),
        "duration_ms": sum(item.duration_ms for item in sessions),
        "time_to_first_token_ms": sum(item.time_to_first_token_ms for item in sessions),
        "compactions": sum(item.compactions for item in sessions),
        "malformed_lines": sum(item.malformed_lines for item in sessions),
        "token_usage": {
            name: sum(item.token_usage[name] for item in sessions) for name in TOKEN_FIELDS
        },
    }
    agent_tools: Counter[str] = Counter()
    work_items: Counter[str] = Counter()
    failed_items: Counter[str] = Counter()
    for item in sessions:
        agent_tools.update(item.agent_tool_calls)
        work_items.update(item.work_items)
        failed_items.update(item.failed_work_items)

    warnings: list[str] = []
    if unreadable:
        warnings.append(f"{len(unreadable)} session files could not be read")
    if totals["malformed_lines"]:
        warnings.append(f"{totals['malformed_lines']} malformed JSONL lines were skipped")
    if not sessions:
        warnings.append("no sessions matched the selected window and project scope")

    return {
        "generated_at": isoformat(utc_now()),
        "window": {"since": isoformat(since), "until": isoformat(until)},
        "scope": {"project": project_root.name if project_root else "all"},
        "totals": totals,
        "agent_tool_calls": dict(agent_tools.most_common()),
        "work_items": dict(work_items.most_common()),
        "failed_work_items": dict(failed_items.most_common()),
        "warnings": warnings,
        "sessions": [item.public() for item in sessions],
    }


def markdown_table(mapping: dict[str, int], empty: str = "None observed") -> list[str]:
    if not mapping:
        return [empty]
    lines = ["| Item | Count |", "| --- | ---: |"]
    lines.extend(f"| {markdown_text(name)} | {count} |" for name, count in mapping.items())
    return lines


def report_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    token_usage = totals["token_usage"]
    lines = [
        "# Codex Usage Review",
        "",
        f"Window: {report['window']['since']} to {report['window']['until']}",
        f"Project scope: {markdown_text(report['scope']['project'])}",
        "",
        "## Totals",
        "",
        f"- Sessions: {totals['sessions']}",
        f"- User messages: {totals['user_messages']}",
        f"- Agent messages: {totals['agent_messages']}",
        f"- Task runs: {totals['task_runs']}",
        f"- Duration: {totals['duration_ms']} ms",
        f"- Compactions: {totals['compactions']}",
        f"- Total tokens: {token_usage['total_tokens']}",
        "",
        "## Agent Tool Calls",
        "",
        *markdown_table(report["agent_tool_calls"]),
        "",
        "## Failed Work Items",
        "",
        *markdown_table(report["failed_work_items"]),
        "",
        "## Data Quality",
        "",
    ]
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- No parser warnings.")
    return "\n".join(lines) + "\n"


def journal_path(state_dir: Path) -> Path:
    return state_dir / JOURNAL_NAME


def validate_journal_record(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"invalid journal record at line {line_number}"
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise UsageError(prefix)
    if not isinstance(record.get("id"), str) or not ID_PATTERN.fullmatch(record["id"]):
        raise UsageError(f"{prefix}: invalid id")
    if record.get("scope") not in SCOPES or record.get("status") not in STATUSES:
        raise UsageError(f"{prefix}: invalid scope or status")
    if not isinstance(record.get("recorded_at"), str):
        raise UsageError(f"{prefix}: missing recorded_at")
    try:
        parse_timestamp(record["recorded_at"])
    except UsageError as error:
        raise UsageError(f"{prefix}: {error}") from error
    project = record.get("project")
    if record["scope"] == "project" and not isinstance(project, str):
        raise UsageError(f"{prefix}: project scope requires project")
    if record["scope"] == "global" and project is not None:
        raise UsageError(f"{prefix}: global scope cannot define project")
    if not isinstance(record.get("category"), str) or not isinstance(record.get("lesson"), str):
        raise UsageError(f"{prefix}: invalid category or lesson")
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        raise UsageError(f"{prefix}: invalid evidence")
    return record


def load_journal(state_dir: Path) -> list[dict[str, Any]]:
    path = journal_path(state_dir)
    if not path.exists():
        return []
    if not path.is_file() or path.is_symlink():
        raise UsageError(f"journal must be a regular file: {path}")
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise UsageError(f"cannot read journal {path}: {error}") from error
    for line_number, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise UsageError(f"malformed journal line {line_number}: {error.msg}") from error
        records.append(validate_journal_record(record, line_number))
    return records


def latest_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        latest[record["id"]] = record
    return sorted(latest.values(), key=lambda item: (str(item.get("recorded_at", "")), item["id"]))


def validate_text(value: str, field_name: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise UsageError(f"{field_name} must not be empty")
    if len(cleaned) > limit:
        raise UsageError(f"{field_name} must be at most {limit} characters")
    return cleaned


def append_record(state_dir: Path, record: dict[str, Any]) -> None:
    if state_dir.exists() and (not state_dir.is_dir() or state_dir.is_symlink()):
        raise UsageError(f"state directory must be a regular directory: {state_dir}")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass
    path = journal_path(state_dir)
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise UsageError(f"journal must be a regular file: {path}")
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    try:
        descriptor = os.open(path, flags, 0o600)
        try:
            os.write(descriptor, data)
        finally:
            os.close(descriptor)
        os.chmod(path, 0o600)
    except OSError as error:
        raise UsageError(f"cannot append journal {path}: {error}") from error


def command_review(args: argparse.Namespace) -> int:
    now = utc_now()
    until = parse_timestamp(args.until) if args.until else now
    since = parse_timestamp(args.since) if args.since else until - timedelta(days=args.days)
    if since > until:
        raise UsageError("review start must not be after review end")
    sessions_root = Path(args.sessions_root).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else None
    report = summarize_sessions(sessions_root, since, until, project_root)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(report_markdown(report), end="")
    return 0


def command_record(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).expanduser().resolve()
    existing = load_journal(state_dir)
    lesson = validate_text(args.lesson, "lesson", 1000)
    project = validate_text(args.project, "project", 200) if args.project else None
    if args.scope == "project" and not project:
        raise UsageError("--project is required for project-scoped lessons")
    if args.scope == "global" and project:
        raise UsageError("--project cannot be used for global lessons")
    evidence = [validate_text(item, "evidence", 500) for item in args.evidence]
    if len(evidence) > 20:
        raise UsageError("at most 20 evidence references may be recorded")
    category = validate_text(args.category, "category", 64)
    generated_id = "learn-" + hashlib.sha256(
        f"{args.scope}\0{project or ''}\0{lesson.casefold()}".encode("utf-8")
    ).hexdigest()[:12]
    learning_id = args.id or generated_id
    if not ID_PATTERN.fullmatch(learning_id):
        raise UsageError("learning id must be 3-64 lowercase letters, digits, or hyphens")
    record = {
        "schema_version": 1,
        "id": learning_id,
        "recorded_at": isoformat(utc_now()),
        "scope": args.scope,
        "project": project,
        "category": category,
        "status": args.status,
        "lesson": lesson,
        "evidence": evidence,
    }
    prior = next((item for item in reversed(existing) if item["id"] == learning_id), None)
    comparable = ("scope", "project", "category", "status", "lesson", "evidence")
    if prior and all(prior.get(key) == record.get(key) for key in comparable):
        print(json.dumps({"changed": False, "record": prior}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    append_record(state_dir, record)
    print(json.dumps({"changed": True, "record": record}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_list(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).expanduser().resolve()
    records = latest_records(load_journal(state_dir))
    filtered = [
        item
        for item in records
        if (args.status is None or item.get("status") == args.status)
        and (args.scope is None or item.get("scope") == args.scope)
        and (args.project is None or item.get("project") == args.project)
    ]
    if args.format == "json":
        print(json.dumps(filtered, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not filtered:
        print("No learning records matched.")
        return 0
    print("# Codex Usage Learnings\n")
    for item in filtered:
        print(
            f"- `{item['id']}` [{markdown_text(item.get('status'))}] "
            f"({markdown_text(item.get('scope'))}) {markdown_text(item.get('lesson'))}"
        )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    review = commands.add_parser("review", help="summarize local Codex session metadata")
    review.add_argument("--sessions-root", default=str(default_sessions_root()))
    window = review.add_mutually_exclusive_group()
    window.add_argument("--days", type=float, default=7.0)
    window.add_argument("--since")
    review.add_argument("--until")
    review.add_argument("--project-root")
    review.add_argument("--format", choices=("markdown", "json"), default="markdown")
    review.set_defaults(handler=command_review)

    record = commands.add_parser("record", help="append a structured learning event")
    record.add_argument("--state-dir", default=str(default_state_dir()))
    record.add_argument("--id")
    record.add_argument("--scope", choices=SCOPES, required=True)
    record.add_argument("--project")
    record.add_argument("--category", default="workflow")
    record.add_argument("--status", choices=STATUSES, default="candidate")
    record.add_argument("--lesson", required=True)
    record.add_argument("--evidence", action="append", required=True)
    record.set_defaults(handler=command_record)

    listing = commands.add_parser("list", help="show the latest state of recorded learnings")
    listing.add_argument("--state-dir", default=str(default_state_dir()))
    listing.add_argument("--status", choices=STATUSES)
    listing.add_argument("--scope", choices=SCOPES)
    listing.add_argument("--project")
    listing.add_argument("--format", choices=("markdown", "json"), default="markdown")
    listing.set_defaults(handler=command_list)
    return root


def main() -> int:
    args = parser().parse_args()
    if getattr(args, "days", 1) <= 0:
        print("ERROR: --days must be greater than zero", file=sys.stderr)
        return 2
    try:
        return args.handler(args)
    except UsageError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
