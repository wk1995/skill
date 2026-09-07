#!/usr/bin/env python3
"""Build portable Skills for a declaratively configured agent platform."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
PLATFORMS_DIR = ROOT / "platforms"
DEFAULT_OUTPUT_DIR = ROOT / "dist"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
RESERVED_OVERRIDE_FILES = {"SKILL.append.md"}


class BuildError(Exception):
    """Raised when adapter input or build output is unsafe or invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def relative_path(value: object, field: str, *, allow_dot: bool = False) -> Path:
    require(isinstance(value, str) and value, f"{field} must be a non-empty string")
    require("\\" not in value, f"{field} must use '/' path separators")
    candidate = PurePosixPath(value)
    require(not candidate.is_absolute(), f"{field} must be relative")
    require(".." not in candidate.parts, f"{field} must not contain '..'")
    require(allow_dot or value != ".", f"{field} must not be '.'")
    return Path(*candidate.parts)


def read_adapter(platform: str) -> tuple[Path, dict[str, object]]:
    require(NAME_PATTERN.fullmatch(platform) is not None, f"invalid platform name: {platform}")
    platform_dir = PLATFORMS_DIR / platform
    config_path = platform_dir / "adapter.json"
    require(config_path.is_file(), f"unknown platform {platform!r}: missing {config_path.relative_to(ROOT)}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f"cannot read {config_path.relative_to(ROOT)}: {error}") from error
    require(isinstance(config, dict), f"{config_path.relative_to(ROOT)} must contain a JSON object")
    require(config.get("schema_version") == 1, f"{config_path.relative_to(ROOT)} schema_version must be 1")
    require(config.get("id") == platform, f"{config_path.relative_to(ROOT)} id must match its directory")
    for field in ("version", "artifact_version"):
        value = config.get(field)
        require(isinstance(value, str) and VERSION_PATTERN.fullmatch(value) is not None,
                f"{config_path.relative_to(ROOT)} {field} must be SemVer")
    changelog = platform_dir / "CHANGELOG.md"
    require(changelog.is_file(), f"{platform_dir.relative_to(ROOT)} is missing CHANGELOG.md")
    changelog_content = changelog.read_text(encoding="utf-8")
    require(re.search(r"^## \[" + re.escape(str(config["version"])) + r"\] - \d{4}-\d{2}-\d{2}$",
                      changelog_content, flags=re.MULTILINE) is not None,
            f"{changelog.relative_to(ROOT)} must document adapter version {config['version']}")
    relative_path(config.get("skills_path"), "skills_path", allow_dot=True)
    for field in ("root_overlay", "skill_overlay", "skill_append"):
        if field in config:
            configured = platform_dir / relative_path(config[field], field)
            if field == "skill_append":
                require(configured.is_file() and not configured.is_symlink(),
                        f"{config_path.relative_to(ROOT)} {field} must name a regular file")
            else:
                require(configured.is_dir() and not configured.is_symlink(),
                        f"{config_path.relative_to(ROOT)} {field} must name a regular directory")
                if field == "skill_overlay":
                    require(not (configured / "SKILL.md").exists(),
                            f"{field} must not replace portable SKILL.md; use skill_append")
    return platform_dir, config


def platform_names() -> list[str]:
    if not PLATFORMS_DIR.is_dir():
        return []
    return [
        path.name
        for path in sorted(PLATFORMS_DIR.iterdir())
        if path.is_dir() and (path / "adapter.json").is_file()
    ]


def skill_metadata(skill_dir: Path) -> tuple[str, str]:
    skill_file = skill_dir / "SKILL.md"
    require(skill_file.is_file(), f"{skill_dir.relative_to(ROOT)} is missing SKILL.md")
    content = skill_file.read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---\n", content, flags=re.DOTALL)
    require(frontmatter is not None, f"{skill_file.relative_to(ROOT)} has invalid frontmatter")
    name_match = re.search(r"^name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter.group(1), re.MULTILINE)
    version_match = re.search(r"^\s+version:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter.group(1), re.MULTILINE)
    require(name_match is not None, f"{skill_file.relative_to(ROOT)} is missing name")
    require(version_match is not None, f"{skill_file.relative_to(ROOT)} is missing metadata.version")
    name = name_match.group(1).strip()
    version = version_match.group(1).strip()
    require(name == skill_dir.name, f"{skill_file.relative_to(ROOT)} name must match its directory")
    require(VERSION_PATTERN.fullmatch(version) is not None, f"{skill_file.relative_to(ROOT)} version must be SemVer")
    require((skill_dir / "agent-builds").is_dir(), f"{skill_dir.relative_to(ROOT)} is missing agent-builds/")
    return name, version


def selected_skills(names: list[str]) -> list[tuple[Path, str, str]]:
    requested = set(names)
    discovered: list[tuple[Path, str, str]] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        name, version = skill_metadata(skill_dir)
        if not requested or name in requested:
            discovered.append((skill_dir, name, version))
            requested.discard(name)
    require(not requested, f"unknown Skill(s): {', '.join(sorted(requested))}")
    require(discovered, "no Skills selected")
    return discovered


def copy_tree(
    source: Path,
    target: Path,
    *,
    skip_top: set[str] | None = None,
    skip_names: set[str] | None = None,
) -> None:
    if not source.exists():
        return
    require(source.is_dir() and not source.is_symlink(), f"overlay must be a regular directory: {source}")
    skipped_top = skip_top or set()
    skipped_names = skip_names or set()
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if relative.parts[0] in skipped_top or any(part in skipped_names for part in relative.parts):
            continue
        require(not path.is_symlink(), f"build inputs must not contain symbolic links: {path}")
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        else:
            raise BuildError(f"unsupported build input: {path}")


def validate_tree(root: Path) -> None:
    """Reject links and special files before a build writes any output."""
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"build inputs must not contain symbolic links: {path}")
        require(path.is_dir() or path.is_file(), f"unsupported build input: {path}")


def validate_override_tree(root: Path) -> None:
    """Validate one per-Skill override and its reserved append fragment."""
    validate_tree(root)
    for path in sorted(root.rglob("*")):
        if path.name not in RESERVED_OVERRIDE_FILES:
            continue
        require(
            path.parent == root and path.is_file(),
            f"reserved override file must be a regular file at the override root: {path}",
        )


def append_instructions(target: Path, fragments: list[Path], values: dict[str, str]) -> None:
    additions: list[str] = []
    for fragment in fragments:
        if not fragment.exists():
            continue
        require(fragment.is_file() and not fragment.is_symlink(), f"instruction fragment must be a regular file: {fragment}")
        text = fragment.read_text(encoding="utf-8").strip()
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        if text:
            additions.append(text)
    if not additions:
        return
    core = target.read_text(encoding="utf-8").rstrip()
    target.write_text(core + "\n\n" + "\n\n".join(additions) + "\n", encoding="utf-8")


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def safe_output(output: Path) -> Path:
    root = ROOT.resolve()
    default_output_dir = DEFAULT_OUTPUT_DIR.resolve()
    expanded = output.expanduser()
    require(not expanded.is_symlink(), "output must not be a symbolic link")
    resolved = expanded.resolve()
    require(resolved != root, "output must not be the repository root")
    require(not root.is_relative_to(resolved), "output must not contain the repository root")
    if resolved.is_relative_to(root):
        require(
            resolved != default_output_dir and resolved.is_relative_to(default_output_dir),
            "output inside the repository must be a child of dist/",
        )
    return resolved


def validate_replacement(output: Path, platform: str, force: bool) -> None:
    """Allow replacement only for a build artifact owned by this platform."""
    if not output.exists():
        return
    require(force, f"output already exists: {output}; pass --force to replace it")
    require(output.is_dir(), f"refusing to replace non-directory output: {output}")
    manifest_path = output / ".agent-build.json"
    require(
        manifest_path.is_file() and not manifest_path.is_symlink(),
        f"refusing to replace unrecognized output without a regular .agent-build.json: {output}",
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f"cannot validate existing build output {output}: {error}") from error
    require(isinstance(manifest, dict), f"existing build manifest must contain a JSON object: {manifest_path}")
    require(manifest.get("schema_version") == 1, f"unsupported existing build manifest: {manifest_path}")
    require(
        manifest.get("platform") == platform,
        f"existing output belongs to platform {manifest.get('platform')!r}, not {platform!r}: {output}",
    )


def build(platform: str, skill_names: list[str], output_arg: str | None, force: bool) -> Path:
    validate_all()
    platform_dir, config = read_adapter(platform)
    skills = selected_skills(skill_names)
    output = safe_output(Path(output_arg) if output_arg else DEFAULT_OUTPUT_DIR / platform)
    validate_replacement(output, platform, force)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-build-", dir=output.parent))
    try:
        root_overlay = config.get("root_overlay")
        if root_overlay:
            copy_tree(platform_dir / relative_path(root_overlay, "root_overlay"), staging)

        skills_root = staging / relative_path(config["skills_path"], "skills_path", allow_dot=True)
        skills_root.mkdir(parents=True, exist_ok=True)
        manifest_skills: list[dict[str, str]] = []
        for skill_dir, name, version in skills:
            target = skills_root / name
            copy_tree(skill_dir, target, skip_top={"agent-builds"})

            skill_overlay = config.get("skill_overlay")
            if skill_overlay:
                copy_tree(platform_dir / relative_path(skill_overlay, "skill_overlay"), target)

            override = skill_dir / "agent-builds" / platform
            require(not (override / "SKILL.md").exists(),
                    f"{override.relative_to(ROOT)}/SKILL.md must not replace the portable core; use SKILL.append.md")
            copy_tree(override, target, skip_names=RESERVED_OVERRIDE_FILES)

            fragments: list[Path] = []
            skill_append = config.get("skill_append")
            if skill_append:
                fragments.append(platform_dir / relative_path(skill_append, "skill_append"))
            fragments.append(override / "SKILL.append.md")
            append_instructions(
                target / "SKILL.md",
                fragments,
                {
                    "skill_name": name,
                    "adapter_id": platform,
                    "adapter_version": str(config["version"]),
                    "artifact_version": str(config["artifact_version"]),
                },
            )
            manifest_skills.append({"name": name, "version": version, "digest": digest_tree(target)})

        manifest = {
            "schema_version": 1,
            "platform": platform,
            "adapter_version": config["version"],
            "artifact_version": config["artifact_version"],
            "skills": manifest_skills,
        }
        (staging / ".agent-build.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
        return output
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate_all() -> None:
    names = platform_names()
    require(names, "platforms/ does not contain any adapters")
    skills = selected_skills([])
    for name in names:
        platform_dir, _ = read_adapter(name)
        validate_tree(platform_dir)
    known = set(names)
    for skill_dir, _, _ in skills:
        for override in sorted((skill_dir / "agent-builds").iterdir()):
            if override.name.startswith("."):
                continue
            require(override.is_dir() and not override.is_symlink(), f"invalid agent build override: {override}")
            require(override.name in known, f"{override.relative_to(ROOT)} has no matching platform adapter")
            require(not (override / "SKILL.md").exists(),
                    f"{override.relative_to(ROOT)}/SKILL.md must not replace the portable core; use SKILL.append.md")
            validate_override_tree(override)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", nargs="?", help="platform adapter id")
    parser.add_argument("--skill", action="append", default=[], help="build only this Skill; repeat as needed")
    parser.add_argument("--output", help="output directory (default: dist/<platform>)")
    parser.add_argument("--force", action="store_true", help="replace an existing output directory")
    parser.add_argument("--list", action="store_true", help="list discovered platform adapters")
    parser.add_argument("--check", action="store_true", help="validate adapters and Skill overrides without building")
    args = parser.parse_args()

    try:
        if args.list:
            require(not args.platform, "do not pass a platform with --list")
            for name in platform_names():
                _, config = read_adapter(name)
                print(f"{name}\tadapter={config['version']}\tartifact={config['artifact_version']}")
            return 0
        if args.check:
            require(not args.platform, "do not pass a platform with --check")
            validate_all()
            print(f"PASS: {len(platform_names())} platform adapters and all Skill overrides are valid")
            return 0
        require(args.platform is not None, "platform is required unless --list or --check is used")
        output = build(args.platform, args.skill, args.output, args.force)
        print(f"Built {args.platform} artifact at {output}")
        return 0
    except BuildError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
