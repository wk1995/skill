#!/usr/bin/env python3
"""Validate release versions in committed PR merges or default-branch pushes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import re
import sys
from dataclasses import dataclass

from pr_review_guard import git, merge_tree


VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
IDENTITY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def version_parts(value: object, path: str) -> tuple[str, str, str]:
    require(isinstance(value, str) and VERSION.fullmatch(value),
            f"{path}: version must be canonical MAJOR.MINOR.PATCH (no leading zeroes or suffixes): {value!r}")
    return tuple(value.split("."))


def increment(value: str) -> str:
    # Decimal strings avoid an arbitrary machine-integer or Python int-digit limit.
    digits = list(value)
    for index in range(len(digits) - 1, -1, -1):
        if digits[index] != "9":
            digits[index] = str(int(digits[index]) + 1)
            return "".join(digits)
        digits[index] = "0"
    return "1" + "".join(digits)


def metadata(content: str, path: str) -> dict[str, str]:
    """Read direct scalar keys from the repository's block-style metadata mapping."""
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
    require(match, f"{path}: missing YAML frontmatter")
    lines = match[1].splitlines()
    starts = [i for i, line in enumerate(lines) if re.fullmatch(r"metadata:\s*(?:#.*)?", line)]
    require(len(starts) == 1 and sum(line.startswith("metadata:") for line in lines) == 1,
            f"{path}: require one block-style metadata mapping")
    block = []
    for line in lines[starts[0] + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        require(not line.startswith("\t"), f"{path}: metadata must use spaces")
        if not line.startswith(" "):
            break
        block.append(line)
    require(block, f"{path}: empty metadata mapping")
    indent = min(len(line) - len(line.lstrip(" ")) for line in block)
    values = {}
    for line in block:
        if len(line) - len(line.lstrip(" ")) != indent:
            continue
        pair = re.fullmatch(r"\s*(sync_id|version):\s*(.*?)\s*", line)
        if not pair:
            continue
        key, raw = pair.groups()
        require(key not in values, f"{path}: duplicate metadata.{key}")
        scalar = re.fullmatch(r'''(?:"([^"\\]*)"|'([^']*)'|([^\s#'"{}\[\],]+))(?:\s+#.*)?''', raw)
        require(scalar, f"{path}: metadata.{key} must be a plain or quoted scalar")
        values[key] = next(value for value in scalar.groups() if value is not None)
    require(set(values) == {"sync_id", "version"}, f"{path}: require metadata.sync_id and metadata.version")
    # Existing builders/sync readers select the first scalar match anywhere in
    # frontmatter; the catalog selects the last. Until those external-compatible
    # readers share a scoped parser, admit only inputs on which they all agree.
    for key, value in values.items():
        occurrences = re.findall(r"^\s*" + key + r"\s*:", match[1], re.MULTILINE)
        matches = re.findall(r"^\s*" + key + r'''\s*:\s*["']?([^"'\n]+)["']?\s*$''',
                             match[1], re.MULTILINE)
        require(len(occurrences) == len(matches) == 1 and matches[0].strip() == value,
                f"{path}: ambiguous metadata.{key}; use one direct scalar without inline comments "
                "and no other occurrence of that key in frontmatter")
    return values


class Tree:
    def __init__(self, ref: str):
        self.ref = ref
        self.files = {}
        for item in git("ls-tree", "-rz", ref, "--", "skills", "platforms").stdout.split("\0"):
            if item:
                entry, path = item.split("\t", 1)
                self.files[path] = entry.split()[0]
                require(len(path.split("/")) > 1, f"{path}: component root must be a tracked directory")
                require(not (len(path.split("/")) == 2 and self.files[path] in {"120000", "160000"}),
                        f"{path}: component directories cannot be symlinks or submodules")

    def read(self, path: str) -> str:
        require(self.files.get(path) in {"100644", "100755"}, f"{path}: must be a tracked regular file")
        return git("show", f"{self.ref}:{path}").stdout


@dataclass(frozen=True)
class Component:
    key: tuple[str, str]
    path: str
    version: str
    changelog: str
    artifact: bool = False


def components(tree: Tree) -> dict[tuple[str, str], Component]:
    found = {}
    for path in sorted(tree.files):
        parts = path.split("/")
        if len(parts) != 3:
            continue
        owner, directory, filename = parts
        entries = []
        if owner == "skills" and filename == "SKILL.md":
            values = metadata(tree.read(path), path)
            entries = [("skill", values["sync_id"], values["version"], False)]
        elif owner == "platforms" and filename == "adapter.json":
            config = json.loads(tree.read(path), object_pairs_hook=unique_json_keys)
            require(isinstance(config, dict), f"{path}: adapter must be an object")
            require(config.get("id") == directory, f"{path}: adapter id must match directory")
            entries = [(kind, config.get("id"), config.get(field), artifact)
                       for kind, field, artifact in (("adapter", "version", False),
                                                    ("artifact", "artifact_version", True))]
        for kind, identity, version, artifact in entries:
            require(isinstance(identity, str) and IDENTITY.fullmatch(identity), f"{path}: invalid component identity")
            version_parts(version, path)
            key = (kind, identity)
            require(key not in found, f"{path}: duplicate {kind} identity {identity}")
            found[key] = Component(key, path, version, f"{owner}/{directory}/CHANGELOG.md", artifact)
    return found


def unique_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key {key}")
        result[key] = value
    return result


def markdown_prose(content: str) -> str:
    """Mask fenced examples and HTML comments before interpreting release fields."""
    result = []
    fence = None
    in_comment = False
    for line in content.splitlines():
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}[ \t]*", line):
                fence = None
            result.append("")
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line) if not in_comment else None
        if opening and (opening[1][0] == "~" or "`" not in opening[2]):
            fence = (opening[1][0], len(opening[1]))
            result.append("")
            continue
        # Preserve columns outside comments so hidden text cannot create a new
        # column-zero heading or bullet. Fence markers inside comments are inert.
        visible = ""
        while line:
            if in_comment:
                end = line.find("-->")
                if end < 0:
                    visible += " " * len(line)
                    break
                visible += " " * (end + 3)
                line = line[end + 3:]
                in_comment = False
            else:
                start = line.find("<!--")
                if start < 0:
                    visible += line
                    break
                visible += line[:start] + " " * 4
                line = line[start + 4:]
                in_comment = True
        result.append(visible)
    return "\n".join(result)


def release_entry(tree: Tree, component: Component) -> tuple[str, str]:
    label = ("artifact " if component.artifact else "") + component.version
    content = markdown_prose(tree.read(component.changelog))
    headings = list(re.finditer(r"^## (.+)$", content, re.MULTILINE))
    matches = [(i, heading) for i, heading in enumerate(headings)
               if heading[1].startswith(f"[{label}]")]
    require(len(matches) == 1, f"{component.changelog}: require one new release entry [{label}]")
    index, heading = matches[0]
    parsed = re.fullmatch(r"\[" + re.escape(label) + r"\] - (\d{4}-\d{2}-\d{2})", heading[1])
    require(parsed, f"{component.changelog}: [{label}] must have a UTC YYYY-MM-DD date")
    release_date = date.fromisoformat(parsed[1])
    require(release_date <= datetime.now(timezone.utc).date(), f"{component.changelog}: release date cannot be in the future")
    end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
    return label, content[heading.end():end]


def declaration(body: str, field: str, path: str) -> str:
    values = re.findall(r"^- " + re.escape(field) + r":[ \t]*(.*)$", body, re.MULTILINE)
    require(len(values) == 1 and values[0].strip(), f"{path}: require one non-empty '- {field}: ...' in the release entry")
    value = values[0].strip()
    require(value.casefold() not in {"todo", "tbd", "...", "n/a", "none"}, f"{path}: {field} must contain release evidence, not a placeholder")
    return value


def validate_release(base: Tree, result: Tree, old: Component | None, new: Component) -> None:
    label, body = release_entry(result, new)
    if old:
        previous = markdown_prose(base.read(old.changelog))
        require(not re.search(r"^## \[" + re.escape(label) + r"\]", previous, re.MULTILINE),
                f"{new.changelog}: cannot reuse existing release [{label}]")
    change_type = declaration(body, "Change-Type", new.changelog)
    declaration(body, "Summary", new.changelog)
    declaration(body, "Compatibility", new.changelog)
    if old is None:
        require(change_type == "initial" and new.version in {"0.1.0", "1.0.0"},
                f"{new.path}: new components require Change-Type: initial and version 0.1.0 or 1.0.0")
    else:
        major, minor, patch = version_parts(old.version, old.path)
        expected = {"fix": f"{major}.{minor}.{increment(patch)}",
                    "feature": f"{major}.{increment(minor)}.0",
                    "breaking": f"{increment(major)}.0.0"}
        if major == "0":
            expected["stable"] = "1.0.0"
        require(change_type in expected and new.version == expected.get(change_type),
                f"{new.path}: {old.version} -> {new.version} does not match Change-Type: {change_type}; "
                f"allowed next releases: {expected}")
    if change_type == "breaking":
        declaration(body, "Breaking-Change", new.changelog)
        declaration(body, "Migration", new.changelog)
    if change_type == "stable" or (old is None and new.version == "1.0.0"):
        declaration(body, "Stable-Contract", new.changelog)
        declaration(body, "Readiness", new.changelog)


def check(base_ref: str, head_ref: str, mode: str = "pr") -> int:
    require(mode in {"pr", "push"}, f"unknown comparison mode: {mode}")
    base_sha = git("rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}").stdout.strip()
    head_sha = git("rev-parse", "--verify", "--end-of-options", f"{head_ref}^{{commit}}").stdout.strip()
    if mode == "push":
        ancestry = git("merge-base", "--is-ancestor", base_sha, head_sha, check=False)
        require(ancestry.returncode == 0,
                "push comparison requires before to be an ancestor of after; rewinds or divergent history are not allowed")
    base = Tree(base_sha)
    head = Tree(head_sha)
    # Validate authored inputs as well as the simulated merge; an unrelated base
    # advance must not look like a PR downgrade or disappear from final checks.
    components(head)
    result = head if mode == "push" else Tree(merge_tree(base_sha, head_sha))
    before, after = components(base), components(result)
    old_paths = {item.path: item for item in before.values() if item.key[0] == "skill"}
    changed = 0
    for key, new in after.items():
        previous_at_path = old_paths.get(new.path)
        if new.key[0] == "skill" and previous_at_path:
            require(previous_at_path.key == key or previous_at_path.key in after,
                    f"{new.path}: metadata.sync_id is immutable")
        old = before.get(key)
        if old is None or old.version != new.version:
            validate_release(base, result, old, new)
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="exact PR base or push before commit")
    parser.add_argument("--head", default="HEAD", help="committed PR head or push after commit; working-tree edits are not read")
    parser.add_argument("--mode", choices=("pr", "push"), default="pr",
                        help="pr: simulate merge; push: compare exact before/after and require forward history")
    args = parser.parse_args()
    try:
        changed = check(args.base, args.head, args.mode)
    except (ValueError, RuntimeError, OSError) as error:
        message = str(error)
        print(f"FAIL: {message}", file=sys.stderr)
        escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::{escaped}", file=sys.stderr)
        return 1
    print(f"PASS: version format and {changed} release declaration(s); compatibility claims require review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
