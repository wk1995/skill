---
name: android-ci-fir-test
description: Build an Android FIR-channel test package through CI, derive regression cases from a PR, and continue the same workflow through device testing and reusable test rounds. Ordinary CI archives artifacts only; publish to FIR only when explicitly requested. Excludes local-only packaging and unrelated test-workbench development.
metadata:
  sync_id: "android-ci-fir-test"
  version: "0.0.1"
  triggering:
    include:
      - Build a FIR-channel Android test APK through CI from a specified branch, tag, or commit, with Release as the default build type.
      - Generate regression cases from a PR for that FIR-channel CI package.
      - Explicitly publish the verified CI package to FIR through a separate publishing workflow.
      - Continue this Android test-package workflow by installing the package, executing device tests, or preparing and recording subsequent test rounds.
    exclude:
      - Local-only Gradle packaging or local FIR upload without CI.
      - Generic CI, Google Play, SDK, AAR, or Gradle plugin packaging without the FIR-channel test workflow.
      - Standalone test-workbench design or development, or unrelated QA planning without this package-testing context.
      - Source version changes, release-branch promotion, code fixes, PR creation, merging, or tagging unless separately requested.
---

# Android CI FIR Test

Connect a verified FIR-channel CI APK with PR-derived regression cases and, when requested, device observations. Keep the source commit, package, case definitions, execution rounds, and device identity traceable.

## Establish the requested scope

Inspect repository instructions, build configuration, existing workflows, and current worktree. Determine the source ref, Android module/flavor, build type (default `release`), related PR, and requested stages. Infer existing configuration before asking for missing inputs; never silently pick another branch or fabricate a PR.

Treat “CI 打个 FIR 测试包” as a FIR-channel build whose outputs stay in CI artifacts. The channel name, a Release variant, or successful CI does not authorize FIR publication. An explicit request to publish/upload to FIR authorizes the separate publication stage; honor existing authorization without asking again. Building or writing cases alone does not authorize device installation, execution, code fixes, or creation of a test web app.

## Build and verify

Read [references/ci-and-publication.md](references/ci-and-publication.md) before dispatching CI or publishing.

1. Resolve the requested remote ref to a commit. If switching the checkout was requested, preserve local changes and switch safely; remote CI alone does not require changing the local checkout.
2. Inspect the workflow and its called actions/scripts at the relevant ref. Choose the packaging entry point that only archives outputs. Check the active CLI account and repository before any remote write.
3. Dispatch with the verified inputs, identify the exact run, and compare its actual checkout SHA with the intended source. Track that run to completion. A failed, skipped, mismatched, or ambiguous run is not a usable package.
4. Verify the APK identity, versionName/versionCode, expected signing certificate, checksum, required mapping/metadata, and repository-specific checks. Record artifact names and actual retention. Static checks such as 16 KB compatibility do not establish runtime coverage.
5. If publication is requested, use a separate publishing workflow consuming this same verified artifact. Verify publication evidence before reporting a FIR link. Otherwise return the CI run and artifacts as the package handoff.

Reuse the repository build contract; do not change source versions, bypass trusted-ref checks, or create release tags to force a package through. Missing configuration or credentials is a concrete blocker, not permission to replace production signing with debug signing.

## Prepare and continue regression testing

Read [references/test-rounds.md](references/test-rounds.md) when generating cases, installing an APK, executing tests, or recording a later round.

- Read the complete PR diff at exact base/head commits, including affected callers. Confirm which changes are present in the packaged source; label cases for absent changes as blocked rather than testing a different package silently.
- Write stable case IDs, priorities, multiple applicable test types, prerequisites, steps, expected results, and evidence expectations. Initial results remain pending. Derive cases from the actual diff; do not copy a historical project's case count or scenarios as universal requirements.
- For each new round, include prior failed cases first, all current smoke cases, PR-change cases, then optional unfinished cases; deduplicate by ID. Include smoke even after a passed round or an empty diff. Missing smoke coverage requires defining it before starting the round.
- Keep version → plan → round organization. Separate case definitions from append-only observations. Register and select a device before saving results; preserve the device/configuration snapshot in each observation.
- Reuse an existing test-workbench template when available. A new suite is data, not a reason to generate another web app. Use its supported interface and validate round/device/revision context before saving; do not overwrite historical snapshots.
- Execute only requested stages. Preserve app data during installation, distinguish automation failures from product defects, and report passed, failed, partially executed, blocked, and untested cases honestly. Hardware, long-duration, channel, and OS-specific requirements remain uncovered until exercised.

## Handoff

Report the resolved source SHA, package variant/version, CI run, artifact names/retention, signature and checksum evidence, and publication outcome only if requested. Link the case plan or existing workbench when one was prepared. For executed tests, include round, device configuration, counts by result, confirmed defects with evidence, and remaining coverage. A CI success is not a complete regression pass.

Historical branches, workflow names, application IDs, devices, and durations from an example conversation are discovery clues. Read the current repository rather than hard-coding them.
