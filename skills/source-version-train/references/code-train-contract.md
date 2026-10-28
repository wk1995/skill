# Source version-train contract

## States

| State | Evidence | Allowed next action |
| --- | --- | --- |
| `development` | Requirement branch has no open integration PR | Continue development or select a version |
| `misrouted` | Open PR targets a branch other than `dev_B` | Close or retarget it |
| `pending` | PR targets `dev_B` but is draft, unapproved, or has incomplete checks | Resolve review or checks |
| `blocked` | A reported code check failed | Repair the requirement branch |
| `ready` | Open, non-draft, approved PR targets `dev_B`; all reported code checks pass | Merge into `dev_B` |
| `integrated` | Selected requirement PR is merged into `dev_B` | Run integration code gates |
| `publish-source` | The visible `dev_B -> publish_B` PR is merged and source gates pass | Rebase that merged result onto the default branch as a hidden candidate |
| `release-candidate` | A hidden release candidate contains `publish_B` rebased onto the fetched default branch, with any permitted build-number adjustment committed and its gates passed again | Call the packaging interface, then the publish interface |
| `packaged` | Every repository-defined package exists for that exact candidate commit | Call the publish interface |
| `published` | Every defined package exists and both interfaces pass | Tag that commit, merge it to the default branch, then delete the hidden candidate |
| `source-only` | The repository defines no package flow for any platform | Merge that commit to the default branch without a tag, then delete the hidden candidate |
| `tagged-source` | The candidate commit is tagged as immutable `vB` and the default branch contains it | Delete `dev_B` only now, delete the hidden candidate, and retain the visible publication branch |

## Source-only invariants

- Resolve the default branch from repository metadata. The lifecycle is not specific to a language or project type.
- The selected version must be `major.minor.patch`: exactly three dot-separated canonical integers, without names, prerelease suffixes, or build metadata. A canonical integer is `0` or a decimal without leading zeroes. `5.1.3`, `1.4.0`, and `0.1.0` are valid; `1`, `1.4`, `1.01.0`, `latest`, `dev`, and `1.4.0-rc.1` are not. Validate it independently at selection, initialization, reuse, and tagging. A caller that skips selection must still be rejected.
- A requirement branch has no integration PR until its version is selected. Its integration PR targets only that version's `dev_B`.
- The integration branch is resolved only from `integration_template`, which defaults to `dev_{version}` and therefore `dev_5.1.3` for version `5.1.3`. A repository may replace that template. No integration prefix is applied in addition to it. `dev/5.1.3` is not the default name.
- A new `dev_B` records the exact default-branch baseline and contains a verified version-initialization commit plus only requirements explicitly selected for B. Every repository-owned version value advances under repository policy; all maintained representations agree. Reusing a verified train never repeats the increment.
- The visible publication branch is resolved only from `publish_template`, which defaults to `publish_{version}` and therefore `publish_5.1.3` for version `5.1.3`. A repository may replace that template. No publication prefix is applied in addition to it. The branch appears in pull requests, is protected, and accepts changes only through a reviewed pull request. Merging `dev_B` into it does not publish and does not authorize rewriting it.
- Version metadata is initialized in the integration source flow and preserved unchanged on the visible publication branch. A repository-authorized publication or build-counter adjustment is applied only on the hidden release candidate, after the rebase and before packaging. That adjustment is a new candidate commit and must pass the candidate's source review and code gates again before packaging. Artifact jobs read the rechecked commit and never modify it.
- A publication branch created before integration starts at the recorded pre-initialization baseline. A project script is optional; equivalent Git/file operations must enforce the same validation and failure-state invariants.
- After the visible PR merges, rebase that merged publication onto the fetched default branch and store the result as a new hidden release candidate. The candidate is not visible in pull requests. Never merge the default branch into the visible publication branch, rewrite that branch, or force-push it.
- Packaging is an interface keyed by the packages the repository defines. Discover them instead of assuming Android: Android uses `.apk` or `.aab`; Windows uses `.exe`, `.msi`, `.msix`, or a portable `.zip`; macOS uses `.dmg`, `.pkg`, or a zipped `.app`; iOS uses `.ipa`. A successful workflow that does not contain each defined file is a packaging failure. A defined package job that failed or never ran is also a packaging failure and blocks the default-branch merge. A repository with no defined package flow for any platform may merge without tagging. `build-pipeline-engineering` is the implementation when it is available, and a failure from it stops the attempt. Publication is a separate interface and runs only after every defined package exists. The only destination named by this contract is GitHub Actions Artifacts, and it is the default. This contract does not name other publish channels. A failure of the default destination is a publish failure.
- Publication is idempotent per commit and destination. Record each attempt's commit, destination, and result. A retry of the same commit must not send it again to a destination already recorded as successful, including after a partial success; retry only destinations that failed or have no record. A new source commit may be published to every configured destination. Never treat a repeated event or command as a reason to publish the same commit twice.
- Delete the hidden release candidate after every attempt, whether publication succeeds or fails. Never delete the visible publication branch as part of that cleanup. Keep `dev_B` through promotion, rebase, packaging, and publication so a failed package or publish can still be repaired from it. Delete `dev_B` only after the candidate commit has merged to the default branch and any required tag is verified. Either condition alone is not enough. A source-only repository has no required tag.
- Tag the candidate commit only after every defined package exists and both interfaces pass. Then merge that exact tagged commit to the default branch. The tag is never moved or replaced by either interface. A missing, failed, or never-run defined package blocks both the tag and the merge. When no package flow is defined, merge without creating a tag. A publish failure also blocks the tag and merge.

## Required source automation

- GitHub App permissions for prescribed branch, PR, merge, and tag operations.
- Rulesets requiring PR review and code checks on the default branch, the integration pattern, and the visible publication pattern. The default integration pattern is `dev_*`; the default publication pattern is `publish_*`. The visible publication pattern must reject direct pushes. The hidden release candidate must not be exposed as a pull-request branch.
- Repository-owned version policy and tag format.
- Code checks appropriate to each branch stage. A compile check may produce temporary outputs but must not treat them as release artifacts.

## Failure handling

- Review or code-check failure: stop before merge, tag, or branch cleanup.
- Non-numeric or descriptive version identifier: stop before creating, reusing, publishing, tagging, or merging a train.
- Initialization validation failure: do not create or push a new train. A failure after local edits or a failed commit must preserve and report that state without pushing it.
- Version-policy failure on an existing train: preserve the branch, correct metadata through a reviewed source commit, and rerun source gates.
- Rebase conflict or failure: stop before creating the hidden candidate, preserve `dev_B` and the visible publication branch, and do not package, publish, tag, or merge.
- Post-rebase adjustment or gate failure: delete the hidden release candidate, keep `dev_B` and the visible publication branch, and do not package, publish, tag, or merge. A retry creates a new hidden candidate and applies the adjustment again.
- Packaging failure or absent defined package: delete the hidden release candidate, keep `dev_B` and the visible publication branch, and do not call publication, tag, or merge. A workflow that succeeds without the required `.apk`, `.aab`, `.exe`, `.msi`, `.msix`, portable `.zip`, `.dmg`, `.pkg`, `.app` archive, or `.ipa` is this failure. A retry creates a new hidden candidate.
- No defined package flow: do not tag. The candidate may merge to the default branch, and `dev_B` may be deleted only after that merge succeeds.
- Publish failure: delete the hidden release candidate and keep `dev_B` and the visible publication branch. Repair starts from the surviving `dev_B`; do not recreate it. If the default GitHub Actions Artifacts destination fails, do not tag or merge. A retry must reuse the recorded results and must not resend the same commit to a destination that already succeeded.
- Default-branch merge failure after the tag exists: keep the verified tag and do not delete `dev_B`, the visible publication branch, or the hidden release candidate. Repair the merge through a protected pull request and continue from the existing tag. Never delete that tag, never force-push, and never create the tag again.
- Existing or invalid tag: stop without replacing it and resolve the version or tag policy.
- Publish failure after `tagged-source`: retain the verified source tag; retries must consume the same commit unless a new source release is explicitly created, and must still skip destinations already recorded as successful.
