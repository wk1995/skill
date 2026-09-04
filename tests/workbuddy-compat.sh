#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
COMPAT_SCRIPT="$ROOT/scripts/workbuddy_compat.py"
CATALOG_WORKFLOW="$ROOT/.github/workflows/skill-catalog.yml"

[[ -f "$COMPAT_SCRIPT" ]]
[[ -f "$CATALOG_WORKFLOW" ]]

python3 "$COMPAT_SCRIPT" --check
grep -Eq 'bash tests/workbuddy-compat.sh' "$CATALOG_WORKFLOW"

PYTHONDONTWRITEBYTECODE=1 python3 - "$COMPAT_SCRIPT" <<'PY'
import subprocess
import sys
import tempfile
from pathlib import Path

script = Path(sys.argv[1])


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory() as raw_tmp:
    skill = Path(raw_tmp) / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        """---
name: demo
description: Demonstrate compatibility checks.
metadata:
  version: "0.0.1"
---

# Demo

Run $demo to perform the workflow.
""",
        encoding="utf-8",
    )
    (skill / "README.md").write_text(
        """# Demo

## How To Use It

- Example:
  ```bash
  $demo perform the workflow
  ```

## When It Triggers

Use it for demos.

## When It Does Not Trigger

Do not use it otherwise.
""",
        encoding="utf-8",
    )
    (skill / "README.zh-CN.md").write_text(
        """# Demo

## 如何使用

在 Codex 中用 `$demo` 运行此 Skill。

## 何时触发

用于演示。

## 何时不触发

其他情况不触发。
""",
        encoding="utf-8",
    )

    failed = run("--check", "--skill", str(skill))
    assert failed.returncode == 1, failed.stdout + failed.stderr
    assert "missing a `## Platform Compatibility` section" in failed.stderr
    assert "SKILL.md body teaches" in failed.stderr
    assert "README.md" in failed.stderr
    assert f"::error file={skill.resolve() / 'README.md'},line=" in failed.stderr

    fixed = run("--fix", "--skill", str(skill))
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    assert "  ```text" in (skill / "README.md").read_text(encoding="utf-8")
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert "Run demo to perform the workflow." in skill_text
    assert "Run $demo to perform the workflow." not in skill_text
    assert "$demo" in (skill / "README.zh-CN.md").read_text(encoding="utf-8")

    before = {path.name: path.read_bytes() for path in skill.iterdir() if path.is_file()}
    fixed_again = run("--fix", "--skill", str(skill))
    assert fixed_again.returncode == 0, fixed_again.stdout + fixed_again.stderr
    after = {path.name: path.read_bytes() for path in skill.iterdir() if path.is_file()}
    assert after == before, "--fix must be idempotent"

print("PASS: WorkBuddy compatibility negative, fix, annotation, external-path, and idempotency cases")
PY
