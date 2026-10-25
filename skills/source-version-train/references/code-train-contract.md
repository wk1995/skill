# Source version-train contract

## States

| State | Evidence | Allowed next action |
| --- | --- | --- |
| `development` | Requirement branch has no open integration PR | Continue development or select a version |
| `misrouted` | Open PR targets a branch other than `dev/B` | Close or retarget it |
| `pending` | PR targets `dev/B` but is draft, unapproved, or has incomplete checks | Resolve review or checks |
| `blocked` | A reported code check failed | Repair the requirement branch |
| `ready` | Open, non-draft, approved PR targets `dev/B`; all reported code checks pass | Merge into `dev/B` |
| `integrated` | Selected requirement PR is merged into `dev/B` | Run integration code gates |
| `publish-source` | The visible `dev/B -> publish/B` PR is merged and source gates pass | Rebase that merged result onto the default branch as a hidden candidate |
| `release-candidate` | A hidden release candidate contains `publish/B` rebased onto the fetched default branch | Call the packaging interface, then the publish interface |
| `published` | Both interfaces pass for that exact candidate commit | Tag that commit, merge it to the default branch, then delete the hidden candidate |
| `tagged-source` | The candidate commit is tagged as immutable `vB` and the default branch contains it | Delete the hidden candidate and retain the visible publication branch |

## Source-only invariants

- Resolve the default branch from repository metadata. The lifecycle is not specific to a language or project type.
- The selected version must be an explicit numeric identifier: one or more dot-separated non-negative integers, without leading zeroes, names, prerelease suffixes, or build metadata. `1`, `1.4`, and `1.4.0` are valid; `latest`, `dev`, and `1.4.0-rc.1` are not. Validate it before branch creation, reuse, publication, tagging, or an early-success return.
- A requirement branch has no integration PR until its version is selected. Its integration PR targets only that version's `dev/B`.
- A new `dev/B` records the exact default-branch baseline and contains a verified version-initialization commit plus only requirements explicitly selected for B. Every repository-owned version value advances under repository policy; all maintained representations agree. Reusing a verified train never repeats the increment.
- The visible publication branch defaults to `publish/B`. A configured template may select another visible name. It appears in pull requests, is protected, and accepts changes only through a reviewed pull request. Merging `dev/B` into it does not publish and does not authorize rewriting it.
- Version metadata is initialized in the integration source flow and preserved at promotion, with only repository-authorized publication or build-counter adjustments. Artifact jobs read it but never modify it.
- A publication branch created before integration starts at the recorded pre-initialization baseline. A project script is optional; equivalent Git/file operations must enforce the same validation and failure-state invariants.
- After the visible PR merges, rebase that merged publication onto the fetched default branch and store the result as a new hidden release candidate. The candidate is not visible in pull requests. Never merge the default branch into the visible publication branch, rewrite that branch, or force-push it.
- Packaging is an interface. No available implementation means packaging passes. `build-pipeline-engineering` is the implementation when it is available, and a failure from it stops the attempt. Publication is a separate interface. No configured implementation means publication passes; otherwise call every configured implementation, such as FIR, GitHub Actions Artifacts, or `wk1998.io`. The default policy passes when one implementation succeeds.
- Delete the hidden release candidate after every attempt, whether publication succeeds or fails. Never delete the visible publication branch as part of that cleanup. Delete `dev/B` only after the tag is verified and the candidate commit has merged to the default branch.
- Tag the candidate commit and merge it to the default branch only after both interfaces pass. The tag points to that exact commit and is never moved or replaced by either interface. A packaging failure or every configured publish implementation failing blocks the tag and merge.

## Required source automation

- GitHub App permissions for prescribed branch, PR, merge, and tag operations.
- Rulesets requiring PR review and code checks on the default branch, `dev/**`, and the visible publication pattern. The default pattern is `publish/**`. The visible publication pattern must reject direct pushes. The hidden release candidate must not be exposed as a pull-request branch.
- Repository-owned version policy and tag format.
- Code checks appropriate to each branch stage. A compile check may produce temporary outputs but must not treat them as release artifacts.

## Failure handling

- Review or code-check failure: stop before merge, tag, or branch cleanup.
- Non-numeric or descriptive version identifier: stop before creating, reusing, publishing, tagging, or merging a train.
- Initialization validation failure: do not create or push a new train. A failure after local edits or a failed commit must preserve and report that state without pushing it.
- Version-policy failure on an existing train: preserve the branch, correct metadata through a reviewed source commit, and rerun source gates.
- Rebase conflict or failure: stop before creating the hidden candidate, preserve and report the visible publication branch, and do not package, publish, tag, or merge.
- Packaging failure: delete the hidden release candidate, keep the visible publication branch, and do not call publication, tag, or merge. A retry creates a new hidden candidate.
- Publish failure: delete the hidden release candidate and keep the visible publication branch. If every configured implementation fails, do not tag or merge. If at least one succeeds under the default policy, record the failures and continue. No configured implementation is itself a pass.
- Default-branch merge conflict: repair through a protected PR; never force-push.
- Existing or invalid tag: stop without replacing it and resolve the version or tag policy.
- Publish failure after `tagged-source`: retain the verified source tag; retries must consume the same commit unless a new source release is explicitly created.
