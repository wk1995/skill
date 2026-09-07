#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
BUILD="$ROOT/scripts/agent_build.py"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

python3 "$BUILD" --check
adapters="$(python3 "$BUILD" --list | cut -f1 | tr '\n' ' ')"
[[ " $adapters" == *" codex "* ]] || fail "Codex adapter was not discovered"
[[ " $adapters" == *" workbuddy "* ]] || fail "WorkBuddy adapter was not discovered"

codex_output="$tmp/codex"
workbuddy_output="$tmp/workbuddy"
python3 "$BUILD" codex --output "$codex_output"
python3 "$BUILD" workbuddy --output "$workbuddy_output"

[[ -f "$codex_output/.codex-plugin/plugin.json" ]] || fail "Codex plugin manifest is missing"
[[ -f "$codex_output/.agent-build.json" ]] || fail "Codex build manifest is missing"
[[ -f "$workbuddy_output/.agent-build.json" ]] || fail "WorkBuddy build manifest is missing"

for skill_dir in "$ROOT"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  skill="$(basename "$skill_dir")"
  [[ -f "$codex_output/skills/$skill/SKILL.md" ]] || fail "Codex did not build $skill"
  [[ -f "$workbuddy_output/$skill/SKILL.md" ]] || fail "WorkBuddy did not build $skill"
  [[ ! -e "$codex_output/skills/$skill/agent-builds" ]] || fail "Codex artifact leaked agent-builds for $skill"
  [[ ! -e "$workbuddy_output/$skill/agent-builds" ]] || fail "WorkBuddy artifact leaked agent-builds for $skill"
  grep -Fq '## Codex Build Adaptation' "$codex_output/skills/$skill/SKILL.md" || fail "Codex adaptation missing for $skill"
  grep -Fq "\$$skill" "$codex_output/skills/$skill/SKILL.md" || fail "Codex invocation was not rendered for $skill"
  grep -Fq '## WorkBuddy Build Adaptation' "$workbuddy_output/$skill/SKILL.md" || fail "WorkBuddy adaptation missing for $skill"
  [[ ! -e "$workbuddy_output/$skill/agents/openai.yaml" ]] || fail "WorkBuddy artifact contains Codex UI metadata for $skill"
done

[[ -f "$codex_output/skills/sync-skills/agents/openai.yaml" ]] || fail "Codex override was not materialized"
grep -Fq '## Codex Sync Adaptation' "$codex_output/skills/sync-skills/SKILL.md" || fail "per-Skill Codex instructions were not appended"
grep -Fq '## WorkBuddy Sync Adaptation' "$workbuddy_output/sync-skills/SKILL.md" || fail "per-Skill WorkBuddy instructions were not appended"
grep -Fq '"adapter_version": "1.0.0"' "$codex_output/.agent-build.json" || fail "adapter version missing from build manifest"
grep -Fq '"artifact_version": "0.1.0"' "$codex_output/.agent-build.json" || fail "artifact version missing from build manifest"

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT/platforms/codex/adapter.json" "$codex_output/.codex-plugin/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

adapter = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
plugin = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert plugin["version"] == adapter["artifact_version"]
assert plugin["skills"] == "./skills/"
print("PASS: Codex plugin manifest matches the adapter artifact version")
PY

PYTHONDONTWRITEBYTECODE=1 python3 - "$BUILD" "$tmp" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

script = Path(sys.argv[1])
fixture_root = Path(sys.argv[2]) / "extension-fixture"
spec = importlib.util.spec_from_file_location("agent_build", script)
assert spec is not None and spec.loader is not None
agent_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_build)

(fixture_root / "platforms" / "new-agent").mkdir(parents=True)
(fixture_root / "skills" / "demo" / "agent-builds").mkdir(parents=True)
(fixture_root / "platforms" / "new-agent" / "adapter.json").write_text(
    json.dumps({
        "schema_version": 1,
        "id": "new-agent",
        "version": "1.0.0",
        "artifact_version": "1.0.0",
        "skills_path": "skills",
        "skill_append": "SKILL.append.md",
    }),
    encoding="utf-8",
)
(fixture_root / "platforms" / "new-agent" / "SKILL.append.md").write_text(
    "## New Agent\n\nBuilt for {{skill_name}} by {{adapter_id}}.\n",
    encoding="utf-8",
)
(fixture_root / "platforms" / "new-agent" / "CHANGELOG.md").write_text(
    "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-09-07\n\n- Initial adapter.\n",
    encoding="utf-8",
)
(fixture_root / "skills" / "demo" / "SKILL.md").write_text(
    """---
name: demo
description: Demonstrate an extensible Agent build.
metadata:
  version: "2.3.4"
---

# Demo
""",
    encoding="utf-8",
)

agent_build.ROOT = fixture_root
agent_build.SKILLS_DIR = fixture_root / "skills"
agent_build.PLATFORMS_DIR = fixture_root / "platforms"
agent_build.DEFAULT_OUTPUT_DIR = fixture_root / "dist"
agent_build.validate_all()
output = agent_build.build("new-agent", [], str(fixture_root / "output"), False)
generated = (output / "skills" / "demo" / "SKILL.md").read_text(encoding="utf-8")
assert "Built for demo by new-agent." in generated
assert not (output / "skills" / "demo" / "agent-builds").exists()
manifest = json.loads((output / ".agent-build.json").read_text(encoding="utf-8"))
assert manifest["skills"][0]["version"] == "2.3.4"
print("PASS: a new Agent is added by one platform directory without builder or Skill changes")
PY

printf 'PASS: declarative Agent builds preserve portable cores and materialize platform overrides\n'
