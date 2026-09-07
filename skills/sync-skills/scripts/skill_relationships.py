#!/usr/bin/env python3
"""Build and safely persist the machine-local Skill relationship report."""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AGENT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
IGNORED_DIRECTORY_NAMES = {".git", "agent-builds", "dist", "node_modules", "__pycache__", ".pytest_cache"}
IGNORED_FILE_NAMES = {".DS_Store"}
BYTECODE_SUFFIXES = {".pyc", ".pyo"}


class RelationshipError(Exception):
    """Raised when a relationship report cannot be generated safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compact_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_assignment(value: str, label: str) -> tuple[str, Path]:
    key, separator, raw_path = value.partition("=")
    if not separator or not key or not raw_path:
        raise RelationshipError(f"{label} must use NAME=/absolute/path syntax: {value!r}")
    if not AGENT_ID.fullmatch(key):
        raise RelationshipError(f"{label} name must be lowercase hyphenated: {key!r}")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise RelationshipError(f"{label} path must be absolute: {raw_path!r}")
    return key, path.absolute()


def path_is_within(child: Path, parent: Path) -> bool:
    child_real = child.expanduser().resolve()
    parent_real = parent.expanduser().resolve()
    try:
        child_real.relative_to(parent_real)
        return True
    except ValueError:
        pass
    for candidate in child_real.parents:
        try:
            if candidate.exists() and parent_real.exists() and os.path.samefile(candidate, parent_real):
                return True
        except OSError:
            continue
    return False


def same_location(first: Path, second: Path) -> bool:
    first_real = first.expanduser().resolve()
    second_real = second.expanduser().resolve()
    if first_real == second_real:
        return True
    try:
        return first_real.exists() and second_real.exists() and os.path.samefile(first_real, second_real)
    except OSError:
        return False


def normalized_absolute(path: Path) -> str:
    value = path.expanduser().absolute()
    return str(PurePosixPath(value))


def should_ignore(path: Path, root: Path, portable: bool) -> bool:
    relative = path.relative_to(root)
    ignored_dirs = IGNORED_DIRECTORY_NAMES if portable else IGNORED_DIRECTORY_NAMES - {"agent-builds"}
    if any(part in ignored_dirs for part in relative.parts[:-1]):
        return True
    if portable and relative.parts and relative.parts[0] == "agent-builds":
        return True
    return path.name in IGNORED_FILE_NAMES or path.suffix in BYTECODE_SUFFIXES


def digest_tree(root: Path, *, portable: bool = False) -> str:
    if not root.is_dir():
        raise RelationshipError(f"cannot digest a missing directory: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RelationshipError(f"Skill tree contains a symbolic link: {path}")
        if not path.is_file() or should_ignore(path, root, portable):
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def match_yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def read_skill(path: Path, *, portable: bool = False) -> dict[str, Any]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file():
        raise RelationshipError(f"missing SKILL.md: {path}")
    before = skill_file.stat()
    try:
        text = skill_file.read_text(encoding="utf-8").lstrip("\ufeff")
    except (OSError, UnicodeError) as error:
        raise RelationshipError(f"cannot read {skill_file}: {error}") from error
    frontmatter_match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if frontmatter_match is None:
        raise RelationshipError(f"invalid frontmatter: {skill_file}")
    frontmatter = frontmatter_match.group(1)
    name = match_yaml_scalar(frontmatter, "name")
    sync_id = match_yaml_scalar(frontmatter, "sync_id")
    version = match_yaml_scalar(frontmatter, "version")
    if not name:
        raise RelationshipError(f"missing name: {skill_file}")
    if version is None or SEMVER.fullmatch(version) is None:
        raise RelationshipError(f"missing or invalid metadata.version: {skill_file}")
    if sync_id is not None and AGENT_ID.fullmatch(sync_id) is None:
        raise RelationshipError(f"invalid metadata.sync_id: {skill_file}")
    digest = digest_tree(path, portable=portable)
    after = skill_file.stat()
    unstable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    return {
        "name": name,
        "sync_id": sync_id,
        "core_version": version,
        "digest": digest,
        "path": normalized_absolute(path),
        "unstable": unstable,
    }


def validate_resolver(resolver: Any, label: str, environment: dict[str, str]) -> tuple[str, str | None, str]:
    if not isinstance(resolver, dict):
        raise RelationshipError(f"{label} must be an object")
    resolver_type = resolver.get("type")
    if resolver_type == "home-relative":
        if set(resolver) != {"type", "path"}:
            raise RelationshipError(f"{label} has unsupported fields")
        raw_path = resolver.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise RelationshipError(f"{label}.path must be a non-empty string")
        relative = PurePosixPath(raw_path)
        if relative.is_absolute() or ".." in relative.parts or raw_path == ".":
            raise RelationshipError(f"{label}.path must be a safe home-relative path")
        home = environment.get("HOME")
        if not home or not Path(home).is_absolute():
            raise RelationshipError("HOME must be an absolute path to resolve adapter roots")
        result = Path(home).joinpath(*relative.parts).absolute()
        return f"home-relative:{raw_path}", normalized_absolute(result), "resolved" if result.exists() else "missing-root"
    if resolver_type == "env":
        if not set(resolver).issubset({"type", "name", "required"}):
            raise RelationshipError(f"{label} has unsupported fields")
        name = resolver.get("name")
        if not isinstance(name, str) or ENV_NAME.fullmatch(name) is None:
            raise RelationshipError(f"{label}.name must be an uppercase environment variable")
        required = resolver.get("required", False)
        if not isinstance(required, bool):
            raise RelationshipError(f"{label}.required must be boolean")
        raw_path = environment.get(name)
        if not raw_path:
            if required:
                raise RelationshipError(f"required adapter root environment variable is not set: {name}")
            return f"env:{name}", None, "unresolved-root"
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            raise RelationshipError(f"adapter root environment variable must be absolute: {name}")
        return f"env:{name}", normalized_absolute(path), "resolved" if path.exists() else "missing-root"
    raise RelationshipError(f"{label}.type must be 'home-relative' or 'env'")


def load_adapters(
    project_root: Path,
    local_root_args: Iterable[str],
    environment: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    environment = dict(os.environ if environment is None else environment)
    override_values: dict[str, list[Path]] = {}
    for value in local_root_args:
        agent_id, path = parse_assignment(value, "--local-root")
        override_values.setdefault(agent_id, []).append(path)
    adapters: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    platforms_root = project_root / "platforms"
    if not platforms_root.is_dir():
        raise RelationshipError(f"current project does not contain platforms/: {project_root}")
    for manifest_path in sorted(platforms_root.glob("*/adapter.json")):
        agent_id = manifest_path.parent.name
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise RelationshipError("manifest must contain an object")
            if value.get("schema_version") != 1:
                raise RelationshipError("schema_version must equal 1")
            if value.get("id") != agent_id or AGENT_ID.fullmatch(agent_id) is None:
                raise RelationshipError("id must be lowercase hyphenated and match the directory")
            adapter_version = value.get("version")
            artifact_version = value.get("artifact_version")
            if not isinstance(adapter_version, str) or SEMVER.fullmatch(adapter_version) is None:
                raise RelationshipError("version must be SemVer")
            if not isinstance(artifact_version, str) or SEMVER.fullmatch(artifact_version) is None:
                raise RelationshipError("artifact_version must be SemVer")
            configured_roots = value.get("local_skill_roots")
            if not isinstance(configured_roots, list) or not configured_roots:
                raise RelationshipError("local_skill_roots must be a non-empty array")
            roots: list[dict[str, Any]] = []
            for index, resolver in enumerate(configured_roots):
                resolver_name, resolved, status = validate_resolver(
                    resolver,
                    f"{manifest_path}: local_skill_roots[{index}]",
                    environment,
                )
                root: dict[str, Any] = {"resolver": resolver_name, "status": status, "source": "adapter"}
                if resolved is not None:
                    root["path"] = resolved
                roots.append(root)
            for override in override_values.pop(agent_id, []):
                roots.append({
                    "resolver": f"override:{normalized_absolute(override)}",
                    "path": normalized_absolute(override),
                    "status": "resolved" if override.exists() else "missing-root",
                    "source": "override",
                })
            roots.sort(key=lambda item: item.get("path", item["resolver"]))
            adapters.append({
                "id": agent_id,
                "adapter_version": adapter_version,
                "artifact_version": artifact_version,
                "adapter_manifest": normalized_absolute(manifest_path),
                "skills_path": value.get("skills_path"),
                "local_skill_roots": roots,
            })
        except (OSError, json.JSONDecodeError, RelationshipError) as error:
            issues.append({
                "severity": "error",
                "code": "agent-build-invalid",
                "message": f"Invalid adapter {manifest_path}: {error}",
                "agent_id": agent_id if AGENT_ID.fullmatch(agent_id) else None,
                "path": normalized_absolute(manifest_path),
            })
    if override_values:
        unknown = ", ".join(sorted(override_values))
        raise RelationshipError(f"--local-root references unsupported Builder(s): {unknown}")
    adapters.sort(key=lambda item: item["id"])
    if not adapters:
        details = "; ".join(issue["message"] for issue in issues)
        raise RelationshipError(
            "no valid AI Agent Builder adapters were discovered"
            + (f": {details}" if details else "")
        )
    return adapters, [{key: value for key, value in issue.items() if value is not None} for issue in issues]


def deduplicate_roots(adapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    for adapter in adapters:
        for configured in adapter["local_skill_roots"]:
            path = configured.get("path")
            existing = None
            if path:
                for candidate in roots:
                    if candidate.get("path") and same_location(Path(path), Path(candidate["path"])):
                        existing = candidate
                        break
            if existing is None:
                existing = dict(configured)
                existing["agent_ids"] = []
                roots.append(existing)
            existing["agent_ids"].append(adapter["id"])
            existing["agent_ids"] = sorted(set(existing["agent_ids"]))
    roots.sort(key=lambda item: item.get("path", item["resolver"]))
    return roots


def scan_root(
    root: Path,
    *,
    portable: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    copies: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if not root.exists():
        return copies, issues
    if root.is_symlink() or not root.is_dir():
        raise RelationshipError(f"inventory root must be a regular directory: {root}")
    for candidate in sorted(root.iterdir(), key=lambda path: path.name):
        if candidate.name.startswith(".") or not candidate.is_dir():
            continue
        try:
            copy = read_skill(candidate, portable=portable)
            copies.append(copy)
        except RelationshipError as error:
            issues.append({
                "severity": "warning",
                "code": "missing-sync-id" if (candidate / "SKILL.md").is_file() else "missing-copy",
                "message": str(error),
                "path": normalized_absolute(candidate),
            })
    return copies, issues


def read_builds(
    project_root: Path,
    adapters: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_sync_id: dict[str, dict[str, dict[str, Any]]] = {}
    issues: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for adapter in adapters:
        agent_id = adapter["id"]
        output = project_root / "dist" / agent_id
        manifest_path = output / ".agent-build.json"
        if not output.exists():
            sources.append({"kind": "agent-build", "id": agent_id, "path": normalized_absolute(output), "status": "missing-root", "skill_count": 0})
            continue
        try:
            if output.is_symlink() or not output.is_dir():
                raise RelationshipError("build output must be a regular directory")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
                raise RelationshipError("a trusted build requires .agent-build.json schema_version 2")
            if manifest.get("platform") != agent_id:
                raise RelationshipError("manifest platform does not match the Builder")
            if manifest.get("adapter_version") != adapter["adapter_version"]:
                raise RelationshipError("manifest adapter_version is stale")
            if manifest.get("artifact_version") != adapter["artifact_version"]:
                raise RelationshipError("manifest artifact_version is stale")
            skills = manifest.get("skills")
            if not isinstance(skills, list):
                raise RelationshipError("manifest skills must be an array")
            seen_ids: set[str] = set()
            for index, record in enumerate(skills):
                if not isinstance(record, dict):
                    raise RelationshipError(f"skills[{index}] must be an object")
                required = {"name", "sync_id", "core_version", "portable_digest", "output_digest", "path"}
                if not required.issubset(record):
                    raise RelationshipError(f"skills[{index}] is missing v2 identity fields")
                sync_id = record["sync_id"]
                if not isinstance(sync_id, str) or AGENT_ID.fullmatch(sync_id) is None or sync_id in seen_ids:
                    raise RelationshipError(f"skills[{index}] has an invalid or duplicate sync_id")
                seen_ids.add(sync_id)
                relative = PurePosixPath(record["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise RelationshipError(f"skills[{index}].path is unsafe")
                skill_path = output.joinpath(*relative.parts)
                if not path_is_within(skill_path, output) or skill_path.is_symlink() or not skill_path.is_dir():
                    raise RelationshipError(f"skills[{index}].path does not identify a safe build directory")
                actual_digest = digest_tree(skill_path)
                if actual_digest != record["output_digest"]:
                    raise RelationshipError(f"skills[{index}] output digest does not match the build directory")
                built_metadata = read_skill(skill_path)
                if built_metadata.get("name") != record["name"]:
                    raise RelationshipError(f"skills[{index}] name does not match the build directory")
                if built_metadata.get("sync_id") != sync_id:
                    raise RelationshipError(f"skills[{index}] sync_id does not match the built SKILL.md")
                if built_metadata.get("core_version") != record["core_version"]:
                    raise RelationshipError(f"skills[{index}] core_version does not match the built SKILL.md")
                by_sync_id.setdefault(sync_id, {})[agent_id] = {
                    "present": True,
                    "sync_id": sync_id,
                    "agent_id": agent_id,
                    "build_id": f"build:{agent_id}",
                    "core_version": record["core_version"],
                    "portable_digest": record["portable_digest"],
                    "adapter_version": adapter["adapter_version"],
                    "artifact_version": adapter["artifact_version"],
                    "output_digest": record["output_digest"],
                    "path": normalized_absolute(skill_path),
                    "manifest_path": normalized_absolute(manifest_path),
                }
            sources.append({"kind": "agent-build", "id": agent_id, "path": normalized_absolute(output), "status": "scanned", "skill_count": len(skills)})
        except (OSError, json.JSONDecodeError, RelationshipError, TypeError) as error:
            sources.append({"kind": "agent-build", "id": agent_id, "path": normalized_absolute(output), "status": "invalid", "skill_count": 0})
            issues.append({
                "severity": "error",
                "code": "agent-build-invalid",
                "message": f"Invalid {agent_id} build: {error}",
                "agent_id": agent_id,
                "path": normalized_absolute(manifest_path),
            })
    return by_sync_id, issues, sources


def registry_location_view(registry: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    locations: dict[str, list[dict[str, Any]]] = {}
    groups = registry.get("groups", {})
    if not isinstance(groups, dict):
        raise RelationshipError("registry groups must be an object")
    for key, group in groups.items():
        if not isinstance(group, dict):
            raise RelationshipError(f"registry group {key!r} must be an object")
        sync_id = str(group.get("sync_id") or key)
        group_locations: list[dict[str, Any]] = []
        configured = group.get("locations", {})
        if configured:
            if not isinstance(configured, dict):
                raise RelationshipError(f"registry group {key!r} locations must be an object")
            for location_id, location in configured.items():
                if not isinstance(location, dict) or not location.get("path"):
                    raise RelationshipError(f"registry location {key!r}/{location_id!r} is invalid")
                item = dict(location)
                item["location_id"] = location_id
                item["path"] = normalized_absolute(Path(str(item["path"])))
                group_locations.append(item)
        roles = group.get("roles", {})
        if roles:
            if not isinstance(roles, dict):
                raise RelationshipError(f"registry group {key!r} roles must be an object")
            for role, raw_path in roles.items():
                if any(item["path"] == normalized_absolute(Path(str(raw_path))) for item in group_locations):
                    continue
                kind = "local" if role == "local" else "project" if role in {"repo", "project"} else "external"
                item = {
                    "location_id": "repo:current" if role == "repo" else f"legacy:{role}",
                    "kind": kind,
                    "path": normalized_absolute(Path(str(raw_path))),
                }
                if role == "repo":
                    item["project_id"] = "current"
                elif role == "project":
                    item["project_id"] = "legacy-project"
                elif kind == "external":
                    item["source_id"] = f"legacy-{role}"
                group_locations.append(item)
        locations[sync_id] = sorted(group_locations, key=lambda item: item["location_id"])
    projects = registry.get("projects", {})
    if not isinstance(projects, dict):
        raise RelationshipError("registry projects must be an object")
    return locations, projects


def location_path_index(
    registry_locations: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, tuple[str, dict[str, Any]]], list[tuple[str, str, str]]]:
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    conflicts: list[tuple[str, str, str]] = []
    for sync_id, locations in registry_locations.items():
        for location in locations:
            path = str(Path(location["path"]).resolve())
            previous = index.get(path)
            if previous and previous[0] != sync_id:
                conflicts.append((path, previous[0], sync_id))
                continue
            index[path] = (sync_id, location)
    return index, conflicts


def agent_for_path(path: Path, roots: list[dict[str, Any]]) -> list[str]:
    agents: set[str] = set()
    for root in roots:
        raw_root = root.get("path")
        if raw_root and path_is_within(path, Path(raw_root)):
            agents.update(root["agent_ids"])
    return sorted(agents)


def add_issue(issues: list[dict[str, Any]], severity: str, code: str, message: str, **identity: Any) -> None:
    issue = {"severity": severity, "code": code, "message": message}
    issue.update({key: value for key, value in identity.items() if value is not None})
    issues.append(issue)


def build_report(
    project_root: Path,
    state_dir: Path,
    registry: dict[str, Any],
    *,
    local_root_args: Iterable[str] = (),
    project_args: Iterable[str] = (),
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    state_dir = state_dir.expanduser().resolve()
    skills_root = project_root / "skills"
    if not skills_root.is_dir():
        raise RelationshipError(f"current project does not contain skills/: {project_root}")
    project_id = project_root.name
    adapters, issues = load_adapters(project_root, local_root_args, environment)
    builder_ids = [adapter["id"] for adapter in adapters]
    roots = deduplicate_roots(adapters)
    registry_locations, registered_projects = registry_location_view(registry)
    registry_index, registry_conflicts = location_path_index(registry_locations)
    for path, first_sync_id, second_sync_id in registry_conflicts:
        add_issue(
            issues,
            "error",
            "identity-conflict",
            f"One physical path is registered to both {first_sync_id!r} and {second_sync_id!r}",
            path=path,
        )

    portable_copies, portable_issues = scan_root(skills_root, portable=True)
    issues.extend(portable_issues)
    scan_sources: list[dict[str, Any]] = [
        {"kind": "current-project", "id": project_id, "path": normalized_absolute(skills_root), "status": "scanned", "skill_count": len(portable_copies)}
    ]
    for adapter in adapters:
        scan_sources.append({"kind": "adapter", "id": adapter["id"], "path": adapter["adapter_manifest"], "status": "scanned", "skill_count": 0})

    local_copies: list[dict[str, Any]] = []
    for root in roots:
        source: dict[str, Any] = {
            "kind": "local",
            "id": "+".join(root["agent_ids"]),
            "status": "scanned" if root["status"] == "resolved" else root["status"],
            "skill_count": 0,
        }
        if root.get("path"):
            source["path"] = root["path"]
        else:
            source["resolver"] = root["resolver"]
        if root["status"] == "resolved":
            copies, root_issues = scan_root(Path(root["path"]), portable=False)
            for copy in copies:
                copy["agent_ids"] = list(root["agent_ids"])
                local_copies.append(copy)
            issues.extend(root_issues)
            source["skill_count"] = len(copies)
        scan_sources.append(source)
    deduplicated_local: dict[str, dict[str, Any]] = {}
    for copy in local_copies:
        identity = str(Path(copy["path"]).resolve())
        existing = deduplicated_local.get(identity)
        if existing is None:
            deduplicated_local[identity] = copy
        else:
            existing["agent_ids"] = sorted(set(existing["agent_ids"]) | set(copy["agent_ids"]))
    local_copies = sorted(deduplicated_local.values(), key=lambda item: item["path"])

    related_inputs: dict[tuple[str, str], Path] = {}
    for related_id, value in registered_projects.items():
        if not isinstance(value, dict):
            raise RelationshipError(f"registry project {related_id!r} must be an object")
        roots_value = value.get("skill_roots", [])
        if not isinstance(roots_value, list):
            raise RelationshipError(f"registry project {related_id!r} skill_roots must be an array")
        for raw_path in roots_value:
            root = Path(str(raw_path)).expanduser().absolute()
            related_inputs[(related_id, normalized_absolute(root))] = root
    for value in project_args:
        related_id, related_root = parse_assignment(value, "--project")
        related_inputs[(related_id, normalized_absolute(related_root))] = related_root

    related_copies: list[dict[str, Any]] = []
    related_ids: set[str] = set()
    for (related_id, _), related_root in sorted(related_inputs.items()):
        related_ids.add(related_id)
        status = "scanned" if related_root.exists() else "missing-root"
        copies: list[dict[str, Any]] = []
        if related_root.exists():
            copies, root_issues = scan_root(related_root, portable=True)
            issues.extend(root_issues)
            for copy in copies:
                copy["project_id"] = related_id
                related_copies.append(copy)
        scan_sources.append({"kind": "related-project", "id": related_id, "path": normalized_absolute(related_root), "status": status, "skill_count": len(copies)})
    for related_id in sorted(related_ids):
        project_config = registered_projects.get(related_id, {})
        adapter_root_value = project_config.get("adapter_root") if isinstance(project_config, dict) else None
        if not adapter_root_value:
            scan_sources.append({
                "kind": "adapter",
                "id": related_id,
                "resolver": f"registry:projects.{related_id}.adapter_root",
                "status": "unresolved-root",
                "skill_count": 0,
            })
            continue
        adapter_root = Path(str(adapter_root_value)).expanduser().absolute()
        if not adapter_root.is_dir():
            scan_sources.append({"kind": "adapter", "id": related_id, "path": normalized_absolute(adapter_root), "status": "missing-root", "skill_count": 0})
            continue
        manifests = sorted(adapter_root.glob("*/adapter.json"))
        scan_sources.append({"kind": "adapter", "id": related_id, "path": normalized_absolute(adapter_root), "status": "scanned", "skill_count": len(manifests)})

    builds, build_issues, build_sources = read_builds(project_root, adapters)
    issues.extend(build_issues)
    scan_sources.extend(build_sources)

    logical: dict[str, dict[str, Any]] = {}
    for copy in portable_copies:
        sync_id = copy.get("sync_id")
        if not sync_id:
            add_issue(issues, "warning", "missing-sync-id", "Current-project Skill is missing metadata.sync_id", path=copy["path"])
            continue
        if sync_id in logical:
            add_issue(issues, "error", "identity-conflict", "Duplicate metadata.sync_id in current project", sync_id=sync_id, path=copy["path"])
            logical[sync_id].setdefault("forced_statuses", set()).add("identity-conflict")
            continue
        logical[sync_id] = {"portable_copy": copy, "registry_group": registry.get("groups", {}).get(sync_id), "locations": [], "local": []}

    for registry_key, group in registry.get("groups", {}).items():
        if not isinstance(group, dict):
            continue
        sync_id = str(group.get("sync_id") or registry_key)
        current_location = next(
            (
                location
                for location in registry_locations.get(sync_id, [])
                if location["location_id"] == "repo:current" or (
                    location.get("kind") == "project" and location.get("project_id") in {project_id, "current"}
                )
            ),
            None,
        )
        if sync_id not in logical and current_location:
            logical[sync_id] = {"portable_copy": None, "expected_portable_path": current_location["path"], "registry_group": group, "locations": [], "local": []}
        elif sync_id in logical:
            logical[sync_id]["registry_group"] = group

    for copy in related_copies:
        sync_id = copy.get("sync_id")
        if not sync_id:
            add_issue(issues, "warning", "missing-sync-id", "Related-project Skill is missing metadata.sync_id", path=copy["path"])
            continue
        if sync_id in logical:
            logical[sync_id]["locations"].append({
                "location_id": f"project:{copy['project_id']}",
                "kind": "project",
                "path": copy["path"],
                "project_id": copy["project_id"],
                "core_version": copy["core_version"],
                "digest": copy["digest"],
            })

    for sync_id, entry in logical.items():
        existing_paths = {location["path"] for location in entry["locations"]}
        for location in registry_locations.get(sync_id, []):
            if location.get("kind") == "local" or location["location_id"] == "repo:current":
                continue
            path = Path(location["path"])
            if normalized_absolute(path) in existing_paths:
                continue
            if not path.exists():
                entry.setdefault("forced_statuses", set()).add("missing-copy")
                add_issue(issues, "warning", "missing-copy", "Registered Skill location does not exist", sync_id=sync_id, path=normalized_absolute(path))
                continue
            try:
                copy = read_skill(path, portable=True)
            except RelationshipError as error:
                entry.setdefault("forced_statuses", set()).add("missing-copy")
                add_issue(issues, "warning", "missing-copy", str(error), sync_id=sync_id, path=normalized_absolute(path))
                continue
            kind = location.get("kind", "external")
            record = {
                "location_id": location["location_id"],
                "kind": kind,
                "path": copy["path"],
                "core_version": copy["core_version"],
                "digest": copy["digest"],
            }
            if kind == "project":
                record["project_id"] = location.get("project_id") or "legacy-project"
            else:
                record["source_id"] = location.get("source_id") or location["location_id"].replace(":", "-")
            entry["locations"].append(record)

    assigned_local_paths: set[str] = set()
    unlinked: list[dict[str, Any]] = []
    for copy in local_copies:
        real_path = str(Path(copy["path"]).resolve())
        registry_match = registry_index.get(real_path)
        sync_id = copy.get("sync_id")
        if sync_id not in logical and registry_match and registry_match[0] in logical:
            sync_id = registry_match[0]
        if sync_id in logical:
            entry = logical[sync_id]
            for agent_id in copy["agent_ids"]:
                entry["local"].append({**copy, "agent_id": agent_id})
            assigned_local_paths.add(copy["path"])
        else:
            statuses = {"unlinked-local"}
            if not sync_id:
                statuses.add("missing-sync-id")
            unlinked.append({
                "name": copy["name"],
                **({"sync_id": sync_id} if sync_id else {}),
                "agent_ids": copy["agent_ids"],
                "path": copy["path"],
                "core_version": copy["core_version"],
                "digest": copy["digest"],
                "statuses": sorted(statuses),
            })

    for sync_id, entry in logical.items():
        for location in registry_locations.get(sync_id, []):
            if location.get("kind") != "local":
                continue
            path = Path(location["path"])
            if normalized_absolute(path) in assigned_local_paths:
                continue
            if not path.exists():
                entry.setdefault("forced_statuses", set()).add("missing-copy")
                add_issue(issues, "warning", "missing-copy", "Registered local Skill does not exist", sync_id=sync_id, path=normalized_absolute(path))

    report_skills: list[dict[str, Any]] = []
    for sync_id, entry in sorted(logical.items()):
        portable = entry.get("portable_copy")
        group = entry.get("registry_group") or {}
        statuses: set[str] = set(entry.get("forced_statuses", set()))
        portable_record: dict[str, Any]
        if portable:
            portable_record = {
                "present": True,
                "project_id": project_id,
                "path": portable["path"],
                "core_version": portable["core_version"],
                "digest": portable["digest"],
            }
            if portable["unstable"]:
                statuses.add("scan-unstable")
        else:
            portable_record = {
                "present": False,
                "project_id": project_id,
                "path": entry["expected_portable_path"],
            }
            statuses.add("missing-copy")

        build_cells: dict[str, dict[str, Any]] = {}
        present_builds: list[dict[str, Any]] = []
        for agent_id in builder_ids:
            cell = builds.get(sync_id, {}).get(agent_id)
            if cell is None:
                cell = {"present": False, "sync_id": sync_id, "agent_id": agent_id}
            else:
                present_builds.append(cell)
                if portable and cell["portable_digest"] != portable["digest"]:
                    statuses.add("agent-build-stale")
                if portable and cell["core_version"] != portable["core_version"]:
                    statuses.add("agent-build-stale")
            build_cells[agent_id] = cell
        if not present_builds:
            statuses.add("agent-build-missing")
        elif len(present_builds) < len(builder_ids):
            statuses.add("agent-build-partial")
        if len({build["core_version"] for build in present_builds}) > 1:
            statuses.add("agent-version-diverged")

        local_installs: list[dict[str, Any]] = []
        for local in sorted(entry["local"], key=lambda item: (item["agent_id"], item["path"])):
            agent_id = local["agent_id"]
            install_statuses: set[str] = set()
            identity_status = "verified"
            if local.get("sync_id") != sync_id:
                if local.get("sync_id"):
                    statuses.add("identity-conflict")
                    install_statuses.add("identity-conflict")
                else:
                    statuses.add("missing-sync-id")
                    install_statuses.add("missing-sync-id")
                    identity_status = "registered-incomplete"
            build = build_cells.get(agent_id)
            if not build or not build["present"]:
                statuses.add("agent-build-missing" if not present_builds else "agent-build-partial")
            elif build["output_digest"] != local["digest"]:
                statuses.add("agent-install-diverged")
                install_statuses.add("agent-install-diverged")
            if local["unstable"]:
                statuses.add("scan-unstable")
                install_statuses.add("scan-unstable")
            if not install_statuses:
                install_statuses.add("synced")
            local_installs.append({
                "agent_id": agent_id,
                "path": local["path"],
                **({"sync_id": local["sync_id"]} if local.get("sync_id") else {}),
                "core_version": local["core_version"],
                "digest": local["digest"],
                "derived_from": f"build:{agent_id}",
                "identity_status": identity_status,
                "statuses": sorted(install_statuses),
            })

        if not local_installs:
            statuses.add("project-only")
        if portable:
            for location in entry["locations"]:
                if location["core_version"] != portable["core_version"]:
                    statuses.add("version-diverged")
                elif location["digest"] != portable["digest"]:
                    statuses.add("content-diverged")
        if not statuses and len(present_builds) == len(builder_ids):
            statuses.add("synced")
        elif statuses == {"project-only"} and len(present_builds) == len(builder_ids):
            pass

        report_skills.append({
            "sync_id": sync_id,
            "name": str(group.get("name") or (portable and portable["name"]) or sync_id),
            "aliases": sorted(set(group.get("aliases", []))),
            "portable": portable_record,
            "locations": sorted(entry["locations"], key=lambda item: item["location_id"]),
            "agent_builds": build_cells,
            "local_installs": local_installs,
            "statuses": sorted(statuses),
        })

    conflicting_ids = {sync_id for _, first, second in registry_conflicts for sync_id in (first, second)}
    for skill in report_skills:
        if skill["sync_id"] in conflicting_ids:
            skill["statuses"] = sorted(set(skill["statuses"]) | {"identity-conflict"})

    copies_by_name: dict[str, set[str]] = {}
    for copy in [*portable_copies, *local_copies, *related_copies]:
        if copy.get("sync_id"):
            copies_by_name.setdefault(copy["name"], set()).add(copy["sync_id"])
    for name, sync_ids in sorted(copies_by_name.items()):
        if len(sync_ids) > 1:
            add_issue(
                issues,
                "warning",
                "identity-conflict",
                f"Copies named {name!r} declare different sync IDs and were not linked: {', '.join(sorted(sync_ids))}",
            )

    for issue in build_issues:
        agent_id = issue.get("agent_id")
        for skill in report_skills:
            if agent_id in skill["agent_builds"]:
                skill["statuses"] = sorted(set(skill["statuses"]) | {"agent-build-invalid"})

    for skill in report_skills:
        if "missing-sync-id" in skill["statuses"]:
            add_issue(
                issues,
                "warning",
                "missing-sync-id",
                "Registered local Agent install has incomplete identity; snapshot and reinstall from its trusted same-Agent build",
                sync_id=skill["sync_id"],
            )
        if "agent-install-diverged" in skill["statuses"]:
            add_issue(issues, "warning", "agent-install-diverged", "Local Agent install differs from its trusted same-Agent build", sync_id=skill["sync_id"])

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda item: (
        severity_rank[item["severity"]],
        item["code"],
        item.get("sync_id", ""),
        item.get("agent_id", ""),
        item.get("path", ""),
    ))
    scan_sources.sort(key=lambda item: (item["kind"], item["id"], item.get("path", item.get("resolver", ""))))
    unlinked.sort(key=lambda item: (item["path"], tuple(item["agent_ids"])))

    local_paths = {
        install["path"]
        for skill in report_skills
        for install in skill["local_installs"]
    } | {item["path"] for item in unlinked}
    related_projects = {
        location["project_id"]
        for skill in report_skills
        for location in skill["locations"]
        if location["kind"] == "project"
    }
    summary = {
        "local_skill_count": len(local_paths),
        "current_project_skill_count": sum(1 for skill in report_skills if skill["portable"]["present"]),
        "related_project_count": len(related_projects),
        "build_complete_count": sum(
            1 for skill in report_skills
            if all(cell["present"] for cell in skill["agent_builds"].values())
            and "agent-build-stale" not in skill["statuses"]
            and "agent-version-diverged" not in skill["statuses"]
        ),
        "build_partial_count": sum("agent-build-partial" in skill["statuses"] for skill in report_skills),
        "build_missing_count": sum("agent-build-missing" in skill["statuses"] and not any(cell["present"] for cell in skill["agent_builds"].values()) for skill in report_skills),
        "agent_version_diverged_count": sum("agent-version-diverged" in skill["statuses"] for skill in report_skills),
        "agent_install_diverged_count": sum(
            1
            for skill in report_skills
            for install in skill["local_installs"]
            if "agent-install-diverged" in install["statuses"]
        ),
        "issue_count": len(issues),
    }
    public_adapters = [
        {key: value for key, value in adapter.items() if key != "skills_path"}
        for adapter in adapters
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "input_fingerprint": "0" * 64,
        "project": {"id": project_id, "root": normalized_absolute(project_root), "skills_root": normalized_absolute(skills_root)},
        "agent_builders": public_adapters,
        "summary": summary,
        "skills": report_skills,
        "unlinked_local_skills": unlinked,
        "issues": issues,
        "scan_sources": scan_sources,
    }
    fingerprint_input = dict(report)
    fingerprint_input.pop("generated_at")
    fingerprint_input.pop("input_fingerprint")
    report["input_fingerprint"] = hashlib.sha256(compact_json(fingerprint_input)).hexdigest()
    validate_contract(report)
    return report


def validate_contract(report: dict[str, Any]) -> None:
    validator_path = REPOSITORY_ROOT / "scripts" / "validate_skill_relationship_report.py"
    spec = importlib.util.spec_from_file_location("skill_relationship_report_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RelationshipError(f"cannot load report validator: {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate_report(report, REPOSITORY_ROOT / "schemas" / "skill-relationships.schema.json")
    except module.ContractError as error:
        raise RelationshipError(f"generated report violates its contract: {error}") from error


def markdown_report(report: dict[str, Any]) -> str:
    builders = report["agent_builders"]
    builder_headers = [builder["id"] for builder in builders]
    lines = [
        "# 本机 Skill 关系表",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 当前项目：`{report['project']['id']}`",
        f"- 项目路径：`{report['project']['root']}`",
        "- 项目支持的 AI Agent Builders：" + ", ".join(
            f"`{builder['id']}`（adapter `{builder['adapter_version']}`，artifact `{builder['artifact_version']}`）"
            for builder in builders
        ),
        "- 汇总：" + "；".join(f"{key}={value}" for key, value in report["summary"].items()),
        "",
        "## Skill 关系与 Agent 构建覆盖",
        "",
    ]
    headers = ["Sync ID", "当前项目 / 本机 / 其他项目", "Portable core", *builder_headers, "汇总状态"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for skill in report["skills"]:
        portable = skill["portable"]
        locations = [portable["path"]]
        locations.extend(install["path"] for install in skill["local_installs"])
        locations.extend(location["path"] for location in skill["locations"])
        cells = [f"`{skill['sync_id']}`", "<br>".join(f"`{path}`" for path in locations), portable.get("core_version", "—")]
        installs = {install["agent_id"]: install for install in skill["local_installs"]}
        for builder in builders:
            agent_id = builder["id"]
            build = skill["agent_builds"][agent_id]
            if not build["present"]:
                cells.append("—")
                continue
            cell = f"core `{build['core_version']}` · adapter `{build['adapter_version']}` · artifact `{build['artifact_version']}`"
            install = installs.get(agent_id)
            if install:
                cell += "<br>local " + ", ".join(f"`{status}`" for status in install["statuses"])
            cells.append(cell)
        cells.append(", ".join(f"`{status}`" for status in skill["statuses"]))
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in cells) + " |")

    lines.extend(["", "## 跨项目明细", ""])
    any_related = False
    for skill in report["skills"]:
        if not skill["locations"]:
            continue
        any_related = True
        lines.append(f"### `{skill['sync_id']}`")
        lines.append("")
        for location in skill["locations"]:
            owner = location.get("project_id") or location.get("source_id")
            lines.append(f"- {location['kind']} `{owner}`：`{location['path']}`，core `{location['core_version']}`。")
        lines.append("")
    if not any_related:
        lines.append("- 无。")

    lines.extend(["", "## 未关联的本机 Skill", ""])
    if report["unlinked_local_skills"]:
        for item in report["unlinked_local_skills"]:
            lines.append(f"- `{item['name']}`：`{item['path']}`；Builder `{', '.join(item['agent_ids'])}`；状态 `{', '.join(item['statuses'])}`。")
    else:
        lines.append("- 无。")

    lines.extend(["", "## 问题与警告", ""])
    if report["issues"]:
        for issue in report["issues"]:
            identity = issue.get("sync_id") or issue.get("agent_id") or issue.get("path", "")
            lines.append(f"- {issue['severity'].title()} — `{issue['code']}` {identity}：{issue['message']}")
    else:
        lines.append("- 无。")

    lines.extend(["", "## 扫描来源", ""])
    for source in report["scan_sources"]:
        location = source.get("path") or source.get("resolver")
        lines.append(f"- {source['kind']} `{source['id']}`：`{location}`，{source['status']}，{source['skill_count']} 个 Skill。")
    return "\n".join(lines).rstrip() + "\n"


def validate_output_directory(output_dir: Path, state_dir: Path, project_root: Path) -> Path:
    output = output_dir.expanduser().absolute()
    forbidden = [project_root, state_dir / "registry.json", state_dir / "snapshots"]
    for target in forbidden:
        if same_location(output, target) or path_is_within(output, target) or path_is_within(target, output):
            if target == state_dir / "snapshots" and output == state_dir / "reports":
                continue
            raise RelationshipError(f"report output conflicts with protected path: {target}")
    current = output
    existing_ancestors: list[Path] = []
    while not current.exists() and current.parent != current:
        current = current.parent
    while current != current.parent:
        existing_ancestors.append(current)
        current = current.parent
    for ancestor in existing_ancestors:
        if ancestor.is_symlink():
            raise RelationshipError(f"report output ancestor must not be a symlink: {ancestor}")
    if output.exists() and (output.is_symlink() or not output.is_dir()):
        raise RelationshipError(f"report output must be a regular directory: {output}")
    return output


def validate_report_target(path: Path) -> None:
    if path.is_symlink():
        raise RelationshipError(f"refusing to replace a report symlink: {path}")
    if path.exists():
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise RelationshipError(f"report target must be a regular file: {path}")
        if path.stat().st_uid != os.getuid():
            raise RelationshipError(f"report target must be owned by the current user: {path}")


def atomic_write_report_set(contents: dict[Path, str]) -> None:
    for path in contents:
        validate_report_target(path)
    parent = next(iter(contents)).parent
    staging_root = Path(tempfile.mkdtemp(prefix=".relationship-report-", dir=parent))
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for index, (target, content) in enumerate(contents.items()):
            staged_path = staging_root / f"staged-{index}"
            staged_path.write_text(content, encoding="utf-8")
            os.chmod(staged_path, 0o600)
            with staged_path.open("rb") as stream:
                os.fsync(stream.fileno())
            if staged_path.read_text(encoding="utf-8") != content:
                raise RelationshipError(f"staged report failed verification: {target.name}")
            staged[target] = staged_path
            if target.exists():
                backup = staging_root / f"backup-{index}"
                shutil.copy2(target, backup)
                os.chmod(backup, 0o600)
                backups[target] = backup
        try:
            for target, staged_path in staged.items():
                os.replace(staged_path, target)
                os.chmod(target, 0o600)
                replaced.append(target)
        except BaseException:
            for target in reversed(replaced):
                backup = backups.get(target)
                if backup and backup.exists():
                    os.replace(backup, target)
                elif target.exists():
                    target.unlink()
            raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def write_reports(
    report: dict[str, Any],
    *,
    output_dir: Path,
    state_dir: Path,
    project_root: Path,
    output_format: str,
) -> dict[str, str]:
    output = validate_output_directory(output_dir, state_dir, project_root)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    json_path = output / "skill-relationships.json"
    markdown_path = output / "skill-relationships.md"
    selected_contents: dict[Path, str] = {}
    if output_format in {"json", "both"}:
        selected_contents[json_path] = canonical_json(report)
    if output_format in {"markdown", "both"}:
        selected_contents[markdown_path] = markdown_report(report)
    for path in selected_contents:
        validate_report_target(path)
    lock_path = state_dir / ".relationships.lock"
    state_dir.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RelationshipError("another relationship report refresh is already running") from error
        atomic_write_report_set(selected_contents)
        written: dict[str, str] = {}
        if json_path in selected_contents:
            written["json"] = normalized_absolute(json_path)
        if markdown_path in selected_contents:
            written["markdown"] = normalized_absolute(markdown_path)
        directory_descriptor = os.open(output, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return written


def generate_and_write(
    *,
    project_root: Path,
    state_dir: Path,
    registry: dict[str, Any],
    local_root_args: Iterable[str] = (),
    project_args: Iterable[str] = (),
    output_dir: Path | None = None,
    output_format: str = "both",
    environment: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    if output_format not in {"json", "markdown", "both"}:
        raise RelationshipError(f"unknown report format: {output_format}")
    report = build_report(
        project_root,
        state_dir,
        registry,
        local_root_args=local_root_args,
        project_args=project_args,
        environment=environment,
    )
    paths = write_reports(
        report,
        output_dir=output_dir or state_dir / "reports",
        state_dir=state_dir,
        project_root=project_root,
        output_format=output_format,
    )
    return report, paths
