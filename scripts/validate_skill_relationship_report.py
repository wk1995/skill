#!/usr/bin/env python3
"""Validate the structural and cross-record contract of a Skill relationship report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "skill-relationships.schema.json"
AGENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DATE_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class ContractError(Exception):
    """Raised when a report violates the relationship-report contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def schema_statuses(schema_path: Path) -> set[str]:
    schema = load_json(schema_path)
    try:
        values = schema["$defs"]["status"]["enum"]
    except (KeyError, TypeError) as error:
        raise ContractError(f"{schema_path} does not define $defs.status.enum") from error
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        raise ContractError(f"{schema_path} $defs.status.enum must be a non-empty string array")
    if values != sorted(set(values)):
        raise ContractError(f"{schema_path} $defs.status.enum must be unique and sorted")
    return set(values)


class Validator:
    def __init__(self, statuses: set[str]) -> None:
        self.allowed_statuses = statuses
        self.errors: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def object(self, value: Any, path: str, required: set[str], allowed: set[str]) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            self.error(path, "must be an object")
            return None
        missing = sorted(required - value.keys())
        extra = sorted(value.keys() - allowed)
        if missing:
            self.error(path, f"missing fields: {', '.join(missing)}")
        if extra:
            self.error(path, f"unknown fields: {', '.join(extra)}")
        return value

    def array(self, value: Any, path: str) -> list[Any] | None:
        if not isinstance(value, list):
            self.error(path, "must be an array")
            return None
        return value

    def string(self, value: Any, path: str, pattern: re.Pattern[str] | None = None) -> str | None:
        if not isinstance(value, str) or not value:
            self.error(path, "must be a non-empty string")
            return None
        if pattern is not None and pattern.fullmatch(value) is None:
            self.error(path, f"has invalid value {value!r}")
        return value

    def integer(self, value: Any, path: str) -> int | None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            self.error(path, "must be a non-negative integer")
            return None
        return value

    def absolute_path(self, value: Any, path: str) -> str | None:
        result = self.string(value, path)
        if result is None:
            return None
        candidate = PurePosixPath(result)
        if not candidate.is_absolute() or str(candidate) != result or "." in candidate.parts or ".." in candidate.parts:
            self.error(path, "must be a normalized absolute path")
        return result

    def digest(self, value: Any, path: str) -> str | None:
        return self.string(value, path, DIGEST_PATTERN)

    def semver(self, value: Any, path: str) -> str | None:
        return self.string(value, path, SEMVER_PATTERN)

    def statuses(self, value: Any, path: str) -> list[str]:
        items = self.array(value, path)
        if items is None:
            return []
        if not items:
            self.error(path, "must not be empty")
        if items != sorted(set(items)):
            self.error(path, "must be unique and sorted")
        for index, status in enumerate(items):
            if not isinstance(status, str) or status not in self.allowed_statuses:
                self.error(f"{path}[{index}]", f"unknown status {status!r}")
        return [item for item in items if isinstance(item, str)]

    def sorted_unique(self, values: list[Any], path: str, key: Any) -> None:
        try:
            keys = [key(value) for value in values]
        except (KeyError, TypeError):
            return
        if keys != sorted(set(keys)):
            self.error(path, "must be unique and sorted")


def validate_report(report: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA) -> None:
    validator = Validator(schema_statuses(schema_path))
    top_fields = {
        "schema_version",
        "generated_at",
        "input_fingerprint",
        "project",
        "agent_builders",
        "summary",
        "skills",
        "unlinked_local_skills",
        "issues",
        "scan_sources",
    }
    if validator.object(report, "$", top_fields, top_fields) is None:
        raise ContractError("\n".join(validator.errors))
    if report.get("schema_version") != 1:
        validator.error("$.schema_version", "must equal 1")
    validator.string(report.get("generated_at"), "$.generated_at", DATE_TIME_PATTERN)
    validator.digest(report.get("input_fingerprint"), "$.input_fingerprint")

    project_fields = {"id", "root", "skills_root"}
    project = validator.object(report.get("project"), "$.project", project_fields, project_fields)
    project_id: str | None = None
    if project is not None:
        project_id = validator.string(project.get("id"), "$.project.id")
        project_root = validator.absolute_path(project.get("root"), "$.project.root")
        skills_root = validator.absolute_path(project.get("skills_root"), "$.project.skills_root")
        if project_root and skills_root and not PurePosixPath(skills_root).is_relative_to(PurePosixPath(project_root)):
            validator.error("$.project.skills_root", "must be inside project.root")

    builders = validator.array(report.get("agent_builders"), "$.agent_builders") or []
    if not builders:
        validator.error("$.agent_builders", "must declare at least one supported Builder")
    validator.sorted_unique(builders, "$.agent_builders", lambda item: item["id"])
    builder_ids: list[str] = []
    builder_versions: dict[str, tuple[str, str]] = {}
    builder_fields = {"id", "adapter_version", "artifact_version", "adapter_manifest", "local_skill_roots"}
    root_fields = {"resolver", "path", "status", "source"}
    for index, value in enumerate(builders):
        path = f"$.agent_builders[{index}]"
        builder = validator.object(value, path, builder_fields, builder_fields)
        if builder is None:
            continue
        agent_id = validator.string(builder.get("id"), f"{path}.id", AGENT_ID_PATTERN)
        adapter_version = validator.semver(builder.get("adapter_version"), f"{path}.adapter_version")
        artifact_version = validator.semver(builder.get("artifact_version"), f"{path}.artifact_version")
        validator.absolute_path(builder.get("adapter_manifest"), f"{path}.adapter_manifest")
        roots = validator.array(builder.get("local_skill_roots"), f"{path}.local_skill_roots") or []
        if not roots:
            validator.error(f"{path}.local_skill_roots", "must declare at least one root resolver")
        validator.sorted_unique(
            roots,
            f"{path}.local_skill_roots",
            lambda item: item.get("path", item.get("resolver", "")),
        )
        for root_index, root_value in enumerate(roots):
            root_path = f"{path}.local_skill_roots[{root_index}]"
            root = validator.object(root_value, root_path, root_fields - {"path"}, root_fields)
            if root is None:
                continue
            validator.string(root.get("resolver"), f"{root_path}.resolver")
            if root.get("status") == "unresolved-root":
                if "path" in root:
                    validator.error(f"{root_path}.path", "must be absent when the resolver has no absolute result")
            else:
                validator.absolute_path(root.get("path"), f"{root_path}.path")
            if root.get("status") not in {"resolved", "missing-root", "unresolved-root"}:
                validator.error(f"{root_path}.status", "has an unknown root status")
            if root.get("source") not in {"adapter", "override"}:
                validator.error(f"{root_path}.source", "must be adapter or override")
        if agent_id:
            builder_ids.append(agent_id)
            if adapter_version and artifact_version:
                builder_versions[agent_id] = (adapter_version, artifact_version)

    summary_fields = {
        "local_skill_count",
        "current_project_skill_count",
        "related_project_count",
        "build_complete_count",
        "build_partial_count",
        "build_missing_count",
        "agent_version_diverged_count",
        "agent_install_diverged_count",
        "issue_count",
    }
    summary = validator.object(report.get("summary"), "$.summary", summary_fields, summary_fields)
    if summary is not None:
        for field in sorted(summary_fields):
            validator.integer(summary.get(field), f"$.summary.{field}")

    skills = validator.array(report.get("skills"), "$.skills") or []
    validator.sorted_unique(skills, "$.skills", lambda item: item["sync_id"])
    skill_fields = {"sync_id", "name", "aliases", "portable", "locations", "agent_builds", "local_installs", "statuses"}
    portable_fields = {"present", "project_id", "path", "core_version", "digest"}
    location_fields = {"location_id", "kind", "path", "project_id", "source_id", "core_version", "digest"}
    build_base_fields = {"present", "sync_id", "agent_id"}
    build_present_fields = build_base_fields | {
        "build_id",
        "core_version",
        "portable_digest",
        "adapter_version",
        "artifact_version",
        "output_digest",
        "path",
        "manifest_path",
    }
    install_fields = {"agent_id", "path", "sync_id", "core_version", "digest", "derived_from", "identity_status", "statuses"}
    related_projects: set[str] = set()
    local_paths: set[str] = set()
    current_project_skill_count = 0
    complete_count = 0
    partial_count = 0
    missing_count = 0
    agent_version_diverged_count = 0
    install_diverged_count = 0
    for index, value in enumerate(skills):
        path = f"$.skills[{index}]"
        skill = validator.object(value, path, skill_fields, skill_fields)
        if skill is None:
            continue
        sync_id = validator.string(skill.get("sync_id"), f"{path}.sync_id")
        validator.string(skill.get("name"), f"{path}.name")
        aliases = validator.array(skill.get("aliases"), f"{path}.aliases") or []
        validator.sorted_unique(aliases, f"{path}.aliases", lambda item: item)
        for alias_index, alias in enumerate(aliases):
            validator.string(alias, f"{path}.aliases[{alias_index}]")
        statuses = validator.statuses(skill.get("statuses"), f"{path}.statuses")
        if "synced" in statuses and len(statuses) != 1:
            validator.error(f"{path}.statuses", "synced cannot coexist with another status")

        portable_value = skill.get("portable")
        portable_present = portable_value.get("present") if isinstance(portable_value, dict) else None
        portable_required = portable_fields if portable_present is True else portable_fields - {"core_version", "digest"}
        portable_allowed = portable_fields if portable_present is True else portable_required
        portable = validator.object(portable_value, f"{path}.portable", portable_required, portable_allowed)
        portable_version: str | None = None
        portable_digest: str | None = None
        if portable is not None:
            if not isinstance(portable_present, bool):
                validator.error(f"{path}.portable.present", "must be a boolean")
            elif portable_present:
                current_project_skill_count += 1
            portable_project_id = validator.string(portable.get("project_id"), f"{path}.portable.project_id")
            if project_id and portable_project_id and portable_project_id != project_id:
                validator.error(f"{path}.portable.project_id", "must match $.project.id")
            validator.absolute_path(portable.get("path"), f"{path}.portable.path")
            if portable_present is True:
                portable_version = validator.semver(portable.get("core_version"), f"{path}.portable.core_version")
                portable_digest = validator.digest(portable.get("digest"), f"{path}.portable.digest")
            elif "missing-copy" not in statuses:
                validator.error(f"{path}.statuses", "must contain missing-copy when the registered portable source is absent")

        locations = validator.array(skill.get("locations"), f"{path}.locations") or []
        validator.sorted_unique(locations, f"{path}.locations", lambda item: item["location_id"])
        for location_index, location_value in enumerate(locations):
            location_path = f"{path}.locations[{location_index}]"
            location_kind = location_value.get("kind") if isinstance(location_value, dict) else None
            owner_field = "project_id" if location_kind == "project" else "source_id"
            location = validator.object(
                location_value,
                location_path,
                location_fields - {"project_id", "source_id"} | {owner_field},
                location_fields,
            )
            if location is None:
                continue
            validator.string(location.get("location_id"), f"{location_path}.location_id")
            if location.get("kind") not in {"project", "external"}:
                validator.error(f"{location_path}.kind", "must be project or external")
            validator.absolute_path(location.get("path"), f"{location_path}.path")
            owner_id = validator.string(location.get(owner_field), f"{location_path}.{owner_field}")
            alternate_owner = "source_id" if owner_field == "project_id" else "project_id"
            if alternate_owner in location:
                validator.error(f"{location_path}.{alternate_owner}", f"must be absent for {location_kind!r} locations")
            validator.semver(location.get("core_version"), f"{location_path}.core_version")
            validator.digest(location.get("digest"), f"{location_path}.digest")
            if location_kind == "project" and owner_id and owner_id != project_id:
                related_projects.add(owner_id)

        builds = validator.object(skill.get("agent_builds"), f"{path}.agent_builds", set(builder_ids), set(builder_ids))
        present_versions: list[str] = []
        present_count = 0
        build_stale = False
        if builds is not None:
            if list(builds) != sorted(builds):
                validator.error(f"{path}.agent_builds", "Builder keys must use canonical sort order")
            for agent_id in builder_ids:
                build_path = f"{path}.agent_builds.{agent_id}"
                build_value = builds.get(agent_id)
                if not isinstance(build_value, dict):
                    validator.error(build_path, "must be an object")
                    continue
                present = build_value.get("present")
                expected_fields = build_present_fields if present is True else build_base_fields
                build = validator.object(build_value, build_path, expected_fields, expected_fields)
                if build is None:
                    continue
                if not isinstance(present, bool):
                    validator.error(f"{build_path}.present", "must be a boolean")
                if build.get("agent_id") != agent_id:
                    validator.error(f"{build_path}.agent_id", "must match the agent_builds key")
                if sync_id and build.get("sync_id") != sync_id:
                    validator.error(f"{build_path}.sync_id", "must match the logical Skill sync_id")
                if present is not True:
                    continue
                present_count += 1
                build_id = validator.string(build.get("build_id"), f"{build_path}.build_id")
                if build_id != f"build:{agent_id}":
                    validator.error(f"{build_path}.build_id", "must equal build:<agent_id>")
                core_version = validator.semver(build.get("core_version"), f"{build_path}.core_version")
                if core_version:
                    present_versions.append(core_version)
                actual_portable_digest = validator.digest(build.get("portable_digest"), f"{build_path}.portable_digest")
                if portable_digest and actual_portable_digest and actual_portable_digest != portable_digest:
                    build_stale = True
                adapter_version = validator.semver(build.get("adapter_version"), f"{build_path}.adapter_version")
                artifact_version = validator.semver(build.get("artifact_version"), f"{build_path}.artifact_version")
                expected_versions = builder_versions.get(agent_id)
                if expected_versions and adapter_version and adapter_version != expected_versions[0]:
                    validator.error(f"{build_path}.adapter_version", "must match the declared Builder")
                if expected_versions and artifact_version and artifact_version != expected_versions[1]:
                    validator.error(f"{build_path}.artifact_version", "must match the declared Builder")
                validator.digest(build.get("output_digest"), f"{build_path}.output_digest")
                validator.absolute_path(build.get("path"), f"{build_path}.path")
                validator.absolute_path(build.get("manifest_path"), f"{build_path}.manifest_path")

        builder_count = len(builder_ids)
        if builder_count and present_count == 0:
            missing_count += 1
            if "agent-build-missing" not in statuses:
                validator.error(f"{path}.statuses", "must contain agent-build-missing when all Builder outputs are absent")
        elif present_count < builder_count:
            partial_count += 1
            if "agent-build-partial" not in statuses:
                validator.error(f"{path}.statuses", "must contain agent-build-partial for partial Builder coverage")
        elif builder_count and portable_version and all(version == portable_version for version in present_versions) and not build_stale:
            complete_count += 1
        if len(set(present_versions)) > 1:
            agent_version_diverged_count += 1
            if "agent-version-diverged" not in statuses:
                validator.error(f"{path}.statuses", "must contain agent-version-diverged for different Builder core versions")
        if portable_version and any(version != portable_version for version in present_versions):
            build_stale = True
        if build_stale:
            if "agent-build-stale" not in statuses:
                validator.error(f"{path}.statuses", "must contain agent-build-stale when a build source differs from portable")

        installs = validator.array(skill.get("local_installs"), f"{path}.local_installs") or []
        validator.sorted_unique(installs, f"{path}.local_installs", lambda item: (item["agent_id"], item["path"]))
        for install_index, install_value in enumerate(installs):
            install_path = f"{path}.local_installs[{install_index}]"
            install = validator.object(install_value, install_path, install_fields - {"sync_id"}, install_fields)
            if install is None:
                continue
            agent_id = validator.string(install.get("agent_id"), f"{install_path}.agent_id", AGENT_ID_PATTERN)
            if agent_id and agent_id not in builder_ids:
                validator.error(f"{install_path}.agent_id", "must reference a declared Builder")
            normalized_install_path = validator.absolute_path(install.get("path"), f"{install_path}.path")
            if normalized_install_path:
                local_paths.add(normalized_install_path)
            validator.semver(install.get("core_version"), f"{install_path}.core_version")
            install_digest = validator.digest(install.get("digest"), f"{install_path}.digest")
            derived_from = validator.string(install.get("derived_from"), f"{install_path}.derived_from")
            if agent_id and derived_from != f"build:{agent_id}":
                validator.error(f"{install_path}.derived_from", "must reference the build for the same Agent")
            install_statuses = validator.statuses(install.get("statuses"), f"{install_path}.statuses")
            install_sync_id = install.get("sync_id")
            if install_sync_id is None:
                if install.get("identity_status") != "registered-incomplete":
                    validator.error(f"{install_path}.identity_status", "must be registered-incomplete when sync_id is absent")
                if "missing-sync-id" not in install_statuses:
                    validator.error(f"{install_path}.statuses", "must contain missing-sync-id when sync_id is absent")
                if "missing-sync-id" not in statuses:
                    validator.error(f"{path}.statuses", "must contain missing-sync-id for an incomplete local identity")
                if "synced" in statuses:
                    validator.error(f"{path}.statuses", "cannot be synced while a local install lacks sync_id")
            else:
                validator.string(install_sync_id, f"{install_path}.sync_id")
                if sync_id and install_sync_id != sync_id:
                    validator.error(f"{install_path}.sync_id", "must match the logical Skill sync_id")
                if install.get("identity_status") != "verified":
                    validator.error(f"{install_path}.identity_status", "must be verified when sync_id is present")
            build = builds.get(agent_id) if builds is not None and agent_id else None
            if isinstance(build, dict) and build.get("present") is True and install_digest:
                if build.get("output_digest") != install_digest:
                    install_diverged_count += 1
                    if "agent-install-diverged" not in install_statuses or "agent-install-diverged" not in statuses:
                        validator.error(install_path, "install/build digest mismatch must cause agent-install-diverged on both records")

    unlinked = validator.array(report.get("unlinked_local_skills"), "$.unlinked_local_skills") or []
    validator.sorted_unique(unlinked, "$.unlinked_local_skills", lambda item: (item["path"], tuple(item["agent_ids"])))
    unlinked_fields = {"name", "sync_id", "agent_ids", "path", "core_version", "digest", "statuses"}
    for index, value in enumerate(unlinked):
        path = f"$.unlinked_local_skills[{index}]"
        item = validator.object(value, path, unlinked_fields - {"sync_id"}, unlinked_fields)
        if item is None:
            continue
        validator.string(item.get("name"), f"{path}.name")
        if "sync_id" in item:
            validator.string(item.get("sync_id"), f"{path}.sync_id")
        agent_ids = validator.array(item.get("agent_ids"), f"{path}.agent_ids") or []
        validator.sorted_unique(agent_ids, f"{path}.agent_ids", lambda agent_id: agent_id)
        if not agent_ids:
            validator.error(f"{path}.agent_ids", "must not be empty")
        for agent_index, agent_id in enumerate(agent_ids):
            validator.string(agent_id, f"{path}.agent_ids[{agent_index}]", AGENT_ID_PATTERN)
            if agent_id not in builder_ids:
                validator.error(f"{path}.agent_ids[{agent_index}]", "must reference a declared Builder")
        normalized_unlinked_path = validator.absolute_path(item.get("path"), f"{path}.path")
        if normalized_unlinked_path:
            local_paths.add(normalized_unlinked_path)
        validator.semver(item.get("core_version"), f"{path}.core_version")
        validator.digest(item.get("digest"), f"{path}.digest")
        item_statuses = validator.statuses(item.get("statuses"), f"{path}.statuses")
        if "unlinked-local" not in item_statuses:
            validator.error(f"{path}.statuses", "must contain unlinked-local")
        if "sync_id" not in item and "missing-sync-id" not in item_statuses:
            validator.error(f"{path}.statuses", "must contain missing-sync-id when sync_id is absent")

    issues = validator.array(report.get("issues"), "$.issues") or []
    issue_fields = {"severity", "code", "message", "sync_id", "agent_id", "path"}
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    issue_keys: list[tuple[Any, ...]] = []
    for index, value in enumerate(issues):
        path = f"$.issues[{index}]"
        issue = validator.object(value, path, {"severity", "code", "message"}, issue_fields)
        if issue is None:
            continue
        severity = issue.get("severity")
        if severity not in severity_rank:
            validator.error(f"{path}.severity", "must be error, warning, or info")
        code = issue.get("code")
        if code not in validator.allowed_statuses:
            validator.error(f"{path}.code", f"unknown status {code!r}")
        validator.string(issue.get("message"), f"{path}.message")
        if "sync_id" in issue:
            validator.string(issue.get("sync_id"), f"{path}.sync_id")
        if "agent_id" in issue:
            validator.string(issue.get("agent_id"), f"{path}.agent_id", AGENT_ID_PATTERN)
        issue_path_value = ""
        if "path" in issue:
            issue_path_value = validator.absolute_path(issue.get("path"), f"{path}.path") or ""
        issue_keys.append((severity_rank.get(severity, 99), str(code), str(issue.get("sync_id", "")), str(issue.get("agent_id", "")), issue_path_value))
    if issue_keys != sorted(issue_keys):
        validator.error("$.issues", "must use canonical severity/code/identity/path order")

    sources = validator.array(report.get("scan_sources"), "$.scan_sources") or []
    source_fields = {"kind", "id", "path", "resolver", "status", "skill_count"}
    validator.sorted_unique(sources, "$.scan_sources", lambda item: (item["kind"], item["id"], item.get("path", item.get("resolver", ""))))
    for index, value in enumerate(sources):
        path = f"$.scan_sources[{index}]"
        source = validator.object(value, path, source_fields - {"path", "resolver"}, source_fields)
        if source is None:
            continue
        if source.get("kind") not in {"local", "current-project", "related-project", "adapter", "agent-build"}:
            validator.error(f"{path}.kind", "has an unknown source kind")
        validator.string(source.get("id"), f"{path}.id")
        if source.get("status") == "unresolved-root":
            validator.string(source.get("resolver"), f"{path}.resolver")
            if "path" in source:
                validator.error(f"{path}.path", "must be absent when the resolver has no absolute result")
        else:
            validator.absolute_path(source.get("path"), f"{path}.path")
        if source.get("status") not in {"scanned", "missing-root", "unresolved-root", "invalid"}:
            validator.error(f"{path}.status", "has an unknown source status")
        validator.integer(source.get("skill_count"), f"{path}.skill_count")

    if summary is not None:
        expected_summary = {
            "local_skill_count": len(local_paths),
            "current_project_skill_count": current_project_skill_count,
            "related_project_count": len(related_projects),
            "build_complete_count": complete_count,
            "build_partial_count": partial_count,
            "build_missing_count": missing_count,
            "agent_version_diverged_count": agent_version_diverged_count,
            "agent_install_diverged_count": install_diverged_count,
            "issue_count": len(issues),
        }
        for field, expected in expected_summary.items():
            if summary.get(field) != expected:
                validator.error(f"$.summary.{field}", f"must equal derived value {expected}")

    if validator.errors:
        raise ContractError("\n".join(validator.errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="relationship report JSON to validate")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="schema used for shared status definitions")
    args = parser.parse_args()
    try:
        validate_report(load_json(args.report), args.schema)
    except ContractError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: valid Skill relationship report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
