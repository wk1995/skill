# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [2.1.0] - 2026-09-10

- Added Windows EXE/MSI/MSIX and portable packaging, plus Linux DEB/RPM/AppImage/archive workflows, with target architecture, runtime dependencies, signing, and install/upgrade/uninstall verification.
- Expanded build inputs and CI evidence for OS/distribution matrices, native versus cross-build constraints, and preservation of Linux file modes and symlinks in uploaded artifacts.
- Added Windows/Linux packaging triggers and excluded standalone format/certificate explanations; preserved Android behavior, immutable source boundaries, and default CI artifact storage.
- Aligned English/Chinese usage documentation and Codex interface guidance. The synchronization ID remains unchanged.

## [2.0.0] - 2026-09-04

- Extracted reproducible distributable builds from the former combined release workflow into a dedicated Skill with a strict source-ref input boundary.
- Added build-variant selection, protected signing, APK/AAB/AAR/JAR/plugin/native packaging, output verification, manifests, checksums, retention, and upload guidance.
- Added focused references for Android applications and components, Gradle plugins, Enter/Flowtime builds, and paired Android submodule builds.
- Added the immutable `build-pipeline-engineering` synchronization ID.
