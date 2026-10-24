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
| `publish-source` | `dev/B -> publish/B` is merged and source gates pass | Rebase onto the fetched default branch |
| `rebased-source` | `publish/B` has been rebased onto the current default branch, pushed, and its source gates pass again | Package when CI packaging exists, then call the publish interface |
| `published` | At least one configured publish implementation succeeded for that exact commit, or checks passed where no CI packaging exists | Tag that commit, then merge it through the protected default-branch path |
| `tagged-source` | The published commit is tagged as immutable `vB` and the default branch contains it | Retain the tag; publish retries consume the same commit |

## Source-only invariants

- Resolve the default branch from repository metadata. The lifecycle is not specific to a language or project type.
- A requirement branch has no integration PR until its version is selected. Its integration PR targets only that version's `dev/B`.
- A new `dev/B` records the exact default-branch baseline and contains a verified version-initialization commit plus only requirements explicitly selected for B. Every repository-owned version value advances under repository policy; all maintained representations agree. Reusing a verified train never repeats the increment.
- The publication branch defaults to `publish/B`. A configured template may resolve another name, including `release/B`, and that resolved branch carries the same contract. It is protected: publication fixes enter through a reviewed pull request, not a direct push. Creating it does not publish. It is deleted only after the rebased commit has been pushed and rechecked, the publish policy has passed, the tag is verified, and the result has merged to the default branch.
- Version metadata is initialized in the integration source flow and preserved at promotion, with only repository-authorized publication or build-counter adjustments. Artifact jobs read it but never modify it.
- A publication branch created before integration starts at the recorded pre-initialization baseline. A project script is optional; equivalent Git/file operations must enforce the same validation and failure-state invariants.
- Rebase the resolved publication branch onto the default branch only after its source gates pass. Push that result through the protected update path and require the gates again before packaging or publishing. Never merge the default branch into the publication branch as a substitute, never direct-push to it, and never force-push the rebase.
- Publication is an interface with replaceable implementations. The default implementations are FIR, GitHub Actions Artifacts, and `wk1998.io`; a repository may configure a different set. Invoke every configured implementation after the rebased checks pass. A repository with CI packaging must package that exact commit through `build-pipeline-engineering` first. A repository without CI packaging publishes from the verified source commit. The default policy passes when one implementation succeeds.
- Tag the published commit and merge it to the default branch only after the publish policy passes. The tag points to that exact commit and is never moved or replaced by a publish implementation. All implementations failing blocks the tag, the merge, and branch deletion.

## Required source automation

- GitHub App permissions for prescribed branch, PR, merge, and tag operations.
- Rulesets requiring PR review and code checks on the default branch, `dev/**`, and the configured publication pattern. The default pattern is `publish/**`; a repository template such as `release/**` is equally valid. The publication pattern must reject direct pushes.
- Repository-owned version policy and tag format.
- Code checks appropriate to each branch stage. A compile check may produce temporary outputs but must not treat them as release artifacts.

## Failure handling

- Review or code-check failure: stop before merge, tag, or branch cleanup.
- Initialization validation failure: do not create or push a new train. A failure after local edits or a failed commit must preserve and report that state without pushing it.
- Version-policy failure on an existing train: preserve the branch, correct metadata through a reviewed source commit, and rerun source gates.
- Rebase conflict or failure: stop on the local publication branch, preserve and report that state, and do not push or merge it.
- Failed gates after the rebase: keep the pushed publication branch, repair it through a reviewed source commit, and rerun the gates. Do not package, publish, tag, or merge it.
- Packaging or publish failure: keep the publication branch and do not tag or merge it. Retry the same commit. If every configured implementation fails, stop. If at least one succeeds under the default policy, record the failures and continue to tag and merge.
- Default-branch merge conflict: repair through a protected PR; never force-push.
- Existing or invalid tag: stop without replacing it and resolve the version or tag policy.
- Publish failure after `tagged-source`: retain the verified source tag; retries must consume the same commit unless a new source release is explicitly created.
