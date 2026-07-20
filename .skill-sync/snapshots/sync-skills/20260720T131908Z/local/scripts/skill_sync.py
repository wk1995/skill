#!/usr/bin/env python3
"""Synchronize linked Agent Skill directory copies with snapshots and rollback."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORE_DIRS = {".git", "node_modules", "dist", "__pycache__", ".pytest_cache"}
IGNORE_FILES = {".DS_Store"}
BYTECODE_SUFFIXES = {".pyc", ".pyo"}
DEFAULT_STATE_DIR = ".skill-sync"
ROLE_FLAGS = ("repo", "local", "project", "external")


def utc_snapshot_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def min_iso(values: list[str | None]) -> str | None:
    parsed = [(parse_iso(value), value) for value in values if value]
    parsed = [(dt, value) for dt, value in parsed if dt is not None]
    if not parsed:
        return None
    return min(parsed, key=lambda item: item[0])[1]


def max_iso(values: list[str | None]) -> str | None:
    parsed = [(parse_iso(value), value) for value in values if value]
    parsed = [(dt, value) for dt, value in parsed if dt is not None]
    if not parsed:
        return None
    return max(parsed, key=lambda item: item[0])[1]


def resolve_path(path: str | None) -> str | None:
    if not path:
        return None
    return str(Path(path).expanduser().resolve())


def should_ignore(path: Path) -> bool:
    if path.name in IGNORE_FILES:
        return True
    if path.suffix in BYTECODE_SUFFIXES:
        return True
    return any(part in IGNORE_DIRS for part in path.parts)


def require_skill_dir(path: str, role: str) -> Path:
    skill_dir = Path(path)
    if not skill_dir.exists():
        raise SystemExit(f"{role}: path does not exist: {path}")
    if not skill_dir.is_dir():
        raise SystemExit(f"{role}: path is not a directory: {path}")
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"{role}: missing SKILL.md: {path}")
    return skill_dir


def copy_skill_tree(source: Path, target: Path) -> None:
    if target.exists() and not target.is_dir():
        raise SystemExit(f"target exists and is not a directory: {target}")
    target.mkdir(parents=True, exist_ok=True)

    for child in target.iterdir():
        if child.name in IGNORE_DIRS:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    for item in source.iterdir():
        if should_ignore(item):
            continue
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, ignore=ignore_names)
        else:
            shutil.copy2(item, destination)


def iter_skill_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*") if p.is_file() and not should_ignore(p))


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_empty_dir(path: Path) -> bool:
    return path.is_dir() and not any(path.iterdir())


def ignore_names(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        candidate = Path(directory) / name
        if should_ignore(candidate):
            ignored.add(name)
    return ignored


def digest_skill_dir(path: Path) -> str:
    hasher = hashlib.sha256()
    for file_path in iter_skill_files(path):
        relative = file_path.relative_to(path).as_posix()
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def latest_skill_update_time(path: Path) -> str:
    git_time = git_commit_time(path, first=False)
    if git_time:
        return git_time
    newest = path.stat().st_mtime
    for file_path in iter_skill_files(path):
        newest = max(newest, file_path.stat().st_mtime)
    return iso_from_timestamp(newest)


def git_commit_time(path: Path, first: bool) -> str | None:
    if not shutil.which("git"):
        return None
    args = ["git", "-C", str(path), "log", "--format=%cI"]
    if first:
        args.append("--reverse")
    else:
        args.append("-1")
    args.extend(["--", "."])
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def git_remote_url(path: Path) -> str | None:
    if not shutil.which("git"):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    return remote or None


def read_skill_metadata(path: Path) -> dict[str, Any]:
    skill_md = path / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8").lstrip("\ufeff")
    frontmatter = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            frontmatter = text[3:end]
    name = match_yaml_scalar(frontmatter, "name")
    version = match_yaml_scalar(frontmatter, "version")
    urls = parse_metadata_url_values(frontmatter)
    return {"name": name, "version": version, "urls": urls}


def parse_metadata_url_values(frontmatter: str) -> list[str]:
    urls: list[str] = []
    in_urls = False
    urls_indent = 0
    for line in frontmatter.splitlines():
        if not in_urls:
            match = re.match(r"^(\s*)urls\s*:\s*$", line)
            if match:
                in_urls = True
                urls_indent = len(match.group(1))
            continue

        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= urls_indent and not line.lstrip().startswith("-"):
            break
        value_match = re.match(r"^\s*value\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$", line)
        if value_match:
            urls.append(value_match.group(1).strip())
    return urls


def match_yaml_scalar(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def load_registry(state_dir: Path) -> dict[str, Any]:
    registry_path = state_dir / "registry.json"
    if not registry_path.exists():
        return {"groups": {}}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def save_registry(state_dir: Path, registry: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    registry_path = state_dir / "registry.json"
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_or_create_group(registry: dict[str, Any], group_name: str) -> dict[str, Any]:
    groups = registry.setdefault("groups", {})
    if group_name not in groups:
        groups[group_name] = {
            "roles": {},
            "role_urls": {},
            "snapshots": [],
            "skill_urls": [],
            "version_history": {},
        }
    group = groups[group_name]
    group.setdefault("roles", {})
    group.setdefault("role_urls", {})
    group.setdefault("snapshots", [])
    group.setdefault("skill_urls", [])
    group.setdefault("version_history", {})
    return group


def existing_members(group: dict[str, Any]) -> dict[str, str]:
    return {role: path for role, path in group.get("roles", {}).items() if Path(path).exists()}


def build_member_state(group: dict[str, Any]) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for role, path in existing_members(group).items():
        skill_dir = require_skill_dir(path, role)
        metadata = read_skill_metadata(skill_dir)
        git_first_commit_at = git_commit_time(skill_dir, first=True)
        git_latest_commit_at = git_commit_time(skill_dir, first=False)
        remote_url = group.get("role_urls", {}).get(role) or git_remote_url(skill_dir)
        content_updated_at = git_latest_commit_at or latest_skill_update_time(skill_dir)
        state[role] = {
            "path": str(skill_dir),
            "url": remote_url,
            "digest": digest_skill_dir(skill_dir),
            "content_updated_at": content_updated_at,
            "content_updated_at_source": "git" if git_latest_commit_at else "filesystem",
            "git_first_commit_at": git_first_commit_at,
            "git_latest_commit_at": git_latest_commit_at,
            "metadata_urls": metadata["urls"],
            "name": metadata["name"],
            "version": metadata["version"],
        }
    return state


def create_snapshot(state_dir: Path, group_name: str, group: dict[str, Any], operation: str, source: str | None) -> str:
    base_snapshot_id = utc_snapshot_id()
    snapshot_id = base_snapshot_id
    snapshot_dir = state_dir / "snapshots" / group_name / snapshot_id
    sequence = 2
    while snapshot_dir.exists():
        snapshot_id = f"{base_snapshot_id}-{sequence}"
        snapshot_dir = state_dir / "snapshots" / group_name / snapshot_id
        sequence += 1
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    member_state = build_member_state(group)
    for role, info in member_state.items():
        copy_skill_tree(Path(str(info["path"])), snapshot_dir / role)

    manifest = {
        "group": group_name,
        "created_at": now_iso(),
        "operation": operation,
        "source": source,
        "members": member_state,
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot_id


def update_group_state(group: dict[str, Any]) -> None:
    current = build_member_state(group)
    operation_at = now_iso()
    merge_metadata_urls(group, current)
    if not group.get("created_at"):
        group["created_at"] = infer_group_created_at(current) or operation_at
    group["last_state"] = current
    group["updated_at"] = operation_at
    update_version_history(group, current, operation_at)


def infer_group_created_at(current: dict[str, dict[str, Any]]) -> str | None:
    return min_iso([info.get("git_first_commit_at") or info.get("content_updated_at") for info in current.values()])


def merge_metadata_urls(group: dict[str, Any], current: dict[str, dict[str, Any]]) -> None:
    skill_urls = group.setdefault("skill_urls", [])
    for info in current.values():
        for url in info.get("metadata_urls", []) or []:
            if url not in skill_urls:
                skill_urls.append(url)


def update_version_history(group: dict[str, Any], current: dict[str, dict[str, Any]], observed_at: str) -> None:
    history = group.setdefault("version_history", {})
    for role, info in current.items():
        version = info.get("version") or "unknown"
        digest = info.get("digest") or "unknown"
        inferred_created_at = info.get("git_first_commit_at") or info.get("content_updated_at") or observed_at
        inferred_updated_at = info.get("git_latest_commit_at") or info.get("content_updated_at") or observed_at
        version_entry = history.setdefault(version, {
            "version": version,
            "created_at": inferred_created_at,
            "updated_at": inferred_updated_at,
            "digests": {},
            "skill_urls": sorted(set(group.get("skill_urls", []))),
        })
        version_entry["skill_urls"] = sorted(set(version_entry.get("skill_urls", [])) | set(group.get("skill_urls", [])))
        if not version_entry.get("created_at"):
            version_entry["created_at"] = inferred_created_at
        version_entry["updated_at"] = max_iso([version_entry.get("updated_at"), inferred_updated_at]) or inferred_updated_at
        digests = version_entry.setdefault("digests", {})
        digest_entry = digests.setdefault(digest, {
            "digest": digest,
            "created_at": inferred_created_at,
            "updated_at": inferred_updated_at,
            "roles": [],
            "role_urls": {},
            "content_updated_at_by_role": {},
        })
        if not digest_entry.get("created_at"):
            digest_entry["created_at"] = inferred_created_at
        digest_entry["updated_at"] = max_iso([digest_entry.get("updated_at"), inferred_updated_at]) or inferred_updated_at
        roles = set(digest_entry.get("roles", []))
        roles.add(role)
        digest_entry["roles"] = sorted(roles)
        if info.get("url"):
            digest_entry.setdefault("role_urls", {})[role] = info.get("url")
        digest_entry.setdefault("content_updated_at_by_role", {})[role] = info.get("content_updated_at")


def apply_url_args(group: dict[str, Any], args: argparse.Namespace) -> None:
    for url in getattr(args, "skill_url", None) or []:
        if url not in group.setdefault("skill_urls", []):
            group["skill_urls"].append(url)
    for role in ROLE_FLAGS:
        role_url = getattr(args, f"{role}_url", None)
        if role_url:
            group.setdefault("role_urls", {})[role] = role_url


def command_link(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_or_create_group(registry, args.group)
    apply_url_args(group, args)

    for role in ROLE_FLAGS:
        path = resolve_path(getattr(args, role))
        if path:
            require_skill_dir(path, role)
            group["roles"][role] = path

    update_group_state(group)
    save_registry(state_dir, registry)
    print(json.dumps({"group": args.group, "created_at": group["created_at"], "updated_at": group["updated_at"], "roles": group["roles"], "role_urls": group.get("role_urls", {}), "skill_urls": group.get("skill_urls", []), "state_dir": str(state_dir)}, indent=2, sort_keys=True))
    return 0


def command_convert(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_or_create_group(registry, args.group)
    apply_url_args(group, args)

    source = require_skill_dir(str(Path(args.source_path).expanduser().resolve()), args.source_role)
    target = Path(args.target_path).expanduser().resolve()
    if source == target:
        raise SystemExit("source and target paths are the same")
    if is_relative_to(target, source):
        raise SystemExit("target path must not be inside the source skill directory")
    if args.source_role == args.target_role:
        raise SystemExit("source-role and target-role must be different")
    if target.exists() and target.is_file():
        raise SystemExit(f"target exists and is not a directory: {target}")
    if target.exists() and not is_empty_dir(target):
        require_skill_dir(str(target), args.target_role)

    group["roles"][args.source_role] = str(source)
    group["roles"][args.target_role] = str(target)
    if args.source_url:
        group.setdefault("role_urls", {})[args.source_role] = args.source_url
    if args.target_url:
        group.setdefault("role_urls", {})[args.target_role] = args.target_url
    snapshot_id = None
    if target.exists() and not is_empty_dir(target):
        snapshot_id = create_snapshot(state_dir, args.group, group, "convert", args.source_role)
        group.setdefault("snapshots", []).append(snapshot_id)

    target.parent.mkdir(parents=True, exist_ok=True)
    copy_skill_tree(source, target)
    operation_at = now_iso()
    group["last_convert"] = {
        "at": operation_at,
        "source": args.source_role,
        "target": args.target_role,
        "source_path": str(source),
        "target_path": str(target),
        "snapshot": snapshot_id,
        "source_url": group.get("role_urls", {}).get(args.source_role),
        "target_url": group.get("role_urls", {}).get(args.target_role),
    }
    update_group_state(group)
    save_registry(state_dir, registry)
    print(json.dumps({"group": args.group, "source": args.source_role, "target": args.target_role, "target_path": str(target), "snapshot": snapshot_id, "updated_at": operation_at, "skill_urls": group.get("skill_urls", []), "source_url": group.get("role_urls", {}).get(args.source_role), "target_url": group.get("role_urls", {}).get(args.target_role)}, indent=2, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_group(registry, args.group)
    current = build_member_state(group)
    digests = {info["digest"] for info in current.values()}
    result = {
        "group": args.group,
        "clean": len(digests) <= 1,
        "members": current,
        "role_urls": group.get("role_urls", {}),
        "skill_urls": group.get("skill_urls", []),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["clean"] else 2


def command_versions(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_group(registry, args.group)
    result = {
        "group": args.group,
        "created_at": group.get("created_at"),
        "updated_at": group.get("updated_at"),
        "role_urls": group.get("role_urls", {}),
        "skill_urls": group.get("skill_urls", []),
        "version_history": group.get("version_history", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_sync(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_group(registry, args.group)
    current = build_member_state(group)
    if len(current) < 2:
        raise SystemExit("sync requires at least two existing linked roles")

    source_role = args.source or choose_source(group, current)
    if source_role not in current:
        raise SystemExit(f"source role is not linked or does not exist: {source_role}")

    source_path = Path(str(current[source_role]["path"]))
    snapshot_id = create_snapshot(state_dir, args.group, group, "sync", source_role)
    snapshot_dir = state_dir / "snapshots" / args.group / snapshot_id
    differences_by_role = {}
    for role, info in current.items():
        if role == source_role:
            continue
        differences_by_role[role] = summarize_diff(compare_skill_dirs(snapshot_dir / role, source_path))
        copy_skill_tree(source_path, Path(str(info["path"])))

    updated_roles = sorted(r for r in current if r != source_role)
    operation_at = now_iso()
    group.setdefault("snapshots", []).append(snapshot_id)
    group["last_sync"] = {
        "at": operation_at,
        "source": source_role,
        "snapshot": snapshot_id,
        "updated_roles": updated_roles,
        "differences_by_role": differences_by_role,
    }
    update_group_state(group)
    save_registry(state_dir, registry)
    print(json.dumps({"group": args.group, "source": source_role, "snapshot": snapshot_id, "updated_roles": updated_roles, "updated_at": operation_at, "differences_by_role": differences_by_role}, indent=2, sort_keys=True))
    return 0


def command_diff(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_group(registry, args.group)
    from_path = resolve_diff_path(state_dir, args.group, group, args.role, args.from_path, args.from_snapshot, False)
    to_path = resolve_diff_path(state_dir, args.group, group, args.role, args.to_path, args.to_snapshot, args.to_current)
    result = compare_skill_dirs(from_path, to_path)
    result.update({
        "group": args.group,
        "role": args.role,
        "from": str(from_path),
        "to": str(to_path),
    })
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_snapshots(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    snapshots_dir = state_dir / "snapshots" / args.group
    snapshots = []
    if snapshots_dir.exists():
        for snapshot_dir in sorted(p for p in snapshots_dir.iterdir() if p.is_dir()):
            manifest_path = snapshot_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            snapshots.append({"snapshot": snapshot_dir.name, "manifest": manifest})
    print(json.dumps({"group": args.group, "snapshots": snapshots}, indent=2, sort_keys=True))
    return 0


def command_rollback(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    group = get_group(registry, args.group)
    snapshot_dir = state_dir / "snapshots" / args.group / args.snapshot
    if not snapshot_dir.is_dir():
        raise SystemExit(f"snapshot not found: {args.snapshot}")

    pre_rollback = create_snapshot(state_dir, args.group, group, "pre-rollback", None)
    roles = args.roles or sorted(existing_members(group))
    restored = []
    for role in roles:
        source = snapshot_dir / role
        if not source.is_dir():
            raise SystemExit(f"snapshot does not contain role: {role}")
        target = Path(group["roles"][role])
        copy_skill_tree(source, target)
        restored.append(role)

    operation_at = now_iso()
    group.setdefault("snapshots", []).append(pre_rollback)
    group["last_rollback"] = {
        "at": operation_at,
        "snapshot": args.snapshot,
        "pre_rollback_snapshot": pre_rollback,
        "restored_roles": restored,
    }
    update_group_state(group)
    save_registry(state_dir, registry)
    print(json.dumps({"group": args.group, "rolled_back_to": args.snapshot, "pre_rollback_snapshot": pre_rollback, "restored_roles": restored, "updated_at": operation_at}, indent=2, sort_keys=True))
    return 0


def get_group(registry: dict[str, Any], group_name: str) -> dict[str, Any]:
    try:
        return registry["groups"][group_name]
    except KeyError:
        raise SystemExit(f"group not found: {group_name}") from None


def resolve_diff_path(state_dir: Path, group_name: str, group: dict[str, Any], role: str, explicit_path: str | None, snapshot: str | None, current: bool) -> Path:
    selected = [bool(explicit_path), bool(snapshot), current]
    if sum(1 for item in selected if item) != 1:
        raise SystemExit("choose exactly one diff source: explicit path, snapshot, or current")
    if explicit_path:
        return require_skill_dir(str(Path(explicit_path).expanduser().resolve()), "diff-path")
    if snapshot:
        path = state_dir / "snapshots" / group_name / snapshot / role
        if not path.is_dir():
            raise SystemExit(f"snapshot role not found: {snapshot}/{role}")
        return require_skill_dir(str(path), role)
    if role not in group.get("roles", {}):
        raise SystemExit(f"role is not linked: {role}")
    return require_skill_dir(group["roles"][role], role)


def compare_skill_dirs(from_dir: Path, to_dir: Path) -> dict[str, Any]:
    from_files = {p.relative_to(from_dir).as_posix(): p for p in iter_skill_files(from_dir)}
    to_files = {p.relative_to(to_dir).as_posix(): p for p in iter_skill_files(to_dir)}
    added = sorted(set(to_files) - set(from_files))
    removed = sorted(set(from_files) - set(to_files))
    common = sorted(set(from_files) & set(to_files))
    modified_text = []
    modified_binary = []

    for relative in common:
        from_bytes = from_files[relative].read_bytes()
        to_bytes = to_files[relative].read_bytes()
        if from_bytes == to_bytes:
            continue
        try:
            from_text = from_bytes.decode("utf-8").splitlines()
            to_text = to_bytes.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            modified_binary.append(relative)
            continue
        diff_lines = list(difflib.unified_diff(from_text, to_text, fromfile=f"from/{relative}", tofile=f"to/{relative}", lineterm=""))
        modified_text.append({"path": relative, "diff": diff_lines[:400], "truncated": len(diff_lines) > 400})

    return {
        "changed": bool(added or removed or modified_text or modified_binary),
        "added_files": added,
        "removed_files": removed,
        "modified_text_files": modified_text,
        "modified_binary_files": modified_binary,
    }


def summarize_diff(diff: dict[str, Any]) -> dict[str, Any]:
    return {
        "changed": diff["changed"],
        "added_files": diff["added_files"],
        "removed_files": diff["removed_files"],
        "modified_text_files": [item["path"] for item in diff["modified_text_files"]],
        "modified_binary_files": diff["modified_binary_files"],
    }


def choose_source(group: dict[str, Any], current: dict[str, dict[str, str | None]]) -> str:
    previous = group.get("last_state", {})
    changed = []
    for role, info in current.items():
        previous_digest = previous.get(role, {}).get("digest")
        if previous_digest and previous_digest != info["digest"]:
            changed.append(role)

    if len(changed) == 1:
        return changed[0]
    if len(changed) > 1:
        raise SystemExit(f"conflict: multiple roles changed since last link/sync: {', '.join(sorted(changed))}; rerun with --source")

    newest_role = max(current, key=lambda role: Path(str(current[role]["path"])).stat().st_mtime)
    return newest_role


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize linked Agent Skill directory copies.")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, help="Registry and snapshot directory. Default: .skill-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    link = subparsers.add_parser("link", help="Create or update a linked skill group.")
    link.add_argument("group")
    link.add_argument("--skill-url", action="append", help="Canonical repository, documentation, registry, or source URL for the logical skill. Can be repeated.")
    for role in ROLE_FLAGS:
        link.add_argument(f"--{role}", help=f"Path for the {role} role.")
        link.add_argument(f"--{role}-url", help=f"Repository, source, or documentation URL for the {role} role.")
    link.set_defaults(func=command_link)

    convert = subparsers.add_parser("convert", help="Copy a skill path to a target path and link both roles.")
    convert.add_argument("group")
    convert.add_argument("--source-path", required=True)
    convert.add_argument("--target-path", required=True)
    convert.add_argument("--source-role", default="external")
    convert.add_argument("--target-role", default="repo")
    convert.add_argument("--source-url", help="Repository, source, or documentation URL for the source role.")
    convert.add_argument("--target-url", help="Repository, source, or documentation URL for the target role.")
    convert.add_argument("--skill-url", action="append", help="Canonical repository, documentation, registry, or source URL for the logical skill. Can be repeated.")
    convert.set_defaults(func=command_convert)

    status = subparsers.add_parser("status", help="Show linked role digests and versions.")
    status.add_argument("group")
    status.set_defaults(func=command_status)

    versions = subparsers.add_parser("versions", help="Show recorded versions and update times.")
    versions.add_argument("group")
    versions.set_defaults(func=command_versions)

    sync = subparsers.add_parser("sync", help="Copy one linked role to the other linked roles.")
    sync.add_argument("group")
    sync.add_argument("--source", help="Role to use as source. Required when conflicts exist.")
    sync.set_defaults(func=command_sync)

    snapshots = subparsers.add_parser("snapshots", help="List snapshots for a group.")
    snapshots.add_argument("group")
    snapshots.set_defaults(func=command_snapshots)

    diff = subparsers.add_parser("diff", help="Show file differences between snapshots, current roles, or explicit paths.")
    diff.add_argument("group")
    diff.add_argument("--role", default="repo")
    diff.add_argument("--from-path")
    diff.add_argument("--to-path")
    diff.add_argument("--from-snapshot")
    diff.add_argument("--to-snapshot")
    diff.add_argument("--to-current", action="store_true")
    diff.set_defaults(func=command_diff)

    rollback = subparsers.add_parser("rollback", help="Restore linked roles from a snapshot.")
    rollback.add_argument("group")
    rollback.add_argument("--snapshot", required=True)
    rollback.add_argument("--roles", nargs="+", help="Optional subset of roles to restore.")
    rollback.set_defaults(func=command_rollback)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
