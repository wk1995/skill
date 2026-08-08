# Release-train contract

## States

| State | Evidence | Allowed next action |
| --- | --- | --- |
| `development` | Branch has no open PR | Continue development or select it for a version train |
| `misrouted` | Open PR targets a branch other than `dev/B` | Close or retarget the PR before selection/integration |
| `pending` | Open PR targets `dev/B` but is draft, unapproved, or has incomplete checks | Resolve review/checks |
| `blocked` | A reported check on an open feature-to-dev PR failed | Repair branch and rerun CI |
| `ready` | Open, non-draft, approved PR targets `dev/B` and all reported checks succeeded | Merge into the selected train |
| `integrated` | Feature PR merged into `dev/B` | Run integration regression |
| `release-candidate` | `dev/B -> release/B` merged and release gates pass | Archive/upload the release artifact |
| `published` | Configured destination confirms the release artifact and QA/release criteria pass | Merge, tag, and clean short-lived branches |

## Invariants

- Resolve the default branch from repository metadata. `main` and `master` are aliases in prose, never two required branches.
- A feature or bugfix branch has no open PR until it is explicitly selected for a version. Its only open integration PR targets that version's `dev/B`; never open a feature-to-default-branch PR in this workflow.
- A `dev/B` contains only the selected feature branches for B. It is deleted only after its promotion PR is merged.
- A `release/B` contains only version metadata and release fixes after promotion. It is deleted only after default-branch sync and tag verification.
- `VERSION_NAME` and `VERSION_CODE` change only in the release flow. `VERSION_CODE` is positive, within Android's supported range, and greater than every prior value recorded for the applicationId by the configured distribution registry.
- Build and sign one configured release artifact (`.aab` or `.apk`) from the release commit. Promote or deliver that immutable archive; do not rebuild for another destination.
- A release tag points to the exact source commit that produced the published artifact.

## Required automation prerequisites

- GitHub App: `contents: write`, `pull-requests: write`; limited to prescribed names and tag creation.
- GitHub Actions `GITHUB_TOKEN`: CI, artifacts, and Environment access only; never PR/branch orchestration.
- Rulesets: default branch, `dev/**`, `release/**` require PRs and checks; only approved release automation may merge the final release.
- Protected Environment: signing and destination credentials, with the designated release approvers.
- Version registry: a distribution-provider API when available, or a protected registry that records every allocated `VERSION_CODE`.

## Failure handling

- CI, signing, or artifact verification failure: stop; do not publish, tag, merge, or clean branches.
- Distribution delivery or promotion failure: stop before default-branch merge/tag; retain the release branch and immutable archive.
- Default-branch merge conflict: retain all release evidence and repair through a new protected PR; never force-push.
- Existing tag or duplicate version code: stop and allocate a new version code.
