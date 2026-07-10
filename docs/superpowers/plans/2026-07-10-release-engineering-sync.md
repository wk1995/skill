# Release Engineering Skill Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the local `release-publishing` Skill to `release-engineering`, store version `1.0.0` in this repository, and make the local Codex path an immediate two-way view of the tracked repository files.

**Architecture:** The repository directory `skills/release-engineering` is the only physical copy and Git source of truth. A safe idempotent shell script links `${CODEX_HOME:-$HOME/.codex}/skills/release-engineering` to that directory and refuses to overwrite conflicts; the current local directory is preserved outside discovery as a migration backup.

**Tech Stack:** Agent Skills Markdown/YAML, POSIX-oriented Bash on macOS, symbolic links, shell contract tests, Git.

## Global Constraints

- The Skill name is exactly `release-engineering` and the display name is exactly `Release Engineering`.
- The Skill version is exactly `1.0.0` and lives at `SKILL.md` frontmatter path `metadata.version`.
- The repository stores the real files at `skills/release-engineering`; the local Codex path is a symbolic link to that directory.
- The old `~/.codex/skills/release-publishing` discovery path must not remain after successful migration.
- Unknown files, directories, and symbolic links must never be overwritten.
- Tests use a temporary `CODEX_HOME`; only the final activation may change the real `~/.codex/skills` directory.
- Do not push, tag, publish, create a PR, or mutate any remote state.
- Every Git commit message must start with `[codex]`.

---

### Task 1: Import and rename the Skill with a content contract

**Files:**
- Create: `tests/release-engineering-sync.sh`
- Create: `skills/release-engineering/SKILL.md`
- Create: `skills/release-engineering/agents/openai.yaml`
- Create: `skills/release-engineering/references/android-app-release.md`
- Create: `skills/release-engineering/references/android-component-release.md`
- Create: `skills/release-engineering/references/enter-flowtime-release.md`
- Create: `skills/release-engineering/references/gradle-plugin-release.md`
- Create: `skills/release-engineering/references/paired-android-submodule-release.md`
- Create: `skills/release-engineering/references/release-model.md`

**Interfaces:**
- Consumes: the current files under `/Users/chengpeng/.codex/skills/release-publishing`.
- Produces: `skills/release-engineering` with `name: release-engineering`, `metadata.version: "1.0.0"`, and unchanged reference content.

- [ ] **Step 1: Write the failing content-contract test**

Create `tests/release-engineering-sync.sh` with:

```bash
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
```

Make it executable:

```bash
chmod +x tests/release-engineering-sync.sh
```

- [ ] **Step 2: Run the test and verify it fails before import**

Run:

```bash
tests/release-engineering-sync.sh
```

Expected: exit code `1` with `FAIL: missing SKILL.md`.

- [ ] **Step 3: Copy the current Skill into the tracked source directory**

Run:

```bash
mkdir -p skills/release-engineering
cp -R /Users/chengpeng/.codex/skills/release-publishing/. skills/release-engineering/
```

Then update `skills/release-engineering/SKILL.md` frontmatter and title to:

```yaml
---
name: release-engineering
description: Use when planning, validating, automating, documenting, or troubleshooting release/publish/发布/发包 workflows for Android apps, Android libraries/components, Gradle plugins, publish branches, tags, artifacts, CI gates, or when extending release workflows beyond Android.
metadata:
  version: "1.0.0"
---

# Release Engineering
```

Retain all content below the title unchanged. Update `skills/release-engineering/agents/openai.yaml` to:

```yaml
interface:
  display_name: "Release Engineering"
  short_description: "Guide app, component, and plugin releases"
  default_prompt: "Use $release-engineering to prepare an Android app release plan for this repository."
```

- [ ] **Step 4: Verify imported references are byte-identical and the content contract passes**

Run:

```bash
diff -ru /Users/chengpeng/.codex/skills/release-publishing/references skills/release-engineering/references
tests/release-engineering-sync.sh
git diff --check
```

Expected: `diff` and `git diff --check` have no output; the test prints `PASS: release-engineering content contract`.

- [ ] **Step 5: Commit the imported Skill**

Run:

```bash
git status --short --branch
git config user.name
git config user.email
git add tests/release-engineering-sync.sh skills/release-engineering
git diff --cached --check
git commit -m "[codex] feat: add release engineering skill"
```

Expected: one commit containing the renamed versioned Skill and its content-contract test.

---

### Task 2: Add the safe, idempotent Codex link command

**Files:**
- Create: `scripts/link-codex-skill.sh`
- Modify: `tests/release-engineering-sync.sh`

**Interfaces:**
- Consumes: repository source directory `skills/release-engineering` and optional environment variable `CODEX_HOME`.
- Produces: `${CODEX_HOME:-$HOME/.codex}/skills/release-engineering` as a symbolic link to the repository source; exits `0` if already correct and non-zero without mutation on conflicts.

- [ ] **Step 1: Extend the test with link, idempotency, two-way visibility, and conflict cases**

Append to `tests/release-engineering-sync.sh` before its final PASS output, moving the existing PASS output to the end:

```bash
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
```

- [ ] **Step 2: Run the expanded test and verify the missing link script fails**

Run:

```bash
tests/release-engineering-sync.sh
```

Expected: exit code `1` with `FAIL: link script is missing or not executable`.

- [ ] **Step 3: Implement the minimal safe link script**

Create `scripts/link-codex-skill.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
SOURCE="$REPO_ROOT/skills/release-engineering"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
SKILLS_DIR="$CODEX_ROOT/skills"
TARGET="$SKILLS_DIR/release-engineering"

if [[ ! -f "$SOURCE/SKILL.md" ]]; then
  printf 'Source Skill is missing: %s\n' "$SOURCE" >&2
  exit 1
fi

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
```

Make it executable:

```bash
chmod +x scripts/link-codex-skill.sh
```

- [ ] **Step 4: Run contract and formatting checks**

Run:

```bash
tests/release-engineering-sync.sh
bash -n scripts/link-codex-skill.sh tests/release-engineering-sync.sh
git diff --check
```

Expected: the contract prints `PASS: release-engineering content and link contracts`; syntax and diff checks produce no errors.

- [ ] **Step 5: Commit the link command**

Run:

```bash
git status --short --branch
git config user.name
git config user.email
git add scripts/link-codex-skill.sh tests/release-engineering-sync.sh
git diff --cached --check
git commit -m "[codex] feat: link release engineering skill to Codex"
```

Expected: one commit containing the safe link script and its contract cases.

---

### Task 3: Activate the link on the real local Codex installation

**Files:**
- Move for backup: `/Users/chengpeng/.codex/skills/release-publishing`
- Create symlink: `/Users/chengpeng/.codex/skills/release-engineering`

**Interfaces:**
- Consumes: the verified repository Skill, the old local Skill directory, and `scripts/link-codex-skill.sh`.
- Produces: a real local Codex Skill link plus a non-discovered migration backup under `/Users/chengpeng/.codex/skill-backups`.

- [ ] **Step 1: Run migration preflight without changing the real local directory**

Run:

```bash
test -d /Users/chengpeng/.codex/skills/release-publishing
test ! -e /Users/chengpeng/.codex/skills/release-engineering
test ! -L /Users/chengpeng/.codex/skills/release-engineering
diff -ru /Users/chengpeng/.codex/skills/release-publishing/references skills/release-engineering/references
tests/release-engineering-sync.sh
```

Expected: exit code `0`; no destination conflict and no reference differences.

- [ ] **Step 2: Move the old directory to a safe non-discovered backup and create the real link**

Run as one guarded shell block:

```bash
set -euo pipefail
old=/Users/chengpeng/.codex/skills/release-publishing
backup_root=/Users/chengpeng/.codex/skill-backups
backup="$backup_root/release-publishing-before-release-engineering-20260710"

if [[ -e "$backup" ]]; then
  printf 'Backup path already exists: %s\n' "$backup" >&2
  exit 1
fi

mkdir -p "$backup_root"
mv "$old" "$backup"
if ! /Users/chengpeng/project/wk/skill/scripts/link-codex-skill.sh; then
  mv "$backup" "$old"
  exit 1
fi
```

Expected: old discovery path is absent, backup exists, and the new local path is linked.

- [ ] **Step 3: Verify real two-way visibility with a temporary probe**

Run:

```bash
set -euo pipefail
repo=/Users/chengpeng/project/wk/skill/skills/release-engineering
local=/Users/chengpeng/.codex/skills/release-engineering
probe=.release-engineering-real-sync-probe
trap 'rm -f "$repo/$probe"' EXIT

test -L "$local"
test "$(cd "$repo" && pwd -P)" = "$(cd "$local" && pwd -P)"
printf 'from-repository\n' > "$repo/$probe"
test "$(cat "$local/$probe")" = "from-repository"
printf 'from-local\n' > "$local/$probe"
test "$(cat "$repo/$probe")" = "from-local"
rm -f "$repo/$probe"
trap - EXIT
test ! -e /Users/chengpeng/.codex/skills/release-publishing
```

Expected: exit code `0`; writes through either path are immediately visible from the other.

- [ ] **Step 4: Run final repository and local-state verification**

Run:

```bash
tests/release-engineering-sync.sh
bash -n scripts/link-codex-skill.sh tests/release-engineering-sync.sh
rg -n 'release-publishing|Release Publishing' skills/release-engineering && exit 1 || true
git diff --check
git status --short --branch
readlink /Users/chengpeng/.codex/skills/release-engineering
```

Expected: all tests pass, there are no old-name matches inside the Skill, no probe remains, and the local link points to `/Users/chengpeng/project/wk/skill/skills/release-engineering`.
