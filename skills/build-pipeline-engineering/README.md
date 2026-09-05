# Build Pipeline Engineering

Language: **English** | [中文](README.zh-CN.md)

`build-pipeline-engineering` configures and operates reproducible distributable-build pipelines from an exact source ref, including build-variant selection, environment setup, signing, packaging, verification, and output upload. For targets with variants, the default is `release`; in GitHub Actions, the default output destination is GitHub Actions Artifacts.

## How To Use It

Provide the repository and source tag/commit when known, plus the desired artifact or variant:

```text
Use $build-pipeline-engineering to configure CI for a signed Android release AAB.
Build the tagged source with the qa variant and upload its APK to GitHub Actions Artifacts.
Audit this AAR pipeline's signing, checksums, and retention.
Troubleshoot why the Gradle plugin artifact is missing from the workflow run.
```

The Skill inspects the build system and CI, defines exact inputs and outputs, keeps signing material in protected secrets, verifies artifacts, and records source SHA, manifests, checksums, destination, and retention. See [SKILL.md](SKILL.md) for the detailed build contract.

## When It Triggers

Use this Skill for CI build configuration, build variants, signing environments, distributable packaging, APK/AAB/AAR/JAR/plugin/native outputs, verification, checksums, manifests, retention, GitHub Actions Artifacts, or an explicitly requested destination. If no variant is provided, it uses `release`.

## When It Does Not Trigger

Do not use this Skill to implement a requirement, select code for an Android version, create or promote source branches and PRs, change source version files, merge code, or create release tags. Use `android-code-release-train` for that lifecycle. Ordinary compile/test checks that retain no distributable release output also do not trigger it.
