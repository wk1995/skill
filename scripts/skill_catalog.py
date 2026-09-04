#!/usr/bin/env python3
"""Validate Skills and render the bilingual root Skills catalogs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
CATALOG_START = "<!-- skills-catalog:start -->"
CATALOG_END = "<!-- skills-catalog:end -->"
ENGLISH_SECTIONS = ("## How To Use It", "## When It Triggers", "## When It Does Not Trigger")
CHINESE_SECTIONS = ("## 如何使用", "## 何时触发", "## 何时不触发")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SYNC_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ValidationError(Exception):
    """Raised when a managed Skill violates the repository contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def frontmatter(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, flags=re.DOTALL)
    require(match is not None, f"{path.relative_to(ROOT)} must start with YAML frontmatter")

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        match = re.match(r"^(\s*)(name|description|sync_id|version):\s*[\"']?(.+?)[\"']?\s*$", line)
        if match:
            values[match.group(2)] = match.group(3)
    return values


def first_body_paragraph(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    paragraph: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("语言：") or stripped.startswith("Language:"):
            continue
        paragraph.append(stripped)
    require(paragraph, f"{path.relative_to(ROOT)} must include an introductory paragraph")
    return " ".join(paragraph)


def validate_skill(skill_dir: Path) -> tuple[str, str, str]:
    name = skill_dir.name
    relative = skill_dir.relative_to(ROOT)
    require(SKILL_NAME.fullmatch(name) is not None, f"{relative} must use a lowercase hyphenated name")

    skill_file = skill_dir / "SKILL.md"
    english_readme = skill_dir / "README.md"
    chinese_readme = skill_dir / "README.zh-CN.md"
    changelog = skill_dir / "CHANGELOG.md"
    for path in (skill_file, english_readme, chinese_readme, changelog):
        require(path.is_file(), f"{relative} is missing {path.name}")

    metadata = frontmatter(skill_file)
    require(metadata.get("name") == name, f"{relative}/SKILL.md name must match its directory")
    require(metadata.get("description"), f"{relative}/SKILL.md must define description")
    require(metadata.get("sync_id"), f"{relative}/SKILL.md must define metadata.sync_id")
    require(SYNC_ID.fullmatch(metadata["sync_id"]) is not None,
            f"{relative}/SKILL.md metadata.sync_id must use lowercase letters, digits, and hyphens")
    require(metadata.get("version"), f"{relative}/SKILL.md must define metadata.version")

    changelog_content = changelog.read_text(encoding="utf-8")
    require(re.search(r"^## \[Unreleased\]\s*$", changelog_content, flags=re.MULTILINE) is not None,
            f"{relative}/CHANGELOG.md must define an [Unreleased] section")
    require(re.search(r"^## \[" + re.escape(metadata["version"]) + r"\]\s+-\s+\d{4}-\d{2}-\d{2}\s*$",
                      changelog_content, flags=re.MULTILINE) is not None,
            f"{relative}/CHANGELOG.md must document current metadata.version {metadata['version']} with a UTC date")

    skill_content = skill_file.read_text(encoding="utf-8")
    require("triggering:" in skill_content and "include:" in skill_content and "exclude:" in skill_content,
            f"{relative}/SKILL.md must define metadata.triggering include and exclude rules")

    english_content = english_readme.read_text(encoding="utf-8")
    chinese_content = chinese_readme.read_text(encoding="utf-8")
    for section in ENGLISH_SECTIONS:
        require(section in english_content, f"{relative}/README.md is missing {section}")
    for section in CHINESE_SECTIONS:
        require(section in chinese_content, f"{relative}/README.zh-CN.md is missing {section}")
    require("README.zh-CN.md" in english_content, f"{relative}/README.md must link to its Chinese README")
    require("README.md" in chinese_content, f"{relative}/README.zh-CN.md must link to its English README")

    return name, metadata["description"], first_body_paragraph(chinese_readme)


def render_catalog(skills: list[tuple[str, str, str]], language: str) -> str:
    def table_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    if language == "en":
        rows = ["| Skill | Purpose | Documentation |", "| --- | --- | --- |"]
        rows.extend(
            f"| `{name}` | {table_cell(description)} | [README](skills/{name}/README.md) |"
            for name, description, _ in skills
        )
    else:
        rows = ["| Skill | 用途 | 文档 |", "| --- | --- | --- |"]
        rows.extend(
            f"| `{name}` | {table_cell(description)} | [README](skills/{name}/README.zh-CN.md) |"
            for name, _, description in skills
        )
    return "\n".join((CATALOG_START, *rows, CATALOG_END))


def update_catalog(path: Path, catalog: str, write: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    match = re.search(f"{re.escape(CATALOG_START)}.*?{re.escape(CATALOG_END)}", content, flags=re.DOTALL)
    require(match is not None, f"{path.relative_to(ROOT)} is missing Skills catalog markers")
    updated = content[:match.start()] + catalog + content[match.end():]
    if updated == content:
        return False
    if write:
        path.write_text(updated, encoding="utf-8")
    return True


def print_error(message: str) -> None:
    """Print a readable failure and a GitHub Actions error annotation."""
    print(f"FAIL: {message}", file=sys.stderr)
    path_match = re.match(r"((?:skills/[^ ]+|README(?:\.zh-CN)?\.md)[^ ]*)", message)
    if path_match:
        print(f"::error file={path_match.group(1)}::{message}", file=sys.stderr)
    else:
        print(f"::error::{message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate Skills and fail when a catalog is stale")
    mode.add_argument("--write", action="store_true", help="validate Skills and update stale catalogs")
    args = parser.parse_args()

    skills: list[tuple[str, str, str]] = []
    errors: list[str] = []
    sync_ids: dict[str, str] = {}
    for path in sorted(SKILLS_DIR.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        try:
            skills.append(validate_skill(path))
            sync_id = frontmatter(path / "SKILL.md")["sync_id"]
            previous = sync_ids.get(sync_id)
            if previous:
                errors.append(
                    f"{path.relative_to(ROOT)}/SKILL.md metadata.sync_id {sync_id!r} is already used by {previous}"
                )
            else:
                sync_ids[sync_id] = str(path.relative_to(ROOT))
        except ValidationError as error:
            errors.append(str(error))

    if not skills and not errors:
        errors.append("skills/ must contain at least one Skill")
    if errors:
        for error in errors:
            print_error(error)
        return 1

    try:
        english_changed = update_catalog(ROOT / "README.md", render_catalog(skills, "en"), args.write)
        chinese_changed = update_catalog(ROOT / "README.zh-CN.md", render_catalog(skills, "zh"), args.write)
    except ValidationError as error:
        print_error(str(error))
        return 1

    if (english_changed or chinese_changed) and args.check:
        print_error("Skills catalogs are stale; run python scripts/skill_catalog.py --write")
        return 1
    print("PASS: Skill structure and bilingual catalogs are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
