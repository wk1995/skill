#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_DIR="$ROOT/skills/release-engineering"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[[ -f "$SKILL_DIR/SKILL.md" ]] || fail "missing SKILL.md"
[[ -f "$SKILL_DIR/agents/openai.yaml" ]] || fail "missing agents/openai.yaml"

name="$(sed -n 's/^name: //p' "$SKILL_DIR/SKILL.md" | head -n 1)"
version="$(sed -n 's/^  version: "\([^"]*\)"/\1/p' "$SKILL_DIR/SKILL.md" | head -n 1)"
[[ "$name" == "release-engineering" ]] || fail "unexpected name: $name"
[[ "$version" == "1.0.0" ]] || fail "unexpected version: $version"

references=(
  android-app-release.md
  android-component-release.md
  enter-flowtime-release.md
  gradle-plugin-release.md
  paired-android-submodule-release.md
  release-model.md
)

for reference in "${references[@]}"; do
  [[ -f "$SKILL_DIR/references/$reference" ]] || fail "missing reference: $reference"
done

reference_count="$(find "$SKILL_DIR/references" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
[[ "$reference_count" == "6" ]] || fail "expected 6 references, found $reference_count"

if rg -n 'release-publishing|Release Publishing' "$SKILL_DIR"; then
  fail "old Skill name remains"
fi

printf 'PASS: release-engineering content contract\n'
