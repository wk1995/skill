# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- Documented equivalent invocation and safety behavior for WorkBuddy without changing the release workflow.

## [2.0.0] - 2026-09-04

- Split the former combined Android release workflow into a source-only code train with explicit boundaries around requirement branches, version integration, release promotion, default-branch synchronization, and immutable source tags.
- Moved signing, packaging, artifact verification, and uploads to `build-pipeline-engineering` so code readiness cannot be confused with artifact readiness.
- Scoped branch inventory to the selected GitHub repository, deduplicated matching refs, and treated closed pull requests as development state rather than active integration candidates.
- Added the immutable `android-code-release-train` synchronization ID.
