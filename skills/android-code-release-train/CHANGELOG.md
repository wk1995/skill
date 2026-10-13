# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [3.0.0] - 2026-10-13

- Change-Type: breaking
- Summary: Initialize both source version values when creating a selected integration train, preserve its pre-initialization baseline, and support repositories with or without a lifecycle helper.
- Compatibility: The source-only boundary, requirement-branch behavior, code gates, and immutable tag rules remain; the version-initialization phase changes from release promotion to integration creation.
- Breaking-Change: Previously a new integration branch could retain the default branch's versions until promotion. New trains must contain a verified initialization commit, and pre-created promotion branches must use the recorded baseline.
- Migration: Update project creation commands and CI to initialize and synchronize repository-owned version fields, record the default-branch SHA, and preserve the initial target at promotion. Use equivalent Git/file operations when no helper exists. Validate and reuse legacy trains without rebumping or recreating their established release branches.

## [2.0.0] - 2026-09-04

- Split the former combined Android release workflow into a source-only code train with explicit boundaries around requirement branches, version integration, release promotion, default-branch synchronization, and immutable source tags.
- Moved signing, packaging, artifact verification, and uploads to `build-pipeline-engineering` so code readiness cannot be confused with artifact readiness.
- Scoped branch inventory to the selected GitHub repository, deduplicated matching refs, and treated closed pull requests as development state rather than active integration candidates.
- Added the immutable `android-code-release-train` synchronization ID.
