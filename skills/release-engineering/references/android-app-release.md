# Android App Release

Use this reference for APK/AAB app releases.

## Inspect First

Check these files and concepts before proposing steps:

- `settings.gradle`, root `build.gradle`, app/module `build.gradle`.
- Android application module and flavor/buildType matrix.
- `versionName`, `versionCode`, and any `version.properties` or generated version source.
- `signingConfig` and whether CI uses protected secrets.
- CI workflows under `.github/workflows`, Fastlane, Gradle publish tasks, or repo scripts.
- Artifact paths under `app/build/outputs`.
- Crash/symbol upload tools such as mapping upload.

## Release Artifacts

Expected app release artifacts usually include:

- Debug or QA APK when the workflow requires it.
- Signed release APK.
- Signed release AAB.
- `output-metadata.json`.
- R8/ProGuard mapping file, commonly `app/build/outputs/mapping/<variant>/mapping.txt`.

Verify artifact version and signing when tools are available:

```bash
./gradlew clean :app:assemble<Variant>Release :app:bundle<Variant>Release
apksigner verify --print-certs path/to/app-release.apk
jarsigner -verify path/to/app-release.aab
```

Adjust task names to the repo's actual product flavor and build type.

## App Flow Pattern

1. Create or select the version development branch from the base branch.
2. Ensure a protected publish/release branch exists for the same version.
3. Require PR review and a release gate from dev branch to publish branch.
4. Validate source branch naming, version, build number, and rebase/merge feasibility.
5. Build signed artifacts from the publish branch commit.
6. Archive/upload artifacts and metadata.
7. Upload symbols/mapping if configured.
8. Create an immutable tag after artifact upload succeeds.
9. Sync the base branch and clean release branches if the contract allows.

## Version Rules

For app build retries, prefer a monotonic build number encoded in `versionCode`. If the repo uses `major.minor.patch.buildNo`, document the exact encoding and overflow behavior.

Before approving a retry release:

- Confirm whether the previous tag exists.
- Confirm the next build number is expected.
- Confirm the artifact version metadata matches source.

## Common Failure Handling

- Build failure: stop before artifacts, tag, branch sync, and cleanup.
- Artifact upload failure: stop tag/source sync/cleanup.
- Mapping upload failure: continue only if the repository contract says it is non-blocking.
- Tag exists: stop and require a new build number/version.
- Base branch sync conflict: keep release branches and report manual repair.
