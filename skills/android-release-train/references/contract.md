# Release-train contract

## States

| State | Evidence | Allowed next action |
| --- | --- | --- |
| `development` | Branch has no eligible PR | Continue development or open a PR |
| `pending` | PR is draft, unapproved, or checks are incomplete | Resolve review/checks |
| `blocked` | A reported check failed | Repair branch and rerun CI |
| `ready` | Open PR, non-draft, approved, all reported checks succeeded | Include in an explicitly selected train |
| `integrated` | Feature PR merged into `dev/B` | Run integration regression |
| `release-candidate` | `dev/B -> release/B` merged and release gates pass | Archive/upload the release artifact |
| `published` | Destination confirms the AAB and QA/release criteria pass | Merge, tag, and clean short-lived branches |

## Invariants

- Resolve the default branch from repository metadata. `main` and `master` are aliases in prose, never two required branches.
- A `dev/B` contains only the selected feature branches for B. It is deleted only after its promotion PR is merged.
- A `release/B` contains only version metadata and release fixes after promotion. It is deleted only after default-branch sync and tag verification.
- `VERSION_NAME` and `VERSION_CODE` change only in the release flow. `VERSION_CODE` is positive, within Android's supported range, and greater than every already-published value for the applicationId.
- Build and sign once from the release commit. Promote that immutable AAB; do not build a new AAB for another Play track.
- A release tag points to the exact source commit that produced the published artifact.

## Required automation prerequisites

- GitHub App: `contents: write`, `pull-requests: write`; limited to prescribed names and tag creation.
- GitHub Actions `GITHUB_TOKEN`: CI, artifacts, and Environment access only; never PR/branch orchestration.
- Rulesets: default branch, `dev/**`, `release/**` require PRs and checks; only approved release automation may merge the final release.
- Protected Environment: signing and Play credentials, with the designated release approvers.
- Version registry: Play Console API or a protected registry that records every allocated `VERSION_CODE`.

## Failure handling

- CI, signing, or artifact verification failure: stop; do not publish, tag, merge, or clean branches.
- Play upload/promotion failure: stop before default-branch merge/tag; retain the release branch and immutable archive.
- Default-branch merge conflict: retain all release evidence and repair through a new protected PR; never force-push.
- Existing tag or duplicate version code: stop and allocate a new version code.
