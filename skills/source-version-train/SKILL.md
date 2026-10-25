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
      - The task involves selecting code for dev/<version>, merging it through a visible publish_<version> PR, rebasing that result onto a hidden release candidate, or tagging and synchronizing the default branch.
      - The user needs source-branch orchestration, PR readiness, code gates, or version metadata changes for a release train.
    exclude:
      - The task is to implement or troubleshoot a packaging build, signing, checksums, or one publish destination. Those are implementations of this train's packaging and publish interfaces; use build-pipeline-engineering for packaging.
      - The request is an ordinary build, test, or code edit without the version-train lifecycle.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Source Version Train

Operate this source-only lifecycle for any repository:

`requirement` -> `feature/*` / `bugfix/*` -> `dev/B` -> visible `publish_B` -> hidden release candidate -> package and publish -> `vB` -> default branch

`publish_B` is the visible publication branch shown in pull requests. `B` is `major.minor.patch`, so version `5.1.3` uses `publish_5.1.3`. `publish_template` is the only source of that name; there is no separate prefix. A repository may replace the template. The branch is protected: changes reach it through a reviewed pull request, never by a direct push. Merging `dev/B` into it does not publish anything.

The merge creates a hidden release candidate by rebasing `publish_B` onto the default branch. That candidate is not a pull-request branch and is deleted after the attempt, whether publication succeeds or fails. The visible `publish_B` remains.

Packaging and publication are interfaces. No packaging implementation means packaging passes. `build-pipeline-engineering` is the packaging implementation used when it is available. Publication defaults to GitHub Actions Artifacts when no destination is configured. When destinations are configured, one success is enough by default. Tag and merge the default branch only after both interfaces pass.

## Prerequisites

- Read [references/code-train-contract.md](references/code-train-contract.md) before a mutating train operation.
- Resolve the repository default branch instead of assuming `main` or `master`.
- Discover the project's branch conventions, authoritative version sources, and version policy. Resolve the visible publication branch only from `publish_template`, which defaults to `publish_{version}`. Do not also apply a publication prefix. The hidden release candidate is separate and is never used as that visible branch.
- Accept only `major.minor.patch`, such as `5.1.3`. Each component is a canonical integer: `0` or a decimal without leading zeroes, so `0.1.0` is valid and `1.01.0` is not. Reject fewer or more components, and reject named or descriptive versions such as `latest`, `dev`, `release`, `1`, `1.4`, or `1.4.0-rc.1`, at every direct entry: selection, initialization, reuse, and tagging. Do not rely on selection having already rejected the version.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App when automated branch, PR, merge, or tag operations must retrigger workflows. Do not substitute `GITHUB_TOKEN` when its events would not retrigger ordinary workflows.
- Use [assets/code-release-train.yml](assets/code-release-train.yml) as the source-flow configuration template when bootstrapping a repository.

## Operation Routing

### Bootstrap or repair source orchestration

Inspect branch conventions, default branch, version source, required code checks, review policy, Rulesets, and existing workflows. Configure only source-flow automation:

1. Code validation on feature, bugfix, integration, publication, and default branches.
2. Train orchestration for `dev/B`, selected feature-to-dev PRs, and the unique promotion PR into the resolved publication branch. Protect that branch so it accepts changes only through a reviewed pull request.
3. Finalization that creates a hidden release candidate from the visible publication branch, invokes the packaging and publish interfaces, creates `vB` after both pass, and then merges that result back.

The checks may compile or test code. This Skill calls the two interfaces and does not implement signing, packaging, upload, or retention. Use `build-pipeline-engineering` when that packaging implementation is available. Use a configured publish implementation for each destination.

### Implement a requirement

Create `feature/<ticket-or-slug>` or `bugfix/<ticket-or-slug>` from the resolved default branch. Keep release version metadata unchanged while implementing the requirement. Build or test only as code validation; do not retain or distribute the outputs as release artifacts.

Do not open a PR until the user explicitly selects an existing `dev/B` train. Never target the default branch directly from a requirement branch and never silently create a train. If the named train does not exist, report that the version scope must be selected first.

### Inventory and select a version scope

Use the bundled read-only inventory and selection validation when its conventions match the repository; otherwise use repository tooling or equivalent Git/hosting reads:

```bash
python3 scripts/code_release_train.py inventory --format table
python3 scripts/code_release_train.py select --version 1.4.0 --branches feature/login,feature/report
```

After selection, initialize or reuse `dev/B` as described below, then create the feature-to-dev PRs through the configured automation identity. A branch is **ready** only when its PR is open, non-draft, targets the selected integration branch, has approval, and all reported code checks succeed. Ready means eligible for code integration, not product acceptance and not artifact readiness. Adapt the bundled inventory's branch assumptions through repository tooling or equivalent Git/hosting reads when project conventions differ.

### Initialize a version integration branch

Create each new version integration branch from an exact, freshly fetched default-branch commit and record that baseline before updating versions. Initialize every repository-owned version value to the selected target according to the project's existing policy, including a build or revision counter when the project maintains one. Every initialized value must advance from the baseline; synchronize every maintained representation of those values. Never assume a language, decimal encoding, build counter, filename, or property key. If the project has no documented way to derive the new values, resolve that policy before writing.

Prefer a discovered, trusted repository command that creates the branch, validates the target, writes the version sources, and commits the initialization. **No project script is required:** when such an entry point is absent, perform the same steps with Git and normal file tools: verify a clean worktree and target availability, capture the default-branch SHA, validate the proposed values, create the branch, edit and verify all version sources, commit only the initialization changes, and push only when authorized. Do not install a project-specific helper or copy another project's version formula just to use this Skill. If verification or commit fails, preserve and report the local state without publishing a partially initialized train.

Reuse an existing integration branch without another increment or initialization commit. Validate its branch/target agreement and version consistency before any update or early-success return; do not reset it to the latest default branch or rewrite its history. Legacy trains may lack a recorded baseline: reuse them only when their identity and version configuration can be verified, and preserve their established publication branch.

When publication branches are initialized in advance, start them from the recorded **pre-initialization default-branch baseline**, not from the integration branch's version commit. This keeps the first build and the version-only integration diff consistent with repository policy. Later promotion, including repositories that create the publication branch only at promotion time, must preserve the initialized target. CI should validate integration branch names, source versions and duplicate configuration, and the baseline before creating a missing publication branch. Repeated runs must preserve existing branches and must not bump versions merely because the command or event was retried.

### Promote, rebase, and finalize source code

Only promote after all selected requirement PRs are merged into `dev/B` and integration code checks pass:

1. Create the visible publication branch from the default branch by resolving `publish_template`. The default template is `publish_{version}`, so version `5.1.3` creates `publish_5.1.3`. Do not prepend another publication prefix. Open the unique PR from `dev/B`.
2. Preserve the version initialized on `dev/B` on the visible publication branch. Do not apply a publication or build-number adjustment there, and do not repeat the initial version bump in packaging.
3. When the `dev/B -> publish_B` PR merges, first record that merge on the visible publication branch. Keep that branch and its history unchanged by the later rebase.
4. Fetch the default branch and rebase the merged publication onto that exact commit, creating a new hidden release candidate. Resolve conflicts on the candidate. Do not merge the default branch into `publish_B`, do not rewrite `publish_B`, and do not open a PR for the candidate.
5. On that hidden candidate, after the rebase and before packaging, validate the preserved version and apply only the policy's permitted publication or build-number adjustment. Commit that adjustment on the candidate, then rerun the candidate's source review and code gates. Do not package or publish a candidate whose adjustment has not passed those gates again. A candidate that needs no adjustment still requires the post-rebase gates before packaging.
6. Call the packaging interface for that exact adjusted and rechecked candidate commit. If no packaging implementation is available, packaging passes. If `build-pipeline-engineering` is available, it is the implementation and must package that commit. A packaging failure stops publication.
7. Call the publish interface for the same commit. If no destination is configured, publish to GitHub Actions Artifacts. Otherwise call every configured implementation, such as FIR, GitHub Actions Artifacts, or `wk1998.io`. One success satisfies the default policy; record every success and failure against that exact commit and destination. The default destination failing is a publish failure. Publication is idempotent: a retry of the same commit must not send it again to a destination that already succeeded, and must retry only the destinations that failed or never ran.
8. Delete the hidden release candidate after the attempt. Delete it when publication succeeds and when it fails. Never delete the visible `publish_B` as part of that cleanup.
9. Only after both interfaces pass, validate the numeric version again and tag that exact candidate commit as `vB`. Verify the tag, then merge it into the default branch. Delete `dev/B` only after both are true: the tag is verified and that merge has succeeded. Do not delete it at promotion, rebase, packaging, or publication. A publish failure must still leave `dev/B` available for repair.

Do not tag or merge when packaging fails or every configured publish implementation fails. A later retry creates a new hidden candidate from the current visible publication branch, but publication of an unchanged commit stays idempotent: skip destinations already recorded as successful and send the commit only to destinations that failed or have no record. A changed source commit is a new publication. The tag is immutable and must not be moved or replaced by either interface.

If `vB` is already created and verified but merging it into the default branch fails, keep the tag and keep every branch involved, including `dev/B`, the visible publication branch, and the hidden release candidate. Repair the merge through a protected pull request and continue from that existing tag. Do not delete the tag, do not delete those branches to recover, and do not create the tag again.

## Remote-Write Gates

Before a remote mutation, state the repository, default branch, source and target branches, selected requirements, version, and whether the operation creates branches, PRs, rebases, pushes, merges, tags, or deletes branches.

Follow `git-account-safety` for GitHub operations. Never force-push, bypass branch protection, alter Rulesets without an explicit request, delete a branch before its gate, or create/replace tags from the artifact workflow.

## Resources

- [scripts/code_release_train.py](scripts/code_release_train.py): read-only feature-branch, PR, and code-check inventory.
- [assets/code-release-train.yml](assets/code-release-train.yml): per-repository source-flow configuration template.
- [references/code-train-contract.md](references/code-train-contract.md): source states, invariants, and failure rules.
