#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
python3 -B -m unittest discover -s "$ROOT/skills/email-management/tests" -p 'test_*.py' -v

if [[ "${1:-}" == "--artifacts" ]]; then
    python3 -B - "$ROOT" <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
skill_source = root / "skills/email-management"
report = skill_source / "doc/test-results/2026-11-10-readonly-smoke/report.zh-CN.md"
for name in ("README.md", "README.zh-CN.md", "references/feishu.md"):
    guide = skill_source / name
    link = os.path.relpath(report, guide.parent)
    if not report.is_file() or f"]({link})" not in guide.read_text(encoding="utf-8"):
        raise SystemExit(f"FAIL: {name} must link the published read-only smoke report")
print("PASS: bilingual guides and Feishu reference link the same read-only smoke report")

with tempfile.TemporaryDirectory(prefix="email-skill-build-tests-") as directory:
    fixture = Path(directory).resolve()
    for adapter in sorted((root / "platforms").glob("*/adapter.json")):
        agent = adapter.parent.name
        output = fixture / agent
        subprocess.run(
            [sys.executable, "-B", str(root / "scripts/agent_build.py"), agent,
             "--skill", "email-management", "--output", str(output)],
            check=True,
        )
        manifest = json.loads((output / ".agent-build.json").read_text())
        skill = output / manifest["skills"][0]["path"]
        env = dict(os.environ, PATH="", PYTHONPATH="",
                   EMAIL_ACCOUNTS_SCRIPT=str(skill / "scripts/email_accounts.py"))
        subprocess.run(
            [sys.executable, "-B", "-S", "-m", "unittest", "discover", "-s", str(skill / "tests")],
            cwd=fixture, env=env, check=True,
        )
        print(f"PASS: {agent} email Skill artifact works outside the checkout with empty PATH")
PY
fi
