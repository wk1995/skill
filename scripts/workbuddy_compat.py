#!/usr/bin/env python3
"""Keep Agent Skills compatible with both OpenAI Codex and WorkBuddy.

This script is the reusable gate behind the ``workbuddy-compat`` Skill and the
``workbuddy-compat`` CI step. It enforces two WorkBuddy-compatibility rules for
every Skill under ``skills/``:

1. ``SKILL.md`` must contain a ``## Platform Compatibility`` section that
   documents Codex vs WorkBuddy behavior (paths, triggering, ignored files).
2. A README's "How To Use It" / "如何使用" section must not teach WorkBuddy
   users the Codex-only ``$<skill>`` invocation syntax, except inside an
   explicit "OpenAI Codex" note.

``--check`` reports gaps and exits non-zero when any Skill fails.
``--fix`` idempotently injects the Platform Compatibility section and rewrites
README examples so the gate passes; it never removes Codex behavior.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

PLATFORM_HEADING = "## Platform Compatibility"
EN_SECTION = "## How To Use It"
ZH_SECTION = "## 如何使用"

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Generic Platform Compatibility section injected into SKILL.md. {name} is the
# Skill directory name. Every sentence is phrased so Codex behavior is preserved
# while WorkBuddy behavior is documented.
PLATFORM_TEMPLATE = """## Platform Compatibility

This skill is written to run in both OpenAI Codex and WorkBuddy.

- **Codex**: user-level skills live under `$CODEX_HOME/skills` or `~/.codex/skills`; the agent interface is `agents/openai.yaml`; Codex uses `metadata.triggering` and the `${name}` invocation syntax, and Codex-specific artifacts include `agents/` and `extensions.yaml`.
- **WorkBuddy**: user-level skills live under `~/.workbuddy/skills` and project-level skills under `<workspace>/.workbuddy/skills`; WorkBuddy reads `SKILL.md` directly, triggers automatically from the `description` field, and ignores `agents/openai.yaml`. No `$`-prefix is needed.

When copying this skill to WorkBuddy, treat `SKILL.md` as the required file and copy `agents/`/`extensions.yaml` only when they exist.
"""

EN_CODEX_NOTE = "In OpenAI Codex you can also invoke the skill explicitly with `{name}`.".format
ZH_CODEX_NOTE = "在 OpenAI Codex 中也可以显式用 `{name}` 调用本 Skill。".format


def parse_name(skill_dir: Path) -> str:
    """Return the Skill name from SKILL.md frontmatter, else the directory name."""
    skill_file = skill_dir / "SKILL.md"
    if skill_file.is_file():
        text = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\n.*?^name:\s*[\"']?(.+?)[\"']?\s*$", text, flags=re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
    return skill_dir.name


def is_allowed_codex_line(line: str, name: str) -> bool:
    """A `$name` mention is allowed only inside an explicit OpenAI Codex note."""
    if re.search(r"\$\s*" + re.escape(name) + r"\b", line) is None:
        return True
    low = line.lower()
    return "codex" in low and ("invoke" in low or "调用" in line)


def section_lines(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Return (start, end) index of the named section; end is the next heading."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def readme_issues(section: list[str], name: str) -> list[tuple[int, str]]:
    """Find unqualified `$name` usages inside a README example section."""
    issues: list[tuple[int, str]] = []
    in_code = False
    for idx, line in enumerate(section):
        if re.match(r"^\s*`{3,}", line):
            in_code = not in_code
            continue
        if re.search(r"\$\s*" + re.escape(name) + r"\b", line) is None:
            continue
        if in_code:
            issues.append((idx + 1, "code block teaches the Codex `$<skill>` invocation"))
        elif not is_allowed_codex_line(line, name):
            issues.append((idx + 1, "prose teaches the Codex `$<skill>` invocation without a Codex qualifier"))
    return issues


def check_skill(skill_dir: Path) -> list[str]:
    """Return human-readable issues for one Skill (empty means compatible)."""
    issues: list[str] = []
    name = parse_name(skill_dir)
    relative = skill_dir.relative_to(ROOT)

    skill_file = skill_dir / "SKILL.md"
    if not re.search(r"^" + re.escape(PLATFORM_HEADING) + r"\s*$",
                     skill_file.read_text(encoding="utf-8"), flags=re.MULTILINE):
        issues.append(f"{relative}/SKILL.md is missing a `{PLATFORM_HEADING}` section")

    for readme_name, heading in ((skill_dir / "README.md", EN_SECTION),
                                 (skill_dir / "README.zh-CN.md", ZH_SECTION)):
        if not readme_name.is_file():
            continue
        lines = readme_name.read_text(encoding="utf-8").splitlines()
        bounds = section_lines(lines, heading)
        if bounds is None:
            continue
        for lineno, reason in readme_issues(lines[bounds[0]:bounds[1]], name):
            issues.append(f"{readme_name.relative_to(ROOT)}:{bounds[0] + lineno} {reason}")
    return issues


def inject_platform_section(skill_dir: Path) -> bool:
    """Insert the Platform Compatibility section into SKILL.md if missing."""
    skill_file = skill_dir / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    if re.search(r"^" + re.escape(PLATFORM_HEADING) + r"\s*$", text, flags=re.MULTILINE):
        return False
    name = parse_name(skill_dir)
    section = PLATFORM_TEMPLATE.format(name=name)
    lines = text.splitlines(keepends=True)
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_at = i
            break
    lines.insert(insert_at, "\n" + section + "\n")
    skill_file.write_text("".join(lines), encoding="utf-8")
    return True


def fix_readme(readme_path: Path, name: str, heading: str) -> bool:
    """Rewrite a README example section so the gate passes. Returns True if changed."""
    lines = readme_path.read_text(encoding="utf-8").splitlines(keepends=True)
    bounds = section_lines(lines, heading)
    if bounds is None:
        return False
    start, end = bounds
    section = lines[start:end]

    out: list[str] = []
    changed = False
    in_code = False
    open_idx = None
    fence_lang = ""
    block_had_skill = False
    for line in section:
        fence = re.match(r"^(\s*)(`{3,})(.*)$", line)
        if fence:
            if in_code:
                if block_had_skill and fence_lang in ("bash", "sh", "shell"):
                    out[open_idx] = "```text\n"
                in_code = False
                block_had_skill = False
                fence_lang = ""
                open_idx = None
                out.append(line)
                continue
            in_code = True
            open_idx = len(out)
            fence_lang = fence.group(3).strip()
            out.append(line)
            continue
        if in_code:
            if re.match(r"^\s*\$\s*" + re.escape(name) + r"\b", line):
                rest = re.sub(r"^\s*\$\s*" + re.escape(name) + r"\b\s*", "", line).rstrip("\n")
                prompt = ("Use this skill to " + rest.strip() + ".") if rest.strip() else "Use this skill for its workflow."
                out.append(prompt + "\n")
                block_had_skill = True
                changed = True
                continue
            out.append(line)
            continue
        if re.search(r"\$\s*" + re.escape(name) + r"\b", line) and not is_allowed_codex_line(line, name):
            out.append(re.sub(r"\$\s*" + re.escape(name) + r"\b", name, line))
            changed = True
            continue
        out.append(line)

    if not readme_issues(out, name):
        # Already compliant after prose/code fixes; no extra note needed.
        pass
    elif heading == EN_SECTION:
        out.append("\n" + EN_CODEX_NOTE(name=name) + "\n")
        changed = True
    elif heading == ZH_SECTION:
        out.append("\n" + ZH_CODEX_NOTE(name=name) + "\n")
        changed = True

    if changed:
        lines[start:end] = out
        readme_path.write_text("".join(lines), encoding="utf-8")
    return changed


def fix_skill(skill_dir: Path) -> bool:
    name = parse_name(skill_dir)
    changed = inject_platform_section(skill_dir)
    for readme_path, heading in ((skill_dir / "README.md", EN_SECTION),
                                 (skill_dir / "README.zh-CN.md", ZH_SECTION)):
        if readme_path.is_file() and section_lines(
                readme_path.read_text(encoding="utf-8").splitlines(), heading) is not None:
            changed = fix_readme(readme_path, name, heading) or changed
    return changed


def iter_skills() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report compatibility gaps and exit non-zero on any")
    mode.add_argument("--fix", action="store_true", help="idempotently inject sections and rewrite README examples")
    parser.add_argument("--skill", metavar="DIR", help="check/fix a single Skill directory instead of all")
    args = parser.parse_args()

    targets = [Path(args.skill).resolve()] if args.skill else iter_skills()
    failures: list[tuple[Path, list[str]]] = []
    for skill_dir in targets:
        if not SKILL_NAME_RE.fullmatch(skill_dir.name):
            continue
        if args.fix:
            fix_skill(skill_dir)
        issues = check_skill(skill_dir)
        if issues:
            failures.append((skill_dir, issues))

    if failures:
        for skill_dir, issues in failures:
            rel = skill_dir.relative_to(ROOT)
            print(f"FAIL: {rel}", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
                print(f"::error file={rel}/SKILL.md::{issue}", file=sys.stderr)
        if args.fix:
            print("Fixed where possible; re-run --check to confirm.", file=sys.stderr)
        return 1

    verb = "checked" if args.check else "fixed and verified"
    print(f"PASS: all Skills are WorkBuddy-compatible ({verb})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
