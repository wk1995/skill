# Android CI FIR Test

Language: **English** | [简体中文](README.zh-CN.md)

`android-ci-fir-test` connects Android FIR-channel CI packaging, PR-derived regression cases, and optional device testing with reusable test rounds. Ordinary CI archives artifacts only; uploading to FIR requires an explicit publication request. The initial Skill version is `0.0.1`.

## How To Use It

Provide the repository, source ref, and related PR when known. Request only the stages you need:

```text
Build a FIR-channel Release test APK from dev_5.1.3 through CI and give me regression cases for PR #44.
Publish the verified package from CI run <run-id> to FIR.
Install that CI APK on my connected test phone and execute the prepared short tests.
Prepare the next test round: failed cases first, all smoke cases, then cases derived from the release PR diff.
```

The first prompt builds and archives the package without publishing. The second explicitly authorizes FIR publication. Installation and testing run only when requested. Release is the default build type; requested variants take precedence. Existing test workbenches are reused, and each observation records its registered device and execution time while preserving history.

See [SKILL.md](SKILL.md) for the procedure, [CI and publication](references/ci-and-publication.md) for source/artifact checks, and [test rounds](references/test-rounds.md) for cases, devices, and result handling. Example branch names and PR numbers are not defaults.

## When It Triggers

- CI packaging of a FIR-channel Android test APK from a selected source ref.
- PR-derived regression cases for that package, with optional explicitly requested FIR publication.
- Follow-up installation, device tests, or repeat rounds in the same package-testing workflow.

## When It Does Not Trigger

- Local-only Gradle builds or local FIR uploads without CI.
- Generic CI or Google Play, SDK, AAR, or plugin packaging without this FIR test workflow.
- Standalone test-workbench development or unrelated QA planning.
- Source version changes, branch promotion, code fixes, PR creation, merging, or tagging without a separate request.

This Skill does not automatically build a web app, install a package, or repair defects merely because a CI package or case list was requested.
