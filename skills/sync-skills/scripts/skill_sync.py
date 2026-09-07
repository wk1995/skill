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
SYNC_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
    source_real = source.resolve()
    target_real = target.resolve()
    if source_real == target_real:
        raise SystemExit(f"refusing to copy a skill onto itself: {source_real}")
    if is_relative_to(target_real, source_real):
        raise SystemExit(f"refusing to copy a skill into its own subtree: {target_real} is inside {source_real}")
    if is_relative_to(source_real, target_real):
        raise SystemExit(f"refusing to copy a skill from inside its target: {source_real} is inside {target_real}")
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


def normalized_role_paths(roles: dict[str, str]) -> dict[str, str]:
    """Resolve every registered role path for stable equality checks."""
    return {
        role: str(Path(path).expanduser().resolve())
        for role, path in roles.items()
        if path
    }


def role_path_issues(roles: dict[str, str]) -> list[str]:
    """Return same-path and nesting conflicts across all registered roles."""
    normalized = normalized_role_paths(roles)
    items = sorted(normalized.items())
    issues: list[str] = []
    for index, (role_a, path_a) in enumerate(items):
        for role_b, path_b in items[index + 1:]:
            if path_a == path_b:
                issues.append(
                    "roles resolve to the same path: "
                    f"{role_a}, {role_b} -> {path_a}"
                )
            elif is_relative_to(Path(path_b), Path(path_a)):
                issues.append(
                    f"role {role_b} is inside role {role_a}: {path_b} is inside {path_a}"
                )
            elif is_relative_to(Path(path_a), Path(path_b)):
                issues.append(
                    f"role {role_a} is inside role {role_b}: {path_a} is inside {path_b}"
                )
    return issues


def validate_role_paths(roles: dict[str, str]) -> dict[str, str]:
    """Return normalized roles or refuse to persist an unsafe registry."""
    normalized = normalized_role_paths(roles)
    issues = role_path_issues(normalized)
    if issues:
        raise SystemExit(
            "refusing unsafe role paths: " + "; ".join(issues)
            + ". A symlinked copy is already identical to its target, so link only real copies."
        )
    return normalized


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


def git_current_branch(path: Path) -> str | None:
    if not shutil.which("git"):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def git_default_branch(path: Path) -> str | None:
    if not shutil.which("git"):
        return None
    commands = [
        ["git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "origin/HEAD"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue
        branch = result.stdout.strip()
        if branch.startswith("origin/"):
            return branch.removeprefix("origin/")
        if branch:
            return branch
    return None


def read_skill_metadata(path: Path) -> dict[str, Any]:
    skill_md = path / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8").lstrip("\ufeff")
    frontmatter = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            frontmatter = text[3:end]
    name = match_yaml_scalar(frontmatter, "name")
    sync_id = match_yaml_scalar(frontmatter, "sync_id")
    version = match_yaml_scalar(frontmatter, "version")
    urls = parse_metadata_url_values(frontmatter)
    return {"name": name, "sync_id": sync_id, "version": version, "urls": urls}


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


def validate_sync_id(sync_id: str) -> str:
    if not SYNC_ID.fullmatch(sync_id):
        raise SystemExit(f"invalid sync ID: {sync_id!r}; use lowercase letters, digits, and hyphens")
    return sync_id


def group_id(key: str, group: dict[str, Any]) -> str:
    return str(group.get("sync_id") or key)


def group_name(key: str, group: dict[str, Any]) -> str:
    return str(group.get("name") or key)


def find_group(registry: dict[str, Any], reference: str) -> tuple[str, dict[str, Any]] | None:
    groups = registry.setdefault("groups", {})
    if reference in groups:
        return reference, groups[reference]
    for key, group in groups.items():
        aliases = set(group.get("aliases", []))
        if reference in aliases or reference == group_id(key, group) or reference == group_name(key, group):
            return key, group
    return None


def get_or_create_group(
    registry: dict[str, Any], sync_id: str, name: str | None = None
) -> tuple[str, dict[str, Any]]:
    groups = registry.setdefault("groups", {})
    match = find_group(registry, sync_id)
    if match:
        key, group = match
    else:
        sync_id = validate_sync_id(sync_id)
        key = sync_id
        groups[key] = {
            "sync_id": sync_id,
            "name": name or sync_id,
            "roles": {},
            "role_urls": {},
            "snapshots": [],
            "skill_urls": [],
            "version_history": {},
        }
        group = groups[key]
    group.setdefault("sync_id", group_id(key, group))
    group.setdefault("name", name or group_name(key, group))
    group.setdefault("aliases", [])
    group.setdefault("roles", {})
    group.setdefault("role_urls", {})
    group.setdefault("snapshots", [])
    group.setdefault("skill_urls", [])
    group.setdefault("version_history", {})
    return key, group


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
            "sync_id": metadata["sync_id"],
            "version": metadata["version"],
        }
    return state


def validate_group_members(group: dict[str, Any], current: dict[str, dict[str, Any]]) -> None:
    declared = group.get("sync_id")
    member_ids = {info.get("sync_id") for info in current.values() if info.get("sync_id")}
    if len(member_ids) > 1:
        raise SystemExit("linked Skill copies declare different metadata.sync_id values")
    if declared and member_ids and member_ids != {declared}:
        actual = next(iter(member_ids))
        raise SystemExit(f"linked Skill metadata.sync_id {actual!r} does not match group {declared!r}")


def read_sync_metadata(path: Path, role: str) -> dict[str, Any]:
    metadata = read_skill_metadata(path)
    sync_id = metadata.get("sync_id")
    if not sync_id:
        raise SystemExit(f"{role}: SKILL.md must define metadata.sync_id for new sync groups")
    metadata["sync_id"] = validate_sync_id(str(sync_id))
    return metadata


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
    validate_group_members(group, current)
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
    paths = {
        role: resolve_path(getattr(args, role))
        for role in ROLE_FLAGS
        if getattr(args, role)
    }
    existing = find_group(registry, args.group)
    legacy_group = bool(existing and "sync_id" not in existing[1])
    if existing:
        key, group = get_or_create_group(registry, args.group, args.name)
    else:
        if not paths:
            raise SystemExit("new sync groups require at least one Skill path with metadata.sync_id")
        source_metadata = [read_sync_metadata(Path(path), role) for role, path in paths.items()]
        source_ids = {str(metadata["sync_id"]) for metadata in source_metadata}
        if len(source_ids) != 1:
            raise SystemExit("linked Skill copies declare different metadata.sync_id values")
        key = next(iter(source_ids))
        if args.group != key:
            raise SystemExit(
                f"new sync groups must use metadata.sync_id {key!r} as the group ID, not {args.group!r}"
            )
        group = get_or_create_group(registry, key, args.name or source_metadata[0].get("name"))[1]
    apply_url_args(group, args)

    expected_id = group_id(key, group)
    resolved_roles: dict[str, str] = {}
    for role in ROLE_FLAGS:
        path = resolve_path(getattr(args, role))
        if path:
            require_skill_dir(path, role)
            resolved_roles[role] = path

    candidate_roles = dict(group.get("roles", {}))
    candidate_roles.update(resolved_roles)
    for role, path in resolved_roles.items():
        skill_dir = require_skill_dir(path, role)
        metadata = read_skill_metadata(skill_dir)
        if metadata.get("sync_id") and str(metadata["sync_id"]) != expected_id:
            raise SystemExit(
                f"{role}: metadata.sync_id {metadata['sync_id']!r} does not match group {expected_id!r}"
            )
        if not metadata.get("sync_id") and not legacy_group:
            read_sync_metadata(skill_dir, role)
    group["roles"] = validate_role_paths(candidate_roles)

    group["sync_id"] = expected_id
    if args.name:
        previous_name = group_name(key, group)
        if previous_name != args.name:
            aliases = set(group.get("aliases", []))
            aliases.add(previous_name)
            aliases.discard(args.name)
            group["aliases"] = sorted(alias for alias in aliases if alias)
        group["name"] = args.name

    update_group_state(group)
    save_registry(state_dir, registry)
    print(json.dumps({"group": key, "name": group_name(key, group), "sync_id": expected_id, "created_at": group["created_at"], "updated_at": group["updated_at"], "roles": group["roles"], "role_urls": group.get("role_urls", {}), "skill_urls": group.get("skill_urls", []), "state_dir": str(state_dir)}, indent=2, sort_keys=True))
    return 0


def command_convert(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    source = require_skill_dir(str(Path(args.source_path).expanduser().resolve()), args.source_role)
    source_metadata = read_skill_metadata(source)
    existing = find_group(registry, args.group)
    legacy_group = bool(existing and "sync_id" not in existing[1])
    source_sync_id = source_metadata.get("sync_id")
    if source_sync_id:
        source_metadata["sync_id"] = validate_sync_id(str(source_sync_id))
    elif not legacy_group:
        read_sync_metadata(source, args.source_role)
    if existing:
        key, group = get_or_create_group(registry, args.group)
        expected_id = group_id(key, group)
        if source_sync_id and expected_id != source_metadata["sync_id"]:
            raise SystemExit(
                f"source metadata.sync_id {source_metadata['sync_id']!r} does not match group {expected_id!r}"
            )
    else:
        if not source_sync_id:
            read_sync_metadata(source, args.source_role)
        if args.group != source_metadata["sync_id"]:
            raise SystemExit(
                f"new sync groups must use metadata.sync_id {source_metadata['sync_id']!r} as the group ID, not {args.group!r}"
            )
        key, group = get_or_create_group(registry, args.group, source_metadata.get("name"))
        expected_id = group_id(key, group)
    apply_url_args(group, args)

    requested_name = getattr(args, "name", None) or source_metadata.get("name")
    if requested_name and requested_name != group_name(key, group):
        aliases = set(group.get("aliases", []))
        aliases.add(group_name(key, group))
        aliases.discard(str(requested_name))
        group["aliases"] = sorted(alias for alias in aliases if alias)
        group["name"] = str(requested_name)

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

    candidate_roles = dict(group.get("roles", {}))
    candidate_roles[args.source_role] = str(source)
    candidate_roles[args.target_role] = str(target)
    group["roles"] = validate_role_paths(candidate_roles)
    if args.source_url:
        group.setdefault("role_urls", {})[args.source_role] = args.source_url
    if args.target_url:
        group.setdefault("role_urls", {})[args.target_role] = args.target_url
    snapshot_id = None
    if target.exists() and not is_empty_dir(target):
        snapshot_id = create_snapshot(state_dir, key, group, "convert", args.source_role)
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
    print(json.dumps({"group": key, "name": group_name(key, group), "sync_id": expected_id, "source": args.source_role, "target": args.target_role, "target_path": str(target), "snapshot": snapshot_id, "updated_at": operation_at, "skill_urls": group.get("skill_urls", []), "source_url": group.get("role_urls", {}).get(args.source_role), "target_url": group.get("role_urls", {}).get(args.target_role)}, indent=2, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    key, group = get_group(registry, args.group)
    path_issues = role_path_issues(group.get("roles", {}))
    current = build_member_state(group)
    validate_group_members(group, current)
    digests = {info["digest"] for info in current.values()}
    result = {
        "group": args.group,
        "sync_id": group_id(key, group),
        "name": group_name(key, group),
        "clean": len(digests) <= 1 and not path_issues,
        "members": current,
        "path_issues": path_issues,
        "role_urls": group.get("role_urls", {}),
        "skill_urls": group.get("skill_urls", []),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["clean"] else 2


def command_versions(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    key, group = get_group(registry, args.group)
    result = {
        "group": args.group,
        "sync_id": group_id(key, group),
        "name": group_name(key, group),
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
    key, group = get_group(registry, args.group)
    group["roles"] = validate_role_paths(group.get("roles", {}))
    current = build_member_state(group)
    validate_group_members(group, current)
    if len(current) < 2:
        raise SystemExit("sync requires at least two existing linked roles")

    source_role = args.source or choose_source(group, current)
    if source_role not in current:
        raise SystemExit(f"source role is not linked or does not exist: {source_role}")

    source_path = Path(str(current[source_role]["path"]))
    snapshot_id = create_snapshot(state_dir, key, group, "sync", source_role)
    snapshot_dir = state_dir / "snapshots" / key / snapshot_id
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
    print(json.dumps({"group": key, "name": group_name(key, group), "sync_id": group_id(key, group), "source": source_role, "snapshot": snapshot_id, "updated_roles": updated_roles, "updated_at": operation_at, "differences_by_role": differences_by_role}, indent=2, sort_keys=True))
    return 0


def command_diff(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    key, group = get_group(registry, args.group)
    from_path = resolve_diff_path(state_dir, key, group, args.role, args.from_path, args.from_snapshot, False)
    to_path = resolve_diff_path(state_dir, key, group, args.role, args.to_path, args.to_snapshot, args.to_current)
    result = compare_skill_dirs(from_path, to_path)
    result.update({
        "group": args.group,
        "sync_id": group_id(key, group),
        "role": args.role,
        "from": str(from_path),
        "to": str(to_path),
    })
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_snapshots(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    key, group = get_group(registry, args.group)
    snapshots_dir = state_dir / "snapshots" / key
    snapshots = []
    if snapshots_dir.exists():
        for snapshot_dir in sorted(p for p in snapshots_dir.iterdir() if p.is_dir()):
            manifest_path = snapshot_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            snapshots.append({"snapshot": snapshot_dir.name, "manifest": manifest})
    print(json.dumps({"group": key, "name": group_name(key, group), "sync_id": group_id(key, group), "snapshots": snapshots}, indent=2, sort_keys=True))
    return 0


def command_rollback(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    key, group = get_group(registry, args.group)
    group["roles"] = validate_role_paths(group.get("roles", {}))
    snapshot_dir = state_dir / "snapshots" / key / args.snapshot
    if not snapshot_dir.is_dir():
        raise SystemExit(f"snapshot not found: {args.snapshot}")

    pre_rollback = create_snapshot(state_dir, key, group, "pre-rollback", None)
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
    print(json.dumps({"group": key, "name": group_name(key, group), "sync_id": group_id(key, group), "rolled_back_to": args.snapshot, "pre_rollback_snapshot": pre_rollback, "restored_roles": restored, "updated_at": operation_at}, indent=2, sort_keys=True))
    return 0


def get_group(registry: dict[str, Any], reference: str) -> tuple[str, dict[str, Any]]:
    match = find_group(registry, reference)
    if not match:
        raise SystemExit(f"group not found: {reference}")
    key, group = match
    group.setdefault("sync_id", group_id(key, group))
    group.setdefault("name", group_name(key, group))
    group.setdefault("aliases", [])
    return key, group


def command_rename(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve()
    registry = load_registry(state_dir)
    match = find_group(registry, args.group)
    if not match:
        raise SystemExit(f"group not found: {args.group}")
    old_key, group = match
    # A missing sync_id marks a legacy name-keyed registry that may be
    # migrated. Once a stable ID exists, it is immutable; only the display
    # name may change.
    legacy_group = "sync_id" not in group
    group.setdefault("sync_id", group_id(old_key, group))
    group.setdefault("name", group_name(old_key, group))
    group.setdefault("aliases", [])
    new_id = validate_sync_id(args.to)
    groups = registry.setdefault("groups", {})
    if new_id != old_key and new_id in groups:
        raise SystemExit(f"sync ID already exists: {new_id}")
    if new_id == old_key and not args.name:
        raise SystemExit("rename requires a different --to sync ID or --name")

    old_name = group_name(old_key, group)
    old_id = group_id(old_key, group)
    if not legacy_group and new_id != old_id:
        raise SystemExit(
            f"cannot change immutable sync ID {old_id!r}; use --to {old_id!r} and optionally --name"
        )
    aliases = set(group.get("aliases", []))
    aliases.update({old_key, old_id, old_name})
    aliases.discard(new_id)
    group["sync_id"] = new_id
    group["name"] = args.name or old_name
    group["aliases"] = sorted(alias for alias in aliases if alias)

    if new_id != old_key:
        old_snapshots = state_dir / "snapshots" / old_key
        new_snapshots = state_dir / "snapshots" / new_id
        if old_snapshots.exists():
            if new_snapshots.exists():
                raise SystemExit(f"snapshot destination already exists: {new_snapshots}")
            new_snapshots.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_snapshots), str(new_snapshots))
        groups.pop(old_key, None)
        groups[new_id] = group

    save_registry(state_dir, registry)
    print(json.dumps({"from": old_key, "group": new_id, "name": group["name"], "sync_id": new_id, "aliases": group["aliases"], "state_dir": str(state_dir)}, indent=2, sort_keys=True))
    return 0


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
    version_source = choose_source_by_version_on_mainline(group, current)
    if version_source:
        return version_source

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


def choose_source_by_version_on_mainline(group: dict[str, Any], current: dict[str, dict[str, str | None]]) -> str | None:
    repo_path = group.get("roles", {}).get("repo")
    if not repo_path:
        return None
    repo_dir = Path(str(repo_path))
    current_branch = git_current_branch(repo_dir)
    default_branch = git_default_branch(repo_dir)
    if current_branch not in {"master", default_branch}:
        return None

    versions_by_role = {role: parse_version(info.get("version")) for role, info in current.items() if info.get("version")}
    comparable = {role: version for role, version in versions_by_role.items() if version is not None}
    if len(comparable) < 2 or len(set(comparable.values())) <= 1:
        return None

    highest = max(comparable.values())
    highest_roles = [role for role, version in comparable.items() if version == highest]
    if len(highest_roles) == 1:
        return highest_roles[0]

    highest_digests = {current[role]["digest"] for role in highest_roles}
    if len(highest_digests) == 1:
        return sorted(highest_roles)[0]
    raise SystemExit(
        "conflict: multiple roles have the highest version with different digests: "
        f"{', '.join(sorted(highest_roles))}; rerun with --source"
    )


def parse_version(value: str | None) -> tuple[int, int, int, int, tuple[tuple[int, int | str], ...]] | None:
    if not value:
        return None
    version = value.strip().split("+", 1)[0]
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-(.+))?", version)
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    prerelease_parts = tuple(split_version_suffix(prerelease or ""))
    release_rank = 1 if not prerelease_parts else 0
    return (int(major), int(minor or 0), int(patch or 0), release_rank, prerelease_parts)


def split_version_suffix(value: str) -> list[tuple[int, int | str]]:
    if not value:
        return []
    parts = value.split(".")
    if any(not part for part in parts):
        return []
    return [(0, int(part)) if part.isdigit() else (1, part) for part in parts]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize linked Agent Skill directory copies.")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, help="Registry and snapshot directory. Default: .skill-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    link = subparsers.add_parser("link", help="Create or update a linked skill group.")
    link.add_argument("group", help="Stable metadata.sync_id (legacy group names remain valid as aliases).")
    link.add_argument("--name", help="Current display/trigger name; it may change without changing the sync ID.")
    link.add_argument("--skill-url", action="append", help="Canonical repository, documentation, registry, or source URL for the logical skill. Can be repeated.")
    for role in ROLE_FLAGS:
        link.add_argument(f"--{role}", help=f"Path for the {role} role.")
        link.add_argument(f"--{role}-url", help=f"Repository, source, or documentation URL for the {role} role.")
    link.set_defaults(func=command_link)

    convert = subparsers.add_parser("convert", help="Copy a skill path to a target path and link both roles.")
    convert.add_argument("group", help="Stable metadata.sync_id (legacy group names remain valid as aliases).")
    convert.add_argument("--source-path", required=True)
    convert.add_argument("--target-path", required=True)
    convert.add_argument("--source-role", default="external")
    convert.add_argument("--target-role", default="repo")
    convert.add_argument("--source-url", help="Repository, source, or documentation URL for the source role.")
    convert.add_argument("--target-url", help="Repository, source, or documentation URL for the target role.")
    convert.add_argument("--name", help="Current display/trigger name; it may change without changing the sync ID.")
    convert.add_argument("--skill-url", action="append", help="Canonical repository, documentation, registry, or source URL for the logical skill. Can be repeated.")
    convert.set_defaults(func=command_convert)

    rename = subparsers.add_parser(
        "rename",
        help="Migrate a legacy group or rename a Skill without changing an existing stable sync ID.",
    )
    rename.add_argument("group", help="Existing sync ID, Skill name, or registered alias.")
    rename.add_argument(
        "--to",
        required=True,
        help="Stable sync ID to assign during legacy migration; must remain unchanged for existing groups.",
    )
    rename.add_argument("--name", help="Optional new display/trigger name.")
    rename.set_defaults(func=command_rename)

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
