# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [3.0.0] - 2026-10-13

- Change-Type: breaking
- Summary: Initialize both source version values when creating a selected integration train, preserve its pre-initialization baseline, and support repositories with or without a lifecycle helper.
- Compatibility: The source-only boundary, requirement-branch behavior, code gates, and immutable tag rules remain; the version-initialization phase changes from release promotion to integration creation.
- Breaking-Change: Previously a new integration branch could retain the default branch's versions until promotion, and accepted release code merged to the default branch before distribution. New trains must contain a verified initialization commit. Publication defaults to a protected publish_<version> branch resolved only from publish_template, which a repository may replace. The version is major.minor.patch. That branch must be rebased onto the default branch, pushed through its protected path, rechecked, packaged when CI packaging exists, and accepted by at least one publish implementation before it is tagged and merged back.
- Migration: Keep the visible publication branch in pull requests and protect it against direct pushes. After its dev PR merges, rebase that result onto a hidden release candidate and delete that candidate after both success and failure. Treat packaging and publication as interfaces: no packaging implementation passes, while available build-pipeline-engineering supplies packaging. Publication defaults to GitHub Actions Artifacts when no destination is configured; otherwise keep one-success unless another policy is required. Retries of the same commit are idempotent and must not resend it to a destination already recorded as successful. Supply a major.minor.patch version; names and partial versions such as latest, 1, or 1.4 are rejected at selection, initialization, reuse, and tagging. Resolve the visible branch only from publish_template, defaulting to publish_<version>, and do not apply a separate prefix. Apply a permitted build-number adjustment only on the hidden candidate after the rebase, then rerun its gates before packaging. When the default-branch merge fails after the tag exists, keep that tag and every branch, continue through a protected pull request, and do not recreate the tag. Delete dev/<version> only after the tag is verified and the default-branch merge succeeds; keep it when publication fails. Update creation commands and CI to initialize repository-owned version fields without assuming Android metadata, record the default-branch SHA, and preserve the initial target. Use equivalent Git/file operations when no helper exists. Validate and reuse legacy trains without rebumping or recreating their established publication branches.

## [2.0.0] - 2026-09-04

- Split the former combined Android release workflow into a source-only code train with explicit boundaries around requirement branches, version integration, release promotion, default-branch synchronization, and immutable source tags.
- Moved signing, packaging, artifact verification, and uploads to `build-pipeline-engineering` so code readiness cannot be confused with artifact readiness.
- Scoped branch inventory to the selected GitHub repository, deduplicated matching refs, and treated closed pull requests as development state rather than active integration candidates.
- Added the immutable `android-code-release-train` synchronization ID.
