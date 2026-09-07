# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- Documented equivalent invocation and safety behavior for WorkBuddy without changing the build workflow.

## [2.0.0] - 2026-09-04

- Extracted reproducible distributable builds from the former combined release workflow into a dedicated Skill with a strict source-ref input boundary.
- Added build-variant selection, protected signing, APK/AAB/AAR/JAR/plugin/native packaging, output verification, manifests, checksums, retention, and upload guidance.
- Added focused references for Android applications and components, Gradle plugins, Enter/Flowtime builds, and paired Android submodule builds.
- Added the immutable `build-pipeline-engineering` synchronization ID.
