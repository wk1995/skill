---
name: release-engineering
description: Use when planning, validating, automating, documenting, or troubleshooting release/publish/发布/发包 workflows for Android apps, Android libraries/components, Gradle plugins, publish branches, tags, artifacts, CI gates, or when extending release workflows beyond Android.
metadata:
  version: "1.0.0"
---

# Release Engineering

## Overview

Use this skill to handle releases as controlled workflows that bind source, version, artifacts, publishing destination, tags, and aftercare. Do not treat release work as only running a build command.

## Start Here

1. Identify the release target: Android app, Android component/library, Gradle plugin, repository workflow, or other platform.
2. Identify the operation: design a process, document an existing process, dry-run, validate, publish, troubleshoot, or extend automation.
3. Inspect the repository before deciding: build files, version source, CI workflows, publish scripts, signing/credential references, branch protections, tags, and artifact outputs.
4. If the next step mutates remote state, state the exact action first. For git/GitHub pushes, tags, PRs, branch protection, or releases, use `git-account-safety`.

## Reference Router

- For cross-target release design, read `references/release-model.md`.
- For Android APK/AAB app releases, read `references/android-app-release.md`.
- For Android library, SDK, AAR, or Maven component releases, read `references/android-component-release.md`.
- For Gradle plugin or build-plugin releases, read `references/gradle-plugin-release.md`.
- For this workspace's PR-driven Enter Flowtime flow, or repos with `dev_*`, `publish_*`, and `scripts/release_flow.py`, read `references/enter-flowtime-release.md`.
- For Android SDK releases that coordinate a parent AAR repo with a child/submodule repo that produces SO or other lower-level artifacts, paired `*/dev_V` and `publish_V` branches, and cross-repo artifacts, read `references/paired-android-submodule-release.md`.

Load only the relevant reference files. If the request spans targets, read `release-model.md` first, then the target references.

## Release Contract

Before performing or approving a release, establish this contract:

- **Source:** branch/ref/commit and whether it came through review.
- **Paired repos:** for parent/child or submodule releases, include both the parent commit and the exact child commit recorded by the parent; child branch names must come from repository configuration or scripts, not hard-coded assumptions.
- **Version:** version name, build number/code, tag format, and source file.
- **Artifacts:** exact files expected, metadata, mapping/symbol files, checksums if required.
- **Destination:** store, artifact repository, GitHub Artifact/Release, Maven, plugin portal, or internal channel.
- **Gates:** tests, PR checks, approval, branch protection, compatibility checks, signing checks.
- **Credentials:** which secret/variable names are required; never add plaintext credentials.
- **Success point:** what marks release success, and which steps are aftercare.
- **Failure policy:** what stops immediately, what can warn and continue, and what must be manually repaired.

## Execution Pattern

1. **Preflight:** verify clean worktree if local, branch naming, version consistency, required secrets, destination access, and no unexpected open PRs or conflicts.
2. **Build or package:** run the target-specific build and collect deterministic outputs.
3. **Verify artifacts:** confirm expected files exist, version matches, signing is present where required, and metadata/mapping files are included.
4. **Publish or archive:** upload artifacts to the intended destination. Prefer dry-run/local publish first when available.
5. **Tag and sync source:** create tags only after publish/archive success unless the repository's contract says otherwise.
6. **Aftercare:** sync base branches, clean release branches, update comments/changelogs, and report what succeeded or stopped.

## Default Safety Rules

- Do not push, tag, delete branches, publish to a repository, upload to a store, or change branch protection unless the user explicitly asked for that remote mutation or confirmed it.
- Prefer dry-run commands for first passes: `publishToMavenLocal`, staging repositories, CI validation jobs, or script `--dry-run` flags.
- Keep release scripts and CI as the source of truth when they exist; do not invent parallel manual steps without explaining why.
- Treat "build success" and "release success" according to the repository contract, not by assumption.
- If a cleanup step fails after artifacts are published, preserve traceability and report the manual repair path instead of retrying destructive operations blindly.

## Output Shape

For a release plan or audit, return:

- Current flow summary.
- Required human actions.
- Automated workflow steps.
- Preconditions/secrets.
- Failure handling.
- Commands or file references for the next concrete action.

For a completed release action, report:

- Source commit/ref.
- Version and tag.
- Artifacts produced or uploaded.
- Destination.
- Aftercare status.
- Anything skipped, failed, or requiring manual follow-up.
