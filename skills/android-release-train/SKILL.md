---
name: android-release-train
description: Orchestrate Android feature branches, version-train integration, release branches, signed Android release artifacts, configurable distribution destinations, and release tags. Use when a user asks to create an Android feature branch for a requirement, list feature-branch or PR readiness, select features for a version, create or promote dev/<version> and release/<version> branches, bootstrap Android CI/release workflows, distribute an Android release through Google Play, another store, enterprise MDM, direct delivery, or an artifact archive, or tag a released Android version.
when_to_use: Use when asked to create or assess an Android feature branch, list feature-branch or PR readiness, select features for a version train, create or promote dev/<version> or release/<version> branches, bootstrap Android release CI, distribute or tag a signed Android release. Not for general Android build, test, or code-change tasks, or for managing Skill copies.
metadata:
  version: "1.2.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/android-release-train
  triggering:
    include:
      - The user asks to create, assess, integrate, promote, publish, or tag an Android version train.
      - The task involves Android feature or bugfix branches, dev/<version> or release/<version> branches, signed AAB/APK artifacts, configurable distribution destinations, or release tags.
      - The user needs Android release-train CI, release configuration, branch gates, or a readiness inventory.
    exclude:
      - The request is a general Android build, test, or code-change task without version-train or release orchestration.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Android Version Train

Use this skill to implement and operate a protected Android release train:

`feature/*` / `bugfix/*` → `dev/B` → `release/B` → default branch → `vB`

The default branch is repository configuration, not a hard-coded `main` or `master` name. Resolve it before every operation.

## Platform Compatibility

This skill works in both OpenAI Codex and ZCode.

- **Codex**: triggered by `metadata.triggering` and the `$android-release-train` invocation; the agent interface is `agents/openai.yaml`.
- **ZCode**: triggered automatically from the top-level `name`, `description`, and `when_to_use` in `SKILL.md` — no `$`-prefix or slash command is required. ZCode parses only top-level frontmatter keys, so the nested `metadata.*` rules are ignored, and `agents/openai.yaml` is ignored as well. Install the skill under `~/.zcode/skills/` or `~/.agents/skills/` with `scripts/link-zcode-skill.sh` from this repository.

## Prerequisites

- Read `references/contract.md` before a mutating release action.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App for automated branch creation, PRs, merging, and tags. Do not substitute `GITHUB_TOKEN`: its push/PR events do not retrigger ordinary workflows.
- Keep signing secrets only in a protected GitHub Environment. Never put credentials, tokens, or keystores in the repository or command output.
- Use `assets/release-train.yml` as the repository configuration template when bootstrapping a project.

## Operation Routing

### Bootstrap or repair automation

When asked to create release automation, inspect the Android module, version source, existing workflows, default branch, branch protection, artifact format, and distribution destination first. Configure Google Play, another store, enterprise MDM, direct delivery, or artifact-only delivery only when the repository uses it. Create or update the repository configuration and these workflows:

1. CI: run on PR and push to `feature/**`, `bugfix/**`, `dev/**`, `release/**`, and the default branch. Run branch-appropriate lint, unit tests, and builds.
2. Train orchestration: GitHub App creates `dev/B`, creates selected feature-to-dev PRs, creates the sole `dev/B -> release/B` promotion PR, and creates `vB` only after release success.
3. Release archive/distribution: accept only the tip of a protected `release/B`; read versions from source; build, sign, verify, and archive one configured release artifact (`.aab` or `.apk`), then distribute or promote that same immutable artifact. Do not rebuild between destinations.

Treat destination credentials or access approvals, GitHub App ID/private key, Environment protection, Rulesets, and required reviewers as external prerequisites. Report missing prerequisites rather than pretending the workflow is production-ready.

### Implement a requirement

Resolve the default branch and create `feature/<ticket-or-slug>` from it. Keep `VERSION_NAME` and `VERSION_CODE` unchanged. Build, test, and push the requested feature, but do not open a PR yet unless the user explicitly names an existing `dev/B` train. A feature branch without a PR is awaiting version selection; never target the default branch directly from a feature branch in this release-train workflow and never silently create a `dev/B`. If the user names a non-existent train, report that the version must be explicitly selected before a PR can be created.

### List feature status or choose a release scope

Run the bundled read-only inventory first:

```bash
python3 scripts/release_train.py inventory --format table
python3 scripts/release_train.py select --version 1.4.0 --branches feature/login,feature/report
```

Feature branches do not need a PR before scope selection. The `select` command validates the explicit branch list and rejects PRs targeting another train; then create `dev/B` and the feature-to-dev PRs. Interpret **ready** narrowly after those PRs exist: the branch has an open, non-draft PR targeting `dev/B`, all reported checks succeeded, and GitHub reports `APPROVED`. A PR targeting any other branch is **misrouted** and cannot be included until it is closed or retargeted. **Ready** means “eligible for integration,” not that product or QA has accepted the feature. Show branches with their PR target, review state, check state, and URL. Do not infer business completion from a branch name.

For an explicit request such as “put feature/login and feature/report on version 1.4.0,” show the validated selection and exact remote writes in commentary, then create the protected `dev/1.4.0` from the default branch and PR each selected feature into it through the GitHub App. Require all feature-to-dev PRs to be **ready** and all integration checks to pass before merging.

### Promote and publish a version

Only start promotion after every selected feature PR is merged into `dev/B` and `dev/B` regression checks are green. Then:

1. Create `release/B` from the default branch and create the unique `dev/B -> release/B` PR through the GitHub App.
2. In that protected release flow, write `VERSION_NAME=B` and allocate `VERSION_CODE` from the configured registry. Verify it is higher than every published build.
3. Delete `dev/B` only after the promotion PR has merged and `release/B` contains every selected commit.
4. Accept only release fixes on `release/B`. Build and sign one configured release artifact; archive it; distribute it to the configured test destination when applicable; run QA; then promote or deliver that exact artifact to the configured release destination. For direct or artifact-only delivery, record the immutable archive and its recipient/approval evidence instead of inventing a track promotion.
5. On confirmed publication, merge the release branch into the default branch, tag the exact published commit as `vB`, verify tag/artifact linkage, then delete `release/B`.

Never tag before the configured success point. If publication, artifact verification, branch sync, or tag verification fails, stop and preserve `release/B` for repair.

## Remote-Write Gates

The user naming a feature or version authorizes planning, not accidental publication. Before a remote mutation, state the target repo, default branch, source/target branches, selected features, version, intended artifact destination, and whether the operation will create branches, PRs, merge, publish, tag, or delete branches.

Use the repository's existing release scripts/workflows if present. For GitHub changes, apply the account-safety guard (in OpenAI Codex this is the `git-account-safety` skill; in ZCode, verify the CLI git identity before any remote write and confirm PR/tag outcomes afterwards). Never force-push, bypass branch protection, alter Rulesets, delete a branch before its stated gate, or use a personal token where a GitHub App is required.

## Resources

- `scripts/release_train.py`: read-only branch/PR/check inventory and selection validation.
- `assets/release-train.yml`: copy and tailor as the per-repository contract before bootstrapping workflows.
- `references/contract.md`: branch, version, artifact, and failure-state rules.
