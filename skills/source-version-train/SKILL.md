---
name: source-version-train
description: Orchestrate source code from a requirement branch through a visible publish PR, a hidden release candidate, packaging and publish interfaces, and an immutable source tag. Use for feature/bugfix branches, dev and publish PRs, code gates, version metadata, or source tags; do not use to implement packaging or a publish destination.
metadata:
  sync_id: "android-code-release-train"
  version: "3.0.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/source-version-train
  triggering:
    include:
      - The user asks to implement a requirement on a feature or bugfix branch and carry its code into a selected version train.
      - The task involves selecting code for dev_<version>, merging it through a visible publish_<version> PR, rebasing that result onto a hidden release candidate, or tagging and synchronizing the default branch.
      - The user needs source-branch orchestration, PR readiness, code gates, or version metadata changes for a release train.
    exclude:
      - The task is to implement or troubleshoot a packaging build, signing, checksums, or one publish destination. Those are implementations of this train's packaging and publish interfaces; use build-pipeline-engineering for packaging.
      - The request is an ordinary build, test, or code edit without the version-train lifecycle.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Source Version Train

Operate this source-only lifecycle for any repository:

`requirement` -> `feature/*` / `bugfix/*` -> `dev_B` -> visible `publish_B` -> hidden release candidate -> package and publish -> `vB` -> default branch

`publish_B` is the visible publication branch shown in pull requests. `B` is `major.minor.patch`, so version `5.1.3` uses `publish_5.1.3`. `publish_template` is the only source of that name; there is no separate prefix. A repository may replace the template. The branch is protected: changes reach it through a reviewed pull request, never by a direct push. Merging `dev_B` into it does not publish anything.

The merge creates a hidden release candidate by rebasing `publish_B` onto the default branch. That candidate is not a pull-request branch. Delete it after a failed attempt before tagging, or after successful finalization; once tagged, retain it until the default-branch ancestry check passes. The visible `publish_B` remains.

Packaging and publication are interfaces. Discover every platform package the repository defines; do not assume Android APK. Windows evidence is an `.exe`, `.msi`, `.msix`, or a portable `.zip` archive, macOS evidence is a `.dmg`, `.pkg`, or `.app` archive, iOS evidence is an `.ipa`, and Android evidence is an `.apk` or `.aab`. A workflow success without the defined package is a packaging failure. A repository that defines no package flow at all may merge to the default branch, but it must not receive a tag. `build-pipeline-engineering` is the packaging implementation used when it is available. Publication defaults to GitHub Actions Artifacts when no destination is configured. When destinations are configured, one success is enough by default. Tag only after every defined package exists and both interfaces pass.

## Prerequisites

- Read [references/code-train-contract.md](references/code-train-contract.md) before a mutating train operation.
- Resolve the repository default branch instead of assuming `main` or `master`.
- Before packaging or publication, verify that the default branch's protected merge path can preserve the exact candidate commit: a merge commit, or a true fast-forward when policy permits it. Squash merge, rebase-and-merge, and cherry-pick cannot finalize a tagged release. If policy permits only rewriting methods, stop before publication and report the incompatible policy; do not bypass protection or change it without authorization.
- Discover the project's branch conventions, authoritative version sources, and version policy. Resolve the integration branch only from `integration_template`, which defaults to `dev_{version}`, so version `5.1.3` uses `dev_5.1.3`. Resolve the visible publication branch only from `publish_template`, which defaults to `publish_{version}`. Do not also apply an integration or publication prefix. The hidden release candidate is separate and is never used as that visible branch.
- Accept only `major.minor.patch`, such as `5.1.3`. Each component is a canonical integer: `0` or a decimal without leading zeroes, so `0.1.0` is valid and `1.01.0` is not. Reject fewer or more components, and reject named or descriptive versions such as `latest`, `dev`, `release`, `1`, `1.4`, or `1.4.0-rc.1`, at every direct entry: selection, initialization, reuse, and tagging. Do not rely on selection having already rejected the version.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App when automated branch, PR, merge, or tag operations must retrigger workflows. Do not substitute `GITHUB_TOKEN` when its events would not retrigger ordinary workflows.
- Use [assets/code-release-train.yml](assets/code-release-train.yml) as the source-flow configuration template when bootstrapping a repository.

## Operation Routing

### Bootstrap or repair source orchestration

Inspect branch conventions, default branch, version source, required code checks, review policy, Rulesets, and existing workflows. Configure only source-flow automation:

1. Code validation on feature, bugfix, integration, publication, hidden candidate, finalization, and default branches. Required finalization PR checks must actually run on the resolved finalization pattern.
2. Train orchestration for `dev_B`, selected feature-to-dev PRs, and the unique promotion PR into the resolved publication branch. Protect that branch so it accepts changes only through a reviewed pull request.
3. Finalization that creates a hidden release candidate from the visible publication branch, invokes the packaging and publish interfaces, creates `vB` after both pass, and merges through a separate finalization PR when the default branch requires one. Keep the hidden candidate out of PRs and never push its rebased history to the visible publication branch.

The checks may compile or test code. This Skill calls the two interfaces and does not implement signing, packaging, upload, or retention. Use `build-pipeline-engineering` when that packaging implementation is available. Use a configured publish implementation for each destination.

### Implement a requirement

Create `feature/<ticket-or-slug>` or `bugfix/<ticket-or-slug>` from the resolved default branch. Keep release version metadata unchanged while implementing the requirement. Build or test only as code validation; do not retain or distribute the outputs as release artifacts.

Do not open a PR until the user explicitly selects an existing `dev_B` train. Never target the default branch directly from a requirement branch and never silently create a train. If the named train does not exist, report that the version scope must be selected first.

### Inventory and select a version scope

Use the bundled read-only inventory and selection validation when its conventions match the repository; otherwise use repository tooling or equivalent Git/hosting reads:

```bash
python3 scripts/code_release_train.py inventory --format table
python3 scripts/code_release_train.py select --version 1.4.0 --branches feature/login,feature/report
```

After selection, initialize or reuse `dev_1.4.0` (`dev_B`) as described below, then create the feature-to-dev PRs through the configured automation identity. A branch is **ready** only when its PR is open, non-draft, targets the selected integration branch, has approval, and all reported code checks succeed. Ready means eligible for code integration, not product acceptance and not artifact readiness. Adapt the bundled inventory's branch assumptions through repository tooling or equivalent Git/hosting reads when project conventions differ.

### Initialize a version integration branch

Create each new version integration branch from an exact, freshly fetched default-branch commit and record that baseline before updating versions. Initialize every repository-owned version value to the selected target according to the project's existing policy, including a build or revision counter when the project maintains one. Every initialized value must advance from the baseline; synchronize every maintained representation of those values. Never assume a language, decimal encoding, build counter, filename, or property key. If the project has no documented way to derive the new values, resolve that policy before writing.

Prefer a discovered, trusted repository command that creates the branch, validates the target, writes the version sources, and commits the initialization. **No project script is required:** when such an entry point is absent, perform the same steps with Git and normal file tools: verify a clean worktree and target availability, capture the default-branch SHA, validate the proposed values, create the branch, edit and verify all version sources, commit only the initialization changes, and push only when authorized. Do not install a project-specific helper or copy another project's version formula just to use this Skill. If verification or commit fails, preserve and report the local state without publishing a partially initialized train.

Reuse an existing integration branch without another increment or initialization commit. Validate its branch/target agreement and version consistency before any update or early-success return; do not reset it to the latest default branch or rewrite its history. Legacy trains may lack a recorded baseline: reuse them only when their identity and version configuration can be verified, and preserve their established publication branch.

When publication branches are initialized in advance, start them from the recorded **pre-initialization default-branch baseline**, not from the integration branch's version commit. This keeps the first build and the version-only integration diff consistent with repository policy. Later promotion, including repositories that create the publication branch only at promotion time, must preserve the initialized target. CI should validate integration branch names, source versions and duplicate configuration, and the baseline before creating a missing publication branch. Repeated runs must preserve existing branches and must not bump versions merely because the command or event was retried.

### Resume before starting another candidate

Serialize attempts for the same repository/version. Before creating a candidate, packaging, or publishing, inspect the remote tag and the durable attempt record described in [the retry contract](references/code-train-contract.md#retry-and-protected-finalization). An existing tag resumes verification or the protected default-branch merge from its recorded commit; it never starts a fresh build/publication. A confirmed first attempt with no tag or prior publication may initialize a new record. A missing or inconsistent record for an existing tag or prior publication, or an uncertain remote lookup, stops the attempt before publication.

After post-rebase gates, persist the visible publication SHA, default baseline, adjustment inputs, exact candidate SHA, package identities/checksums, and per-destination results outside the disposable branch and runner. Retain recoverable candidate Git objects and package evidence before deleting an untagged failed candidate. A retry with unchanged inputs restores the same candidate SHA and reuses its packages; it must not reconstruct a build-adjustment commit and treat its new timestamp/SHA as new source. An intentional source/baseline/adjustment change is a new candidate with fresh gates and package evidence, and cannot replace an existing tag. Record an interrupted publication as uncertain and reconcile its destination receipt before resending.

### Promote, rebase, and finalize source code

Only promote after all selected requirement PRs are merged into `dev_B` and integration code checks pass:

1. Create the visible publication branch from the default branch by resolving `publish_template`. The default template is `publish_{version}`, so version `5.1.3` creates `publish_5.1.3`. Do not prepend another publication prefix. Open the unique PR from `dev_B`.
2. Preserve the version initialized on `dev_B` on the visible publication branch. Do not apply a publication or build-number adjustment there, and do not repeat the initial version bump in packaging.
3. When the `dev_B -> publish_B` PR merges, first record that merge on the visible publication branch. Keep that branch and its history unchanged by the later rebase.
4. Fetch the default branch and rebase the merged publication onto that exact commit, creating a new hidden release candidate. Resolve conflicts on the candidate. Do not merge the default branch into `publish_B`, do not rewrite `publish_B`, and do not open a PR for the candidate.
5. On that hidden candidate, after the rebase and before packaging, validate the preserved version and apply only the policy's permitted publication or build-number adjustment. Commit that adjustment on the candidate, then rerun the candidate's source review and code gates. Do not package or publish a candidate whose adjustment has not passed those gates again. A candidate that needs no adjustment still requires the post-rebase gates before packaging.
6. Call the packaging interface for that exact adjusted and rechecked candidate commit. Discover the repository's defined packages first. Android requires the defined `.apk` or `.aab`; Windows requires each defined `.exe`, `.msi`, `.msix`, or portable `.zip`; macOS requires each defined `.dmg`, `.pkg`, or `.app` archive; iOS requires the defined `.ipa`. A green job that does not contain one of those defined files is a packaging failure, as is a package job that failed or never ran. If the repository defines no package flow at all, packaging is not applicable: the candidate may later merge without a tag. If `build-pipeline-engineering` is available for a defined package, it is the implementation and must produce that package from this commit.
7. Call the publish interface for the same commit only when every defined package exists. With no configured destinations, GitHub Actions Artifacts is the sole default and must succeed. A non-empty configured destination list replaces that fallback; by default any one configured success passes publication, even when another configured destination fails. Honor a repository's explicit stricter policy. Record every success and failure against that exact commit and destination. Publication is idempotent: a retry of the same commit must not send it again to a destination that already succeeded, and must retry only failed or unattempted destinations after resolving uncertain attempts. Skip publication when no package flow is defined.
8. Validate the numeric version again. Tag that exact candidate commit as `vB` only when every defined package was produced and both interfaces passed. Verify the tag, then merge that original commit into the default branch using a merge commit or a policy-permitted true fast-forward. When default-branch protection requires a PR, create or reuse a separate finalization branch from the recorded candidate/tagged SHA, using `finalization_template` (default `finalize_{version}`), and open its PR to the default branch. Verify its source commit before reuse, satisfy required reviews/checks, and explicitly select a preserving merge method. Never use the unchanged visible `publish_B` as a substitute for the adjusted candidate, and never open a PR from the hidden candidate. Do not squash, rebase-and-merge, cherry-pick, or rewrite the candidate after packaging or tagging. If the default branch advanced, preserve the tagged commit and follow the protected finalization path; a conflict or incompatible policy stops finalization. If no package flow is defined, use the same protected path without creating a tag.
9. After the remote merge, fetch the default branch and tag from the resolved repository remote. Require the tag's peeled commit to equal the recorded packaged/published candidate SHA, and require `git merge-base --is-ancestor` to prove that commit is in the fetched default-branch history. Follow [the finalization check](references/code-train-contract.md#finalization-check); PR status or equal file contents is insufficient. Only after verification succeeds may the release be reported complete and `dev_B` and the hidden candidate be deleted. A fetch, identity, or ancestry failure must preserve the tag and every involved branch for repair. Before a tag exists, a failed package or publish attempt deletes only the hidden candidate and keeps `dev_B` and `publish_B`. A source-only merge requires confirmation on the fetched default branch before cleanup, without any tag check.

Do not merge when a defined package failed, never ran, or is absent. Do not tag when no package flow is defined, when any defined package is missing, or when the effective publication policy fails. Restore the recorded candidate on an unchanged-input retry; create a new candidate only for a deliberate input change before a tag exists. Skip destinations already recorded as successful. The tag is immutable and must not be moved or replaced by either interface. Clean up the separate finalization branch only after the same remote verification required for `dev_B` and the hidden candidate.

If `vB` exists but the merge or finalization check fails, keep the tag and every branch involved, including `dev_B`, the visible publication branch, and the hidden release candidate. Repair through a protected pull request that preserves the original tagged commit as an ancestor, continue from that existing tag, and rerun the finalization check even when a prior PR is already marked merged. Do not delete, move, or recreate the tag, and do not delete those branches to recover.

## Remote-Write Gates

Before a remote mutation, state the repository, default branch, source and target branches, selected requirements, version, and whether the operation creates branches, PRs, rebases, pushes, merges, tags, or deletes branches.

Follow `git-account-safety` for GitHub operations. Never force-push, bypass branch protection, alter Rulesets without an explicit request, delete a branch before its gate, or create/replace tags from the artifact workflow.

## Resources

- [scripts/code_release_train.py](scripts/code_release_train.py): read-only feature-branch, PR, and code-check inventory.
- [assets/code-release-train.yml](assets/code-release-train.yml): per-repository source-flow configuration template.
- [references/code-train-contract.md](references/code-train-contract.md): source states, invariants, and failure rules.
