# Release Engineering

Language: **English** | [中文](README.zh-CN.md)

`release-engineering` helps plan, validate, automate, document, and troubleshoot controlled release workflows. It covers Android apps, Android libraries and SDKs, Gradle plugins, artifacts, release branches and tags, CI gates, publishing, rollback planning, and release aftercare.

## How To Use It

Ask for a release-oriented outcome and provide the repository or release target where possible. Typical prompts include:

```text
Use $release-engineering to create a dry-run plan for releasing this Android app.
Audit the Maven publishing workflow for this Android library.
Troubleshoot why the Gradle plugin release job did not publish an artifact.
```

The skill first identifies the target and operation, inspects the relevant build, CI, version, signing, and publishing configuration, then creates or validates a release contract. It uses the target-specific references only when they apply:

- Android APK/AAB applications
- Android libraries, SDKs, AARs, and Maven components
- Gradle and build plugins
- Enter Flowtime and paired Android/submodule release flows

Remote changes—such as publishing artifacts, pushing tags, creating releases, or changing branch protection—require the user's explicit authorization.

## When It Triggers

Use this skill when the request:

- plans, validates, automates, documents, or debugs a release or publishing workflow;
- concerns Android app/component/plugin releases, artifacts, tags, publish branches, or CI release gates; or
- needs release contracts, dry runs, publishing safety checks, rollback plans, or aftercare.

## When It Does Not Trigger

Do not use this skill when the request:

- only discusses this repository's Skill-management architecture or metadata conventions; or
- is ordinary code editing with no release, publishing, artifact, tag, or release-automation work.

For exact instructions and safeguards, see [SKILL.md](SKILL.md).
