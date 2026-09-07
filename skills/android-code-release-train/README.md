# Android Code Release Train

Language: **English** | [中文](README.zh-CN.md)

`android-code-release-train` governs the Android code lifecycle from a requirement branch through version integration and release promotion to a reviewed source commit and immutable tag. It does not build, sign, package, or upload release artifacts.

## How To Use It

Provide the repository, requirement or branch names, version, and desired source stage when known:

```text
Use android-code-release-train to create a feature branch for this Android requirement.
Select feature/login and feature/report for dev/1.4.0.
Show which requirement PRs are ready for code integration.
Promote the approved code to release/1.4.0 and finalize its source tag.
```

The Skill resolves the default branch, holds requirement branches until a version is selected, checks PR readiness, promotes reviewed code, updates repository-owned version metadata, synchronizes the default branch, and creates the immutable source tag. See [SKILL.md](SKILL.md) for the operational contract.

## When It Triggers

Use this Skill for Android requirement branches, version scope selection, `dev/<version>` and `release/<version>` integration, code gates, source version metadata, default-branch synchronization, or source tags.

## When It Does Not Trigger

Do not use this Skill to configure or run signing, APK/AAB/AAR packaging, checksum generation, output retention, GitHub Actions artifact uploads, store delivery, or Maven/plugin publication. Use `build-pipeline-engineering` for those requests. It also does not trigger for ordinary code editing without the version-train lifecycle.
