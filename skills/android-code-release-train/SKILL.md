---
name: android-code-release-train
description: Orchestrate Android source code from a requirement branch through version-train integration, release promotion, default-branch synchronization, and an immutable source tag. Use for feature/bugfix branches, versioned dev and release PRs, code-readiness gates, version metadata, or source-release tags; do not use for APK/AAB/AAR builds, signing, packaging, or artifact uploads.
metadata:
  sync_id: "android-code-release-train"
  version: "2.0.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/android-code-release-train
  triggering:
    include:
      - The user asks to implement an Android requirement on a feature or bugfix branch and carry its code into a selected version train.
      - The task involves selecting or assessing code for dev/<version>, promoting code to release/<version>, synchronizing the default branch, or creating the source release tag.
      - The user needs Android source-branch orchestration, PR readiness, code gates, or version metadata changes for a release train.
    exclude:
      - The task is to configure or run APK, AAB, AAR, JAR, or plugin packaging builds, signing, checksums, or output uploads; use build-pipeline-engineering instead.
      - The request is an ordinary Android build, test, or code edit without the version-train lifecycle.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Android Code Release Train

Operate this source-only Android lifecycle:

`requirement` -> `feature/*` / `bugfix/*` -> `dev/B` -> `release/B` -> default branch -> `vB`

The output is a reviewed, versioned source commit and immutable tag. This Skill never configures or runs packaging, signing, output verification, or uploads. Use `build-pipeline-engineering` when work starts from a source ref and enters a build pipeline.


## Platform Compatibility

This skill is written to run in both OpenAI Codex and WorkBuddy.

- **Codex**: user-level skills live under `$CODEX_HOME/skills` or `~/.codex/skills`; the agent interface is `agents/openai.yaml`; Codex uses `metadata.triggering` and the `$android-code-release-train` invocation syntax, and Codex-specific artifacts include `agents/` and `extensions.yaml`.
- **WorkBuddy**: WorkBuddy reads `SKILL.md` directly, triggers automatically from the `description` field, and ignores `agents/openai.yaml`. Its installed-Skill directory is product-configured: domestic builds commonly use `~/.workbuddy/skills`, while WorkBuddy AI/overseas builds may use `~/.workbuddy-ai/skills`. Import through WorkBuddy or use the directory configured by the installed product. No `$`-prefix is needed.

When copying this skill to WorkBuddy, treat `SKILL.md` as the required file and copy `agents/`/`extensions.yaml` only when they exist.

## Prerequisites

- Read [references/code-train-contract.md](references/code-train-contract.md) before a mutating train operation.
- Resolve the repository default branch instead of assuming `main` or `master`.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App when automated branch, PR, merge, or tag operations must retrigger workflows. Do not substitute `GITHUB_TOKEN` when its events would not retrigger ordinary workflows.
- Use [assets/code-release-train.yml](assets/code-release-train.yml) as the source-flow configuration template when bootstrapping a repository.

## Operation Routing

### Bootstrap or repair source orchestration

Inspect branch conventions, default branch, version source, required code checks, review policy, Rulesets, and existing workflows. Configure only source-flow automation:

1. Code validation on feature, bugfix, integration, release, and default branches.
2. Train orchestration for `dev/B`, selected feature-to-dev PRs, and the unique `dev/B -> release/B` promotion PR.
3. Source finalization that synchronizes the accepted release commit to the default branch and creates `vB`.

The checks may compile or test code, but this Skill must not configure signing credentials, distributable packaging, artifact upload, store delivery, or artifact retention.

### Implement a requirement

Create `feature/<ticket-or-slug>` or `bugfix/<ticket-or-slug>` from the resolved default branch. Keep release version metadata unchanged while implementing the requirement. Build or test only as code validation; do not retain or distribute the outputs as release artifacts.

Do not open a PR until the user explicitly selects an existing `dev/B` train. Never target the default branch directly from a requirement branch and never silently create a train. If the named train does not exist, report that the version scope must be selected first.

### Inventory and select a version scope

Run the bundled read-only inventory and selection validation:

```bash
python3 scripts/code_release_train.py inventory --format table
python3 scripts/code_release_train.py select --version 1.4.0 --branches feature/login,feature/report
```

After selection, create `dev/B` and the feature-to-dev PRs through the configured automation identity. A branch is **ready** only when its PR is open, non-draft, targets `dev/B`, has approval, and all reported code checks succeed. A PR targeting another branch is **misrouted**. Ready means eligible for code integration, not product acceptance and not artifact readiness.

### Promote and finalize source code

Only promote after all selected requirement PRs are merged into `dev/B` and integration code checks pass:

1. Create `release/B` from the default branch and the unique `dev/B -> release/B` PR.
2. Update the repository-owned version metadata in that protected release flow and validate it against repository policy.
3. Delete `dev/B` only after promotion is merged and `release/B` contains every selected commit.
4. Accept only release fixes on `release/B`; require the configured source review and code gates.
5. Merge the accepted release source into the default branch, tag that exact commit as `vB`, verify the tag, then delete `release/B`.

Source release success is the verified default-branch commit and tag. Artifact build success is deliberately outside this contract; downstream artifact automation may consume the tag without moving or replacing it.

## Remote-Write Gates

Before a remote mutation, state the repository, default branch, source and target branches, selected requirements, version, and whether the operation creates branches, PRs, merges, tags, or deletes branches.

Follow `git-account-safety` for GitHub operations. Never force-push, bypass branch protection, alter Rulesets without an explicit request, delete a branch before its gate, or create/replace tags from the artifact workflow.

## Resources

- [scripts/code_release_train.py](scripts/code_release_train.py): read-only feature-branch, PR, and code-check inventory.
- [assets/code-release-train.yml](assets/code-release-train.yml): per-repository source-flow configuration template.
- [references/code-train-contract.md](references/code-train-contract.md): source states, invariants, and failure rules.
