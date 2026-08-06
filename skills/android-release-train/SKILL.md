---
name: android-release-train
description: Orchestrate Android feature branches, version-train integration, release branches, signed release archives, and release tags. Use when a user asks to create an Android feature branch for a requirement, list feature-branch or PR readiness, select features for a version, create or promote dev/<version> and release/<version> branches, bootstrap Android CI/release workflows, publish an Android release, or tag a published Android version.
metadata:
  version: "1.0.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/android-release-train
  triggering:
    include:
      - The user asks to create, assess, integrate, promote, publish, or tag an Android version train.
      - The task involves Android feature or bugfix branches, dev/<version> or release/<version> branches, AAB signing, Play track promotion, or release tags.
      - The user needs Android release-train CI, release configuration, branch gates, or a readiness inventory.
    exclude:
      - The request is a general Android build, test, or code-change task without version-train or release orchestration.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Android Version Train

Use this skill to implement and operate a protected Android release train:

`feature/*` / `bugfix/*` → `dev/B` → `release/B` → default branch → `vB`

The default branch is repository configuration, not a hard-coded `main` or `master` name. Resolve it before every operation.

## Prerequisites

- Read `references/contract.md` before a mutating release action.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App for automated branch creation, PRs, merging, and tags. Do not substitute `GITHUB_TOKEN`: its push/PR events do not retrigger ordinary workflows.
- Keep signing secrets only in a protected GitHub Environment. Never put credentials, tokens, or keystores in the repository or command output.
- Use `assets/release-train.yml` as the repository configuration template when bootstrapping a project.

## Operation Routing

### Bootstrap or repair automation

When asked to create release automation, inspect the Android module, version source, existing workflows, default branch, branch protection, and Play target first. Create or update the repository configuration and these workflows:

1. CI: run on PR and push to `feature/**`, `bugfix/**`, `dev/**`, `release/**`, and the default branch. Run branch-appropriate lint, unit tests, and builds.
2. Train orchestration: GitHub App creates `dev/B`, creates selected feature-to-dev PRs, creates the sole `dev/B -> release/B` promotion PR, and creates `vB` only after release success.
3. Release archive/publish: accept only the tip of a protected `release/B`; read versions from source; build, sign, verify, archive, then publish/promote the same AAB. Do not rebuild between Play tracks.

Treat Play upload, GitHub App ID/private key, Environment protection, Rulesets, and required reviewers as external prerequisites. Report missing prerequisites rather than pretending the workflow is production-ready.

### Implement a requirement

Resolve the default branch and create `feature/<ticket-or-slug>` from it. Keep `VERSION_NAME` and `VERSION_CODE` unchanged. Build and test the requested feature, push it, and open a PR to the branch requested by the user. If no train is named, target the default branch or ask whether the feature belongs to an active train; never silently create a `dev/B`.

### List feature status or choose a release scope

Run the bundled read-only inventory first:

```bash
python3 scripts/release_train.py inventory --format table
python3 scripts/release_train.py select --version 1.4.0 --branches feature/login,feature/report --require-ready
```

Interpret **ready** narrowly: the branch has an open, non-draft PR, all reported checks succeeded, and GitHub reports `APPROVED`. It means “eligible for integration,” not that product or QA has accepted the feature. Show branches with their PR target, review state, check state, and URL. Do not infer business completion from a branch name.

For an explicit request such as “put feature/login and feature/report on version 1.4.0,” show the validated selection and exact remote writes in commentary, then create the protected `dev/1.4.0` from the default branch and PR each selected feature into it through the GitHub App. Require all integration checks before merging.

### Promote and publish a version

Only start promotion after every selected feature PR is merged into `dev/B` and `dev/B` regression checks are green. Then:

1. Create `release/B` from the default branch and create the unique `dev/B -> release/B` PR through the GitHub App.
2. In that protected release flow, write `VERSION_NAME=B` and allocate `VERSION_CODE` from the configured registry. Verify it is higher than every published build.
3. Delete `dev/B` only after the promotion PR has merged and `release/B` contains every selected commit.
4. Accept only release fixes on `release/B`. Build and sign one AAB; archive it; upload to internal/closed; run QA; promote that exact AAB.
5. On confirmed publication, merge the release branch into the default branch, tag the exact published commit as `vB`, verify tag/artifact linkage, then delete `release/B`.

Never tag before the configured success point. If publication, artifact verification, branch sync, or tag verification fails, stop and preserve `release/B` for repair.

## Remote-Write Gates

The user naming a feature or version authorizes planning, not accidental publication. Before a remote mutation, state the target repo, default branch, source/target branches, selected features, version, intended artifact destination, and whether the operation will create branches, PRs, merge, publish, tag, or delete branches.

Use the repository's existing release scripts/workflows if present. For GitHub changes, follow `git-account-safety`; verify the CLI identity before pushes and verify PR/tag outcomes afterwards. Never force-push, bypass branch protection, alter Rulesets, delete a branch before its stated gate, or use a personal token where a GitHub App is required.

## Resources

- `scripts/release_train.py`: read-only branch/PR/check inventory and selection validation.
- `assets/release-train.yml`: copy and tailor as the per-repository contract before bootstrapping workflows.
- `references/contract.md`: branch, version, artifact, and failure-state rules.
