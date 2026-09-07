---
name: build-pipeline-engineering
description: Configure, validate, run, and troubleshoot reproducible distributable builds from an exact source ref, including CI environments, user-selected build variants, Android signing, APK/AAB/AAR or plugin packaging, output verification, manifests, checksums, and uploads. For variant-based builds default to release; for CI output default to GitHub Actions Artifacts. Do not use for requirement branches, PR integration, source version changes, or tag creation.
metadata:
  sync_id: "build-pipeline-engineering"
  version: "2.0.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/build-pipeline-engineering
  triggering:
    include:
      - The user asks to configure or troubleshoot CI that builds, signs, packages, verifies, or uploads software outputs for a selected build variant.
      - The task produces APK, AAB, AAR, JAR, Gradle plugin, native, mapping, metadata, checksum, or archive outputs from a specified source ref.
      - The user asks to build a signed Android package or store build outputs in GitHub Actions Artifacts or another explicit destination.
    exclude:
      - The task selects Android requirements for a version, creates feature/dev/release branches or PRs, changes source version metadata, merges code, or creates release tags; use android-code-release-train for that source lifecycle.
      - The request is a normal compile or test used only to validate a code edit and does not retain a distributable artifact.
      - The request only manages copies or metadata of Skills; use sync-skills instead.
---

# Build Pipeline Engineering

Turn one exact source ref and build variant into verified, traceable outputs. This Skill owns build environments, CI configuration, variant selection, packaging, signing, validation, manifests, checksums, retention, and uploads. It does not own how source code reaches that ref.


## Platform Compatibility

This skill is written to run in both OpenAI Codex and WorkBuddy.

- **Codex**: user-level skills live under `$CODEX_HOME/skills` or `~/.codex/skills`; the agent interface is `agents/openai.yaml`; Codex uses `metadata.triggering` and the `$build-pipeline-engineering` invocation syntax, and Codex-specific artifacts include `agents/` and `extensions.yaml`.
- **WorkBuddy**: WorkBuddy reads `SKILL.md` directly, triggers automatically from the `description` field, and ignores `agents/openai.yaml`. Its installed-Skill directory is product-configured: domestic builds commonly use `~/.workbuddy/skills`, while WorkBuddy AI/overseas builds may use `~/.workbuddy-ai/skills`. Import through WorkBuddy or use the directory configured by the installed product. No `$`-prefix is needed.

When copying this skill to WorkBuddy, treat `SKILL.md` as the required file and copy `agents/`/`extensions.yaml` only when they exist.

## Boundary Contract

Input:

- Repository and immutable commit SHA or verified tag. A branch is acceptable only when the user explicitly requests a branch build; record the resolved commit.
- Output target and build variant. Use the requested variant; default to `release` only when none is supplied.
- Build/version metadata already present in source or supplied as non-source build inputs.

Output:

- Exact build command and environment.
- Produced artifact paths, identity, signatures, metadata, and checksums.
- Upload destination and retention evidence.
- Source-ref-to-artifact traceability.

If the required source ref, version commit, branch promotion, or tag does not exist, stop at that boundary and use `android-code-release-train` for an Android code train. Never create or modify a source branch, PR, version file, merge, or tag to make an artifact build proceed.

## Start Here

1. Identify the output target, source ref, local or CI execution environment, requested build variant, and signing requirements. Default the variant to `release` when omitted.
2. Inspect build files, wrapper/toolchain versions, CI workflows, output paths, and existing secret references.
3. Read only the applicable reference:
   - [references/build-pipeline-model.md](references/build-pipeline-model.md) for a new or cross-target pipeline.
   - [references/android-app-build.md](references/android-app-build.md) for APK/AAB and Android signing.
   - [references/android-component-build.md](references/android-component-build.md) for AAR, SDK, Maven, or component outputs.
   - [references/gradle-plugin-build.md](references/gradle-plugin-build.md) for Gradle plugin outputs.
   - [references/enter-flowtime-build.md](references/enter-flowtime-build.md) for the Enter Flowtime packaging conventions.
   - [references/paired-android-submodule-build.md](references/paired-android-submodule-build.md) for parent/child builds with pinned native outputs.
4. Establish the build contract before changing CI or running the selected build.

## Artifact Build Contract

- **Source:** immutable commit/tag and checkout verification.
- **Toolchain:** runner OS, Java/Gradle/AGP or other versions, caches, and dependency locks.
- **Build inputs:** module, requested variant (default `release`), tasks, and permitted non-source parameters.
- **Signing:** secret names, protected environment, keystore/certificate identity, and verification command. Never print or commit secrets.
- **Outputs:** exact paths and required companion files such as mapping, POM, metadata, or symbols.
- **Identity:** version read from source and any build/run number; verify rather than edit source.
- **Integrity:** signature checks, checksums, manifest, and source SHA embedded in build evidence.
- **Destination:** GitHub Actions Artifacts by default for CI, including artifact name and retention; use another destination only when explicitly requested or already configured.
- **Failure policy:** which missing or invalid output stops the job and which optional telemetry may warn.

## Configure CI

Prefer repository-owned workflows and scripts. For a new GitHub Actions pipeline with no requested destination, expose or honor the requested variant and default it to `release`:

1. Check out the requested ref and record `git rev-parse HEAD`.
2. Install the pinned toolchain and restore safe caches.
3. Load signing material only from protected Actions secrets or environments.
4. Build once, verify the outputs and signatures, and generate a manifest plus checksums.
5. Upload the verified files with `actions/upload-artifact`, using a traceable name and explicit retention.

Do not add branch creation, PR management, version commits, merging, or tag creation to an artifact workflow. A tag-triggered workflow may consume a tag but must never create, move, or delete it.

## Execute or Troubleshoot a Build

1. Resolve the requested ref to an exact commit and ensure the worktree or CI checkout matches it.
2. Run the repository's existing build entry point; do not invent a parallel build path without explaining why.
3. Verify every required artifact exists, has the expected version/variant, and is signed when required.
4. Generate or validate the build manifest and checksums.
5. Upload exactly those verified files. Do not rebuild separately for another destination.
6. Report source ref, commands, artifacts, signatures, checksums, destination, retention, and any skipped or failed checks.

For Android app retries, preserve the source ref. If a higher `versionCode` requires a source change, stop and return that work to the source lifecycle instead of editing it here.

## Remote-Write Safety

Configuring a workflow in the requested repository is an implementation change. Dispatching remote CI, uploading to a registry/store, or replacing retention settings is a separate remote action: state the exact run and destination before doing it and require that it is within the user's request.

Follow `git-account-safety` for repository and GitHub operations. Never expose signing material, overwrite an immutable published version, silently change the source ref, or claim success without verifying uploaded artifact evidence.

## Output Shape

For a pipeline plan or audit, report the source input, build matrix, signing setup, outputs, default or explicit destination, required secrets, validation, and failure behavior.

For an executed build, report the resolved source commit, run URL or local environment, produced files, verification results, checksums/manifest, upload destination, retention, and anything requiring follow-up.
