# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

## [3.0.0] - 2026-10-28

- Change-Type: breaking
- Summary: Generalize the source train beyond Android, initialize versions when a train is created, and finalize the exact packaged and published commit through a verified default-branch merge.
- Compatibility: The immutable sync ID `android-code-release-train`, requirement selection, reviewed source gates, and source/packaging interface boundary remain. This release consolidates the pending branch changes since the published `2.0.0`; the intermediate branch version entries are not separate releases.
- Breaking-Change: Previously a new `dev/<version>` could retain default-branch versions until promotion to `release/<version>`, and accepted source could merge and be tagged before distribution. New trains initialize all repository-owned version values immediately, default to `dev_<version>` and a protected visible `publish_<version>` PR, then create a hidden rebased candidate. Every declared package must exist and publication must pass before tagging; a repository with no package flow may merge without a tag. Finalization must preserve the original tagged commit in default-branch history.
- Migration: Replace Android-only Skill references with `source-version-train` while retaining the sync ID. Migrate new-train branch conventions, PR targets, protection, and workflows from `dev/**` and `release/**` to the resolved integration/publication templates. Configure the repository's version policy and declared packages, preserve initialized versions through publication, and use a commit-preserving protected merge plus remote identity/ancestry verification. Validate and reuse legacy trains without rebumping, rewriting history, or recreating their established publication branch.

### Train initialization and routing

- Discover repository-owned version sources and initialize every maintained value from a freshly fetched default-branch baseline. Use a trusted lifecycle helper when available or equivalent Git/file operations when none exists.
- Reuse verified integration branches without another version increment; record the pre-initialization baseline for publication branches created in advance.
- Resolve branch names only from `integration_template` and `publish_template`, defaulting to `dev_<version>` and `publish_<version>` without an additional prefix. Keep publication changes behind a reviewed PR.
- Require canonical `major.minor.patch` versions, including rejection of leading zeroes, independently at selection, initialization, reuse, and tagging.

### Candidate, packaging, and publication

- Generalize the Skill name and workflow to non-Android repositories without changing the synchronization identity.
- Preserve the visible publication branch and rebase its merged source onto a hidden candidate. Apply permitted build-number adjustments only after rebase and rerun candidate gates before packaging.
- Discover every repository-defined platform package instead of assuming Android. Missing, failed, or never-run package outputs block tagging and the default-branch merge; a green job without its required files is a failure. A repository with no package flow skips publication and merges without a tag.
- Use available `build-pipeline-engineering` for the packaging interface. Default publication to GitHub Actions Artifacts; repository-configured destinations use one-success by default unless a stricter policy is selected.
- Record publication results per exact commit and destination. Retries skip successful destinations and send only to failed or unattempted destinations.

### Tag identity, ancestry, and recovery

- Tag the exact packaged/published candidate and finalize with a merge commit or a policy-permitted true fast-forward. Reject squash, rebase-and-merge, cherry-pick, and post-package candidate rewriting; an incompatible protected merge policy stops the flow before publication.
- Freshly fetch the remote tag and default branch, compare the peeled tag to the recorded candidate SHA, and require `git merge-base --is-ancestor` before reporting completion or cleaning up. Repeat the check on already-merged retry paths; shallow history, missing Git, fetch failures, mismatched tags, and missing ancestry cannot pass.
- Keep `dev_<version>` through packaging and publication. Delete an untagged failed candidate, but retain an existing tag and all involved branches when merge or finalization verification fails. Repair through a protected PR that preserves the original tagged commit; never move or recreate the tag. Clean up only after verification succeeds and retain the visible publication branch.

## [2.0.0] - 2026-09-04

- Split the former combined Android release workflow into a source-only code train with explicit boundaries around requirement branches, version integration, release promotion, default-branch synchronization, and immutable source tags.
- Moved signing, packaging, artifact verification, and uploads to `build-pipeline-engineering` so code readiness cannot be confused with artifact readiness.
- Scoped branch inventory to the selected GitHub repository, deduplicated matching refs, and treated closed pull requests as development state rather than active integration candidates.
- Added the immutable `android-code-release-train` synchronization ID.
