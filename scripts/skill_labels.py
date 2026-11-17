#!/usr/bin/env python3
"""Keep GitHub issue labels in sync with the Skills in this repository.

Each Skill owns exactly one label named after its directory. When a Skill is
renamed, its label is renamed instead of deleted and recreated, because GitHub
keeps a renamed label attached to every issue and pull request that already
carries it while recreating a label does not. ``metadata.sync_id`` is the
immutable identity that proves a name change is a rename rather than a removal
plus an unrelated addition; ``scripts/version_guard.py`` already rejects an
edited ``sync_id`` for a Skill that still exists.

The tool plans every change from local Skills and the current remote labels
before it mutates anything, so a rejected plan leaves the repository untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
LABEL_COLOR = "1D76DB"
LABEL_DESCRIPTION = "Issues related to the {name} Skill."
MANAGED_DESCRIPTION = re.compile(r"^Issues related to the .+ Skill\.$")
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_LABEL_NAME = 50
API_VERSION = "2022-11-28"


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def is_ancestor(root: Path, revision: str) -> bool:
    """A base that is not a predecessor cannot describe a rename."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def parse_frontmatter(content: str, origin: str) -> dict[str, str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
    require(match is not None, f"{origin}: missing YAML frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        scalar = re.match(r"^[ \t]*(name|sync_id):[ \t]*[\"']?([^\"'\n]+?)[\"']?[ \t]*$", line)
        if scalar is None:
            continue
        key, value = scalar.group(1), scalar.group(2).strip()
        require(key not in values, f"{origin}: duplicate metadata.{key}")
        values[key] = value
    return values


@dataclass(frozen=True)
class Skill:
    name: str
    sync_id: str


def load_skill(name: str, content: str, origin: str) -> Skill:
    values = parse_frontmatter(content, origin)
    require(values.get("name") == name, f"{origin}: name must match its directory ({name})")
    sync_id = values.get("sync_id", "")
    require(sync_id != "", f"{origin}: metadata.sync_id is required")
    require(
        SKILL_NAME.fullmatch(sync_id) is not None,
        f"{origin}: metadata.sync_id must use lowercase letters, digits, and hyphens",
    )
    return Skill(name, sync_id)


def load_skills(root: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    owners: dict[str, str] = {}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        name = path.parent.name
        origin = path.relative_to(root).as_posix()
        # Only a current Skill needs a usable label name; a historical name read
        # from --base only locates an existing label.
        require(
            len(name) <= MAX_LABEL_NAME,
            f"{origin}: Skill name is {len(name)} characters, "
            f"but GitHub rejects label names longer than {MAX_LABEL_NAME}",
        )
        skill = load_skill(name, path.read_text(encoding="utf-8"), origin)
        require(
            skill.sync_id not in owners,
            f"{origin}: metadata.sync_id {skill.sync_id!r} is already used by {owners.get(skill.sync_id)}",
        )
        owners[skill.sync_id] = origin
        skills[name] = skill
    require(
        bool(skills),
        f"{root}/skills contains no Skill; refusing to reconcile labels from an empty tree",
    )
    return skills


def load_skills_at(root: Path, revision: str) -> dict[str, Skill]:
    """Read the Skills that existed at ``revision`` so renames survive a missed run."""
    skills: dict[str, Skill] = {}
    listing = git(root, "ls-tree", "-r", "--name-only", revision, "--", "skills")
    for line in listing.splitlines():
        parts = PurePosixPath(line).parts
        if len(parts) != 3 or parts[0] != "skills" or parts[2] != "SKILL.md":
            continue
        content = git(root, "show", f"{revision}:{line}")
        skills[parts[1]] = load_skill(parts[1], content, f"{revision}:{line}")
    return skills


def renamed_skills(before: dict[str, Skill], after: dict[str, Skill]) -> list[tuple[str, str]]:
    """Return (old name, new name) pairs whose immutable sync_id survived a name change."""
    previous = {skill.sync_id: skill.name for skill in before.values()}
    pairs: list[tuple[str, str]] = []
    for skill in after.values():
        old = previous.get(skill.sync_id)
        if old is not None and old != skill.name:
            pairs.append((old, skill.name))
    return sorted(pairs)


@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str


@dataclass
class Plan:
    deletions: list[str]
    renames: list[tuple[str, str]]
    creates: list[Skill]
    updates: list[tuple[str, str]]
    orphans: list[str]
    notes: list[str]
    total: int

    def actionable(self) -> bool:
        return bool(self.deletions or self.renames or self.creates or self.updates)


def description_for(name: str) -> str:
    return LABEL_DESCRIPTION.format(name=name)


def is_managed(label: Label) -> bool:
    return MANAGED_DESCRIPTION.match(label.description or "") is not None


def build_plan(
    desired: dict[str, Skill],
    labels: dict[str, Label],
    detected: list[tuple[str, str]],
    requested: list[tuple[str, str]],
    prune: bool,
    normalize: bool,
) -> Plan:
    """Resolve every change without touching the remote so a rejected plan is inert."""
    folded_desired = {name.casefold(): name for name in desired}

    def canonical(name: str) -> str | None:
        """Return the Skill a label name belongs to; GitHub names are case-insensitive."""
        if name in desired:
            return name
        return folded_desired.get(name.casefold())

    # Labels are ours when their description matches the template or when their
    # name is a Skill name in different letter case. Everything else is untouched.
    managed = {name for name, label in labels.items() if is_managed(label) or canonical(name) is not None}
    orphans = sorted(name for name in managed if canonical(name) is None)

    notes: list[str] = []
    pairs: list[tuple[str, str]] = []
    folded_labels = {name.casefold() for name in labels}
    for name in sorted(labels):
        target = canonical(name)
        if target is not None and target != name:
            pairs.append((name, target))
    for old, new in detected:
        if old not in labels:
            notes.append(f"skip rename {old} -> {new}: label {old!r} does not exist; it will be created")
            continue
        if new.casefold() in folded_labels:
            notes.append(f"skip rename {old} -> {new}: a label with that name already exists")
            continue
        if old in desired:
            notes.append(f"skip rename {old} -> {new}: another Skill still uses the name {old!r}")
            continue
        pairs.append((old, new))
    pairs.extend(requested)

    queued: dict[str, str] = {}
    for old, new in pairs:
        require(old in labels, f"cannot rename label {old!r}: it does not exist")
        require(old in managed, f"refusing to rename label {old!r}: it is not managed by this tool")
        require(
            old not in desired,
            f"cannot rename label {old!r}: a Skill still uses that name; "
            "rename one of the exchanged labels manually first",
        )
        require(new in desired, f"cannot rename label {old!r} to {new!r}: no Skill uses that name")
        require(old not in queued, f"cannot rename label {old!r} twice")
        require(new not in queued.values(), f"cannot rename two labels to {new!r}")
        queued[old] = new

    # A rename source is not desired any more, but it must survive until it has
    # been renamed; deleting it first would discard every issue association.
    orphans = [name for name in orphans if name not in queued]
    deletion_set = set(orphans) if prune else set()
    occupied = set(labels) - deletion_set
    for old, new in sorted(queued.items()):
        if new not in occupied or new in queued:
            continue
        if new in orphans:
            raise ValueError(
                f"cannot rename label {old!r} to {new!r}: the orphan label {new!r} still uses "
                "that name; rerun with --prune to delete it first"
            )
        raise ValueError(
            f"cannot rename label {old!r} to {new!r}: a label already uses that name; "
            "resolve the duplicate manually"
        )

    ordered: list[tuple[str, str]] = []
    pending = dict(queued)
    while pending:
        ready = sorted(old for old, new in pending.items() if new not in occupied)
        require(
            bool(ready),
            "cannot order the label renames without freeing a name first: "
            + ", ".join(f"{old} -> {new}" for old, new in sorted(pending.items()))
            + "; rename one of those labels manually",
        )
        old = ready[0]
        new = pending.pop(old)
        ordered.append((old, new))
        occupied.discard(old)
        occupied.add(new)

    creates = [desired[name] for name in sorted(desired) if name not in occupied]

    projected = dict(labels)
    for old, new in ordered:
        projected[new] = replace(projected.pop(old), name=new)

    updated: list[tuple[str, str]] = []
    renamed_into = {new for _, new in ordered}
    for name in sorted(desired):
        label = projected.get(name)
        if label is None:
            continue
        reasons = []
        if label.color.upper() != LABEL_COLOR:
            reasons.append(f"color {label.color.upper()} -> {LABEL_COLOR}")
        if name not in renamed_into and label.description != description_for(name):
            reasons.append(f"description {label.description!r} -> {description_for(name)!r}")
        if not reasons:
            continue
        if normalize:
            updated.append((name, "; ".join(reasons)))
        else:
            notes.append(f"{name}: {'; '.join(reasons)}; rerun with --normalize to rewrite it")

    return Plan(
        deletions=sorted(deletion_set),
        renames=ordered,
        creates=creates,
        updates=updated,
        orphans=[name for name in orphans if name not in deletion_set],
        notes=notes,
        total=len(desired),
    )


def describe(plan: Plan) -> list[str]:
    lines: list[str] = []
    for name in plan.deletions:
        lines.append(f"DELETE   {name} (no Skill uses this label; --prune)")
    for old, new in plan.renames:
        lines.append(f"RENAME   {old} -> {new} (issue associations are preserved)")
    for skill in plan.creates:
        lines.append(f"CREATE   {skill.name}")
    for name, reason in plan.updates:
        lines.append(f"UPDATE   {name}: {reason}")
    for name in plan.orphans:
        lines.append(f"KEEP     {name} (no Skill uses this label; rerun with --prune to delete)")
    for note in plan.notes:
        lines.append(f"NOTE     {note}")
    return lines


class ApiError(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"GitHub API {status}: {detail}")
        self.status = status
        self.detail = detail


class GitHub:
    def __init__(self, api_url: str, repository: str, token: str | None, per_page: int) -> None:
        self.api_url = api_url.rstrip("/")
        self.repository = repository
        self.token = token
        self.per_page = per_page

    def request(self, method: str, path: str, payload: dict[str, object] | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(f"{self.api_url}{path}", data=data, method=method)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", API_VERSION)
        request.add_header("User-Agent", "skill-labels")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None, response.headers
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace").strip()
            try:
                parsed = json.loads(detail)
                messages = [str(parsed.get("message", ""))]
                messages.extend(
                    str(item.get("message") or item.get("code") or "")
                    for item in parsed.get("errors", [])
                    if isinstance(item, dict)
                )
                detail = "; ".join(part for part in messages if part) or detail
            except json.JSONDecodeError:
                pass
            raise ApiError(error.code, detail) from None

    def labels(self) -> dict[str, Label]:
        labels: dict[str, Label] = {}
        page = 1
        while True:
            payload, headers = self.request(
                "GET", f"/repos/{self.repository}/labels?per_page={self.per_page}&page={page}"
            )
            for item in payload or []:
                labels[item["name"]] = Label(
                    name=item["name"],
                    color=str(item.get("color", "")),
                    description=str(item.get("description") or ""),
                )
            link = headers.get("Link", "")
            if 'rel="next"' not in link:
                return labels
            page += 1

    def label_path(self, name: str) -> str:
        return f"/repos/{self.repository}/labels/{urllib.parse.quote(name, safe='')}"

    def create(self, skill: Skill) -> None:
        self.request(
            "POST",
            f"/repos/{self.repository}/labels",
            {
                "name": skill.name,
                "color": LABEL_COLOR,
                "description": description_for(skill.name),
            },
        )

    def rename(self, old: str, new: str) -> None:
        self.request(
            "PATCH",
            self.label_path(old),
            {"new_name": new, "description": description_for(new)},
        )

    def update(self, name: str) -> None:
        self.request(
            "PATCH",
            self.label_path(name),
            {"color": LABEL_COLOR, "description": description_for(name)},
        )

    def delete(self, name: str) -> None:
        self.request("DELETE", self.label_path(name))


def apply_plan(api: GitHub, plan: Plan) -> None:
    for name in plan.deletions:
        api.delete(name)
    for old, new in plan.renames:
        api.rename(old, new)
    for skill in plan.creates:
        api.create(skill)
    for name, _ in plan.updates:
        api.update(name)


def resolve_repository(value: str | None) -> str:
    repository = value or os.environ.get("GITHUB_REPOSITORY", "")
    require(
        re.fullmatch(r"[^/\s]+/[^/\s]+", repository) is not None,
        "set --repository or GITHUB_REPOSITORY to owner/name",
    )
    return repository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to read Skills from")
    parser.add_argument("--base", default="", help="commit before the change; enables Skill rename detection")
    parser.add_argument("--rename", action="append", default=[], metavar="OLD=NEW", help="extra label rename to apply")
    parser.add_argument("--apply", action="store_true", help="perform the planned changes instead of only printing them")
    parser.add_argument("--check", action="store_true", help="exit non-zero when the labels are not already in sync")
    parser.add_argument("--prune", action="store_true", help="delete labels whose Skill no longer exists")
    parser.add_argument("--normalize", action="store_true", help="rewrite color and description drift on managed labels")
    parser.add_argument("--repository", default=None, help="owner/name; defaults to GITHUB_REPOSITORY")
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--token-env", default="GITHUB_TOKEN", help="environment variable holding the API token")
    args = parser.parse_args()

    try:
        root = args.root.resolve()
        require(args.per_page > 0, "--per-page must be a positive integer")
        desired = load_skills(root)

        rename_pairs: list[tuple[str, str]] = []
        if args.base:
            git(root, "rev-parse", "--verify", "--end-of-options", f"{args.base}^{{commit}}")
            if is_ancestor(root, args.base):
                rename_pairs = list(renamed_skills(load_skills_at(root, args.base), desired))
            else:
                print(
                    f"NOTE     --base {args.base} is not an ancestor of HEAD; "
                    "Skill rename detection is skipped"
                )
        requested: list[tuple[str, str]] = []
        for item in args.rename:
            old, separator, new = item.partition("=")
            require(bool(separator and old and new), f"--rename expects OLD=NEW, got {item!r}")
            requested.append((old, new))

        token = os.environ.get(args.token_env) or os.environ.get("GH_TOKEN") or None
        if args.apply:
            require(token is not None, f"--apply requires a token in ${args.token_env} or $GH_TOKEN")

        api = GitHub(args.api_url, resolve_repository(args.repository), token, args.per_page)
        plan = build_plan(desired, api.labels(), rename_pairs, requested, args.prune, args.normalize)

        for line in describe(plan):
            print(line)
        changes = len(plan.deletions) + len(plan.renames) + len(plan.creates) + len(plan.updates)
        if args.apply:
            apply_plan(api, plan)
            print(f"PASS: applied {changes} change(s) across {plan.total} Skill label(s)")
            return 0
        if args.check and plan.actionable():
            print(f"FAIL: {plan.total} Skill labels are not in sync; rerun with --apply", file=sys.stderr)
            return 1
        if changes:
            print(f"PLAN: {changes} change(s) pending across {plan.total} Skill label(s); rerun with --apply")
        else:
            print(f"PASS: {plan.total} Skill labels in sync (no changes)")
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        message = str(error)
        print(f"FAIL: {message}", file=sys.stderr)
        escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::{escaped}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
