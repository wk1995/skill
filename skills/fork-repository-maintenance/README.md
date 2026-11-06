# Fork Repository Maintenance

Language: **English** | [简体中文](README.zh-CN.md)

Fork Repository Maintenance creates selected-branch forks, manually synchronizes same-name source branches without changing an independent personal default branch, integrates personal features separately, and preserves or restores verified Git bundle snapshots.

## How To Use It

Ask for outcomes such as:

- “Fork A's main and release/5 into B, and create personal-main as my independent default.”
- “Synchronize all existing corresponding source branches, without importing new upstream branches.”
- “Import upstream's new develop branch, keeping my personal default unchanged.”
- “Upgrade my personal version from upstream 5 to 7 while preserving feature X.”
- “Preserve this fork, then restore it offline into a new directory.”

Requires Python 3.11+, Git 2.45+ and macOS/Linux. GitHub.com operations also require the authenticated `gh` CLI and suitable permissions. No live GitHub writes have been certified in this release; isolated real-Git repositories and controlled API fixtures provide the implementation evidence. Other Git hosting providers and native Windows writes are not supported.

Use the script in this Skill's `scripts/` directory. Plans and runtime state belong outside source trees. Commands below illustrate a GitHub workflow; replace the repositories and paths with the user's authorized targets:

```bash
python3 scripts/fork_maintenance.py fork \
  --source acme/project --destination my-account/project \
  --scope selected --branch main --branch release/5 \
  --default-name personal-main --checkout /absolute/new-checkout \
  --dry-run --refresh --save-plan /absolute/fork-plan.json

python3 scripts/fork_maintenance.py fork \
  --plan /absolute/fork-plan.json --approve-plan <approval_digest>
```

`--refresh` explicitly prepares owned local Git objects; it does not update B. Without refresh, planning uses already prepared objects and fails clearly if history is unavailable. A dry-run never writes remote refs; combining it with `--refresh` permits only that disclosed local preparation. Save-plan outputs are exclusive and cannot replace existing files.

The successful fork result returns a `profile_id`. Use it for subsequent operations:

```bash
python3 scripts/fork_maintenance.py plan-sync \
  --profile <profile_id> --scope all --new-branches existing-only \
  --refresh --save-plan /absolute/sync-plan.json

python3 scripts/fork_maintenance.py sync \
  --plan /absolute/sync-plan.json --approve-plan <approval_digest>
```

Scope is `single` with one `--branch`, `selected` with an explicit list, or `all` with no branch arguments. `existing-only` is the default; `include-new` may create selected upstream branches only when names are unoccupied. “All” never includes the personal default or personal feature branches. Default-branch names must differ from copied source names; when the upstream default is omitted, provide `--default-base` from the selected branches.

Preservation and offline recovery:

```bash
python3 scripts/fork_maintenance.py preserve \
  --profile <profile_id> --snapshot-scope both --include-tags \
  --archive-root /absolute/owned-archive \
  --dry-run --refresh --save-plan /absolute/preserve-plan.json

python3 scripts/fork_maintenance.py preserve \
  --plan /absolute/preserve-plan.json --approve-plan <approval_digest>

python3 scripts/fork_maintenance.py restore \
  --snapshot /absolute/owned-archive/<snapshot_id> \
  --destination-path /absolute/new-restored-directory \
  --dry-run --save-plan /absolute/restore-plan.json
```

Apply the restore plan with `restore --plan ... --approve-plan ...`. A B restoration requires that the snapshot include B's personal default. A-only snapshots remain valid archives but cannot restore B's omitted personal code. Restores require a nonexistent target path, never overwrite existing directories, and do not contact the remote repositories. Git objects and refs are verified independently; LFS payloads, submodule repositories, uncommitted work, credentials and platform attachments are excluded and reported. `git_complete` does not mean `project_complete`.

Personal integration uses `integrate --profile ... --source-name main --target personal-main --strategy merge --dry-run --refresh`, with one or more `--validation '["program", "argument"]'` commands, then applies the saved plan. Merge/cherry-pick leave a reviewed candidate to be committed under repository policy; resolve/continue and commit there, then `resume --operation <id> --approve-plan <digest>`. Linear rebase requires `--base-oid` and a different, unoccupied `--result-branch`; it never rewrites the published default. Candidates without approved validation stay unverified and are not published.

Read [the runtime contract](references/runtime-contract.md) for results, state layout and exact limitations, [the branch model](references/branch-model.md) for roles, and [recovery](references/recovery.md) for partial/uncertain operations. Detailed agent procedure is in [SKILL.md](SKILL.md).

## When It Triggers

Fork initialization/adoption with selected source branches and an independent personal default; explicit manual source synchronization; separate personal-version integration; Git history preservation, inventory and offline restoration.

## When It Does Not Trigger

Ordinary Git commits, rebases or PRs without this managed-fork lifecycle; release orchestration; Agent Skill-copy synchronization; automatic scheduled source synchronization; propagation of upstream deletions or destructive replacement of diverged shared history.
