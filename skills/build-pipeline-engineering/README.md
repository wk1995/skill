# Build Pipeline Engineering

Language: **English** | [中文](README.zh-CN.md)

`build-pipeline-engineering` configures and operates reproducible distributable-build pipelines for Android, Windows, Linux, and plugins from an exact source ref. It covers build variants, installer/package selection, environment setup, signing, runtime dependencies, installation verification, and output upload. For targets with variants, the default is `release`; in GitHub Actions, the default output destination is GitHub Actions Artifacts.

## How To Use It

Provide the repository and source tag/commit when known, plus the desired artifact or variant:

```text
Use build-pipeline-engineering to configure CI for a signed Android release AAB.
Build the tagged source with the qa variant and upload its APK to GitHub Actions Artifacts.
Audit this AAR pipeline's signing, checksums, and retention.
Troubleshoot why the Gradle plugin artifact is missing from the workflow run.
Package this commit as a Windows x64 MSI with silent installation and upgrade checks.
Build a Windows EXE installer and a portable ZIP; label this internal test build unsigned.
Package this tag for Ubuntu 22.04 amd64 as DEB and AppImage, and verify runtime dependencies.
Configure Linux x86_64/ARM64 RPM and tar outputs with checksums in GitHub Actions Artifacts.
```

The Skill inspects the build system and CI, defines exact inputs and outputs, keeps signing material in protected secrets, verifies artifacts, and records source SHA, manifests, checksums, destination, and retention. See [SKILL.md](SKILL.md) for the detailed build contract.

For Windows/Linux, provide the stack/build command if known, target OS or distribution versions, architecture, installer versus portable format, application metadata/assets, runtime bundling, install scope, upgrade/uninstall expectations, and signing requirements. Existing repository configuration supplies defaults; missing choices that affect delivery are clarified before packaging. Windows outputs include EXE installers, MSI, MSIX, and portable bundles; Linux outputs include DEB, RPM, AppImage, and tar archives. An application EXE alone is not necessarily an installer.

Public Windows signing uses a trusted code-signing provider or an existing signing service; self-signed certificates require controlled target trust. An unsigned test build is recorded explicitly and cannot satisfy a signed-release requirement. Installation and upgrade checks run in disposable target environments; checks that cannot run are reported as unverified. See the [Windows](references/windows-app-build.md) and [Linux](references/linux-app-build.md) guides for platform details.

## When It Triggers

Use this Skill for CI build configuration, build variants, signing environments, distributable packaging, APK/AAB/AAR/JAR/plugin/native outputs, Windows installers/portable bundles, Linux packages/archives, runtime dependency and installation checks, checksums, manifests, retention, GitHub Actions Artifacts, or an explicitly requested destination. For targets with variants, if none is provided, it uses `release` (or the build system's equivalent).

## When It Does Not Trigger

Do not use this Skill to implement a requirement, select code for an Android version, create or promote source branches and PRs, change source version files, merge code, or create release tags. Use `android-code-release-train` for that lifecycle. Ordinary compile/test checks that retain no distributable release output also do not trigger it.

Standalone EXE-versus-MSI explanations or certificate advice without a build task do not trigger it. Requests that only manage Skill copies or metadata belong to `sync-skills`.
