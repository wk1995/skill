#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
BUILD_SCRIPT="$REPO_ROOT/scripts/agent_build.py"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
SKILLS_DIR="$CODEX_ROOT/skills"
TARGET="$SKILLS_DIR/build-pipeline-engineering"
BUILD_ROOT="$CODEX_ROOT/.agent-builds/personal-skills-build-pipeline-engineering"
SOURCE="$BUILD_ROOT/skills/build-pipeline-engineering"

if [[ ! -f "$BUILD_SCRIPT" ]]; then
  printf 'Agent build script is missing: %s\n' "$BUILD_SCRIPT" >&2
  exit 1
fi

python3 "$BUILD_SCRIPT" codex --skill build-pipeline-engineering --output "$BUILD_ROOT" --force

source_real="$(cd -- "$SOURCE" && pwd -P)"

if [[ -L "$TARGET" ]]; then
  if target_real="$(cd -- "$TARGET" 2>/dev/null && pwd -P)" && [[ "$target_real" == "$source_real" ]]; then
    printf 'Codex Skill link already configured: %s -> %s\n' "$TARGET" "$source_real"
    exit 0
  fi

  printf 'Refusing to replace conflicting symbolic link: %s -> %s\n' "$TARGET" "$(readlink "$TARGET")" >&2
  exit 1
fi

if [[ -e "$TARGET" ]]; then
  printf 'Refusing to replace existing path: %s\n' "$TARGET" >&2
  exit 1
fi

mkdir -p "$SKILLS_DIR"
ln -s "$source_real" "$TARGET"
printf 'Linked Codex Skill: %s -> %s\n' "$TARGET" "$source_real"
