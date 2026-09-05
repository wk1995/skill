# Android code-train contract

## States

| State | Evidence | Allowed next action |
| --- | --- | --- |
| `development` | Requirement branch has no open integration PR | Continue development or select a version |
| `misrouted` | Open PR targets a branch other than `dev/B` | Close or retarget it |
| `pending` | PR targets `dev/B` but is draft, unapproved, or has incomplete checks | Resolve review or checks |
| `blocked` | A reported code check failed | Repair the requirement branch |
| `ready` | Open, non-draft, approved PR targets `dev/B`; all reported code checks pass | Merge into `dev/B` |
| `integrated` | Selected requirement PR is merged into `dev/B` | Run integration code gates |
| `release-source` | `dev/B -> release/B` is merged and source gates pass | Merge through the protected default-branch path |
| `tagged-source` | Default branch contains the accepted release commit and immutable `vB` points to it | Hand the exact ref to artifact automation |

## Source-only invariants

- Resolve the default branch from repository metadata.
- A requirement branch has no integration PR until its version is selected. Its integration PR targets only that version's `dev/B`.
- `dev/B` contains only requirements explicitly selected for B and is deleted only after promotion succeeds.
- `release/B` contains version metadata and release fixes after promotion and is deleted only after default-branch synchronization and tag verification.
- Version metadata changes only in the protected release source flow. Artifact jobs read it but never modify it.
- The release tag points to the exact accepted source commit and is never moved or recreated by artifact automation.
- This contract contains no binary artifact, signing, upload, distribution, store, or retention state.

## Required source automation

- GitHub App permissions for prescribed branch, PR, merge, and tag operations.
- Rulesets requiring PR review and code checks on the default branch, `dev/**`, and `release/**`.
- Repository-owned version policy and tag format.
- Code checks appropriate to each branch stage. A compile check may produce temporary outputs but must not treat them as release artifacts.

## Failure handling

- Review or code-check failure: stop before merge, tag, or branch cleanup.
- Version-policy failure: keep `release/B`, correct metadata through a reviewed commit, and rerun source gates.
- Default-branch merge conflict: repair through a protected PR; never force-push.
- Existing or invalid tag: stop without replacing it and resolve the version or tag policy.
- Artifact failure after `tagged-source`: retain the verified source tag; artifact retries must consume the same ref unless a new source release is explicitly created.
