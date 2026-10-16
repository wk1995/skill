#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_DIR="$ROOT/skills/build-pipeline-engineering"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[[ -f "$SKILL_DIR/SKILL.md" ]] || fail "missing SKILL.md"
[[ -f "$SKILL_DIR/agent-builds/codex/agents/openai.yaml" ]] || fail "missing Codex agent-build override"

name="$(sed -n 's/^name: //p' "$SKILL_DIR/SKILL.md" | head -n 1)"
version="$(sed -n 's/^  version: "\([^"]*\)"/\1/p' "$SKILL_DIR/SKILL.md" | head -n 1)"
[[ "$name" == "build-pipeline-engineering" ]] || fail "unexpected name: $name"
[[ "$version" == "2.1.0" ]] || fail "unexpected version: $version"

references=(
  android-app-build.md
  android-component-build.md
  enter-flowtime-build.md
  gradle-plugin-build.md
  paired-android-submodule-build.md
  build-pipeline-model.md
  windows-app-build.md
  linux-app-build.md
)

for reference in "${references[@]}"; do
  [[ -f "$SKILL_DIR/references/$reference" ]] || fail "missing reference: $reference"
done

reference_count="$(find "$SKILL_DIR/references" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
[[ "$reference_count" == "${#references[@]}" ]] || fail "expected ${#references[@]} references, found $reference_count"

if grep -R -n -E 'release-publishing|Release Publishing|artifact-build-engineering|Artifact Build Engineering|release-build-engineering|Release Build Engineering' "$SKILL_DIR"; then
  fail "old Skill name remains"
fi

LINK_SCRIPT="$ROOT/scripts/link-build-pipeline-engineering.sh"
[[ -x "$LINK_SCRIPT" ]] || fail "link script is missing or not executable"

tmp="$(mktemp -d)"
probe="$SKILL_DIR/.build-pipeline-engineering-sync-probe.$$"
cleanup() {
  rm -rf "$tmp"
  rm -f "$probe"
}
trap cleanup EXIT

first_home="$tmp/first-home"
CODEX_HOME="$first_home" "$LINK_SCRIPT"
target="$first_home/skills/build-pipeline-engineering"
[[ -L "$target" ]] || fail "target is not a symbolic link"

source_real="$(cd -- "$first_home/.agent-builds/personal-skills-build-pipeline-engineering/skills/build-pipeline-engineering" && pwd -P)"
target_real="$(cd -- "$target" && pwd -P)"
[[ "$target_real" == "$source_real" ]] || fail "link resolves to $target_real"
[[ -f "$target/agents/openai.yaml" ]] || fail "Codex metadata was not materialized"
[[ ! -e "$target/agent-builds" ]] || fail "source-only agent-builds leaked into installed output"
grep -Fq '## Codex Build Adaptation' "$target/SKILL.md" || fail "Codex instructions were not appended"
for reference in "${references[@]}"; do
  cmp "$SKILL_DIR/references/$reference" "$target/references/$reference" || fail "packaged reference differs: $reference"
done

CODEX_HOME="$first_home" "$LINK_SCRIPT"

printf 'from-local-link\n' > "$target/.build-pipeline-engineering-sync-probe.$$"
[[ ! -e "$probe" ]] || fail "generated installation wrote through to portable source"
CODEX_HOME="$first_home" "$LINK_SCRIPT"
[[ ! -e "$target/.build-pipeline-engineering-sync-probe.$$" ]] || fail "rebuild did not replace modified generated content"

conflict_home="$tmp/conflict-home"
mkdir -p "$conflict_home/skills"
printf 'do not overwrite\n' > "$conflict_home/skills/build-pipeline-engineering"
if CODEX_HOME="$conflict_home" "$LINK_SCRIPT" >/dev/null 2>&1; then
  fail "link script accepted a conflicting file"
fi
[[ "$(cat "$conflict_home/skills/build-pipeline-engineering")" == "do not overwrite" ]] || fail "conflicting file was changed"

wrong_home="$tmp/wrong-home"
mkdir -p "$wrong_home/skills" "$tmp/wrong-target"
ln -s "$tmp/wrong-target" "$wrong_home/skills/build-pipeline-engineering"
if CODEX_HOME="$wrong_home" "$LINK_SCRIPT" >/dev/null 2>&1; then
  fail "link script accepted a conflicting symbolic link"
fi
[[ "$(readlink "$wrong_home/skills/build-pipeline-engineering")" == "$tmp/wrong-target" ]] || fail "conflicting symbolic link was changed"

printf 'PASS: build-pipeline-engineering content and link contracts\n'
