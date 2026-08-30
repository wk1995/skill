#!/usr/bin/env bash
set -euo pipefail

# Link repository Skills into a ZCode discovery root.
#
# Usage:
#   scripts/link-zcode-skill.sh                  # link every Skill
#   scripts/link-zcode-skill.sh <skill-name>...  # link selected Skills
#
# The default destination is ~/.zcode/skills (ZCode user scope). Set
# ZCODE_SKILLS_DIR to link elsewhere, for example ~/.agents/skills to share
# the links across tools that read that directory.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
SKILLS_DIR="${ZCODE_SKILLS_DIR:-$HOME/.zcode/skills}"

link_skill() {
  local name="${1%/}"
  if [[ "$name" == */* ]]; then
    printf 'Invalid Skill name: %s\n' "$1" >&2
    return 1
  fi

  local source="$REPO_ROOT/skills/$name"
  local target="$SKILLS_DIR/$name"

  if [[ ! -f "$source/SKILL.md" ]]; then
    printf 'Source Skill is missing: %s\n' "$source" >&2
    return 1
  fi

  local source_real target_real
  source_real="$(cd -- "$source" && pwd -P)"

  if [[ -L "$target" ]]; then
    if target_real="$(cd -- "$target" 2>/dev/null && pwd -P)" && [[ "$target_real" == "$source_real" ]]; then
      printf 'ZCode Skill link already configured: %s -> %s\n' "$target" "$source_real"
      return 0
    fi

    printf 'Refusing to replace conflicting symbolic link: %s -> %s\n' "$target" "$(readlink "$target")" >&2
    return 1
  fi

  if [[ -e "$target" ]]; then
    printf 'Refusing to replace existing path: %s\n' "$target" >&2
    return 1
  fi

  if ! ln -s "$source_real" "$target"; then
    printf 'Failed to link ZCode Skill: %s\n' "$target" >&2
    return 1
  fi
  printf 'Linked ZCode Skill: %s -> %s\n' "$target" "$source_real"
}

names=()
if [[ $# -gt 0 ]]; then
  names=("$@")
else
  shopt -s nullglob dotglob
  for dir in "$REPO_ROOT"/skills/*/; do
    name="$(basename -- "$dir")"
    if [[ "$name" == .* ]]; then
      continue
    fi
    names+=("$name")
  done
  shopt -u nullglob dotglob
fi

if [[ ${#names[@]} -eq 0 ]]; then
  printf 'No Skills found under %s/skills\n' "$REPO_ROOT" >&2
  exit 1
fi

mkdir -p "$SKILLS_DIR"

failed=0
for name in "${names[@]}"; do
  if ! link_skill "$name"; then
    failed=1
  fi
done

exit "$failed"
