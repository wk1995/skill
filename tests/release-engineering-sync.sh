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

LINK_SCRIPT="$ROOT/scripts/link-codex-skill.sh"
[[ -x "$LINK_SCRIPT" ]] || fail "link script is missing or not executable"

tmp="$(mktemp -d)"
probe="$SKILL_DIR/.release-engineering-sync-probe.$$"
cleanup() {
  rm -rf "$tmp"
  rm -f "$probe"
}
trap cleanup EXIT

first_home="$tmp/first-home"
CODEX_HOME="$first_home" "$LINK_SCRIPT"
target="$first_home/skills/release-engineering"
[[ -L "$target" ]] || fail "target is not a symbolic link"

source_real="$(cd -- "$SKILL_DIR" && pwd -P)"
target_real="$(cd -- "$target" && pwd -P)"
[[ "$target_real" == "$source_real" ]] || fail "link resolves to $target_real"

CODEX_HOME="$first_home" "$LINK_SCRIPT"

printf 'from-local-link\n' > "$target/.release-engineering-sync-probe.$$"
[[ "$(cat "$probe")" == "from-local-link" ]] || fail "local write was not visible in repository source"
printf 'from-repository-source\n' > "$probe"
[[ "$(cat "$target/.release-engineering-sync-probe.$$")" == "from-repository-source" ]] || fail "repository write was not visible through local link"

conflict_home="$tmp/conflict-home"
mkdir -p "$conflict_home/skills"
printf 'do not overwrite\n' > "$conflict_home/skills/release-engineering"
if CODEX_HOME="$conflict_home" "$LINK_SCRIPT" >/dev/null 2>&1; then
  fail "link script accepted a conflicting file"
fi
[[ "$(cat "$conflict_home/skills/release-engineering")" == "do not overwrite" ]] || fail "conflicting file was changed"

wrong_home="$tmp/wrong-home"
mkdir -p "$wrong_home/skills" "$tmp/wrong-target"
ln -s "$tmp/wrong-target" "$wrong_home/skills/release-engineering"
if CODEX_HOME="$wrong_home" "$LINK_SCRIPT" >/dev/null 2>&1; then
  fail "link script accepted a conflicting symbolic link"
fi
[[ "$(readlink "$wrong_home/skills/release-engineering")" == "$tmp/wrong-target" ]] || fail "conflicting symbolic link was changed"

printf 'PASS: release-engineering content and link contracts\n'
