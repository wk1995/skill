---
name: source-version-train
description: Orchestrate source code from a requirement branch through version-train integration, publication, a verified rebase onto the default branch, and an immutable source tag. Use for feature/bugfix branches, versioned dev and publish PRs, code-readiness gates, version metadata, or source-release tags in any repository; do not use for packaging, signing, or artifact uploads.
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
      - The task involves selecting or assessing code for dev/<version>, promoting code to publish/<version>, rebasing that publication onto the default branch, synchronizing the default branch, or creating the source release tag.
      - The user needs source-branch orchestration, PR readiness, code gates, or version metadata changes for a release train.
    exclude:
      - The task is to configure or run packaging builds, signing, checksums, or output uploads; use build-pipeline-engineering instead.
      - The request is an ordinary build, test, or code edit without the version-train lifecycle.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Source Version Train

Operate this source-only lifecycle for any repository:

`requirement` -> `feature/*` / `bugfix/*` -> `dev/B` -> `publish/B` -> rebase onto the default branch -> package and publish -> `vB` -> default branch

`publish/B` is the default publication branch. A repository may configure another template, such as `release/B`; every publication step below applies to that resolved branch. The publication branch is protected: changes reach it through a reviewed pull request, never by a direct push.

The output is a reviewed, versioned source commit and immutable tag. Creating the publication branch does not publish anything. Publication is an interface invoked only after the rebased branch is pushed and its checks pass: use the repository's CI package when one exists, then call the configured publish implementations. Use `build-pipeline-engineering` for the packaging implementation. One successful publish implementation is enough by default. Tag and merge the default branch only after that success.

## Prerequisites

- Read [references/code-train-contract.md](references/code-train-contract.md) before a mutating train operation.
- Resolve the repository default branch instead of assuming `main` or `master`.
- Discover the project's branch conventions, authoritative version sources, and version policy. Default the publication branch to `publish/B`. Use a configured publication template when the repository or the user specifies one; `release/B` remains valid under that template.
- Require `gh`, `git`, a clean worktree, and GitHub authentication for repository operations.
- Use the repository's GitHub App when automated branch, PR, merge, or tag operations must retrigger workflows. Do not substitute `GITHUB_TOKEN` when its events would not retrigger ordinary workflows.
- Use [assets/code-release-train.yml](assets/code-release-train.yml) as the source-flow configuration template when bootstrapping a repository.

## Operation Routing

### Bootstrap or repair source orchestration

Inspect branch conventions, default branch, version source, required code checks, review policy, Rulesets, and existing workflows. Configure only source-flow automation:

1. Code validation on feature, bugfix, integration, publication, and default branches.
2. Train orchestration for `dev/B`, selected feature-to-dev PRs, and the unique promotion PR into the resolved publication branch. Protect that branch so it accepts changes only through a reviewed pull request.
3. Source finalization that rebases the accepted publication onto the default branch, invokes packaging and the publish interface, creates `vB` after one implementation succeeds, and then merges that result back.

The checks may compile or test code. This Skill selects and invokes the packaging and publish interfaces; it does not implement signing, packaging, upload, or retention. Use `build-pipeline-engineering` for packaging and a configured publish implementation for each destination.

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

1. Create the publication branch from the default branch. Its name is `publish/B` unless a publication template resolves a different name. Open the unique promotion PR from `dev/B`.
2. Preserve the version initialized on `dev/B`, validate it against repository policy, and apply only the policy's permitted publication or build-number adjustments. Do not repeat the initial version bump at promotion or in artifact jobs.
3. Delete `dev/B` only after promotion is merged and the publication branch contains every selected commit.
4. Accept only publication fixes through a reviewed pull request. The publication branch is protected and cannot be updated by a direct push.
5. After those gates pass, fetch the default branch and rebase the publication branch onto that exact commit. Resolve conflicts there; do not merge the default branch in the other direction and do not force-push.
6. Push the rebased publication branch through its protected update path and rerun its source review and code gates. A rebase that changes the commit requires this verification again.
7. Package and publish that exact pushed commit. When the repository has a CI packaging workflow, run it through `build-pipeline-engineering` and publish its outputs. When it has no CI packaging, the passed checks in step 6 are sufficient and publication may proceed without a package. Call every configured publish implementation, such as FIR, GitHub Actions Artifacts, or `wk1998.io`. One successful implementation satisfies the default policy; record which implementations succeeded and failed.
8. Only after that publish policy passes, tag the exact published commit as `vB`, verify the tag, merge it into the default branch, and then delete the publication branch.

Do not tag or merge when every publish implementation fails. A later retry must reuse the same published commit unless the user explicitly creates a new source release. The tag is immutable and must not be moved or replaced by a publish implementation.

## Remote-Write Gates

Before a remote mutation, state the repository, default branch, source and target branches, selected requirements, version, and whether the operation creates branches, PRs, rebases, pushes, merges, tags, or deletes branches.

Follow `git-account-safety` for GitHub operations. Never force-push, bypass branch protection, alter Rulesets without an explicit request, delete a branch before its gate, or create/replace tags from the artifact workflow.

## Resources

- [scripts/code_release_train.py](scripts/code_release_train.py): read-only feature-branch, PR, and code-check inventory.
- [assets/code-release-train.yml](assets/code-release-train.yml): per-repository source-flow configuration template.
- [references/code-train-contract.md](references/code-train-contract.md): source states, invariants, and failure rules.
