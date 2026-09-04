# Enter Flowtime Android build pipeline

Use this reference for `/Users/chengpeng/project/wk/android/Enter-Flowtime-Android` and repositories that retain its packaging conventions. Source branch creation, PR promotion, base synchronization, version edits, tags, and branch cleanup are outside this reference.

## Required source input

Receive an exact reviewed commit or verified source tag from the code lifecycle. If a `publish_*` branch is supplied for a historical workflow, resolve and record its commit SHA before building; never create, update, merge, rebase, or delete that branch here.

## Build

The current application uses the `ApiComFlowtime` flavor. Honor the requested build type and default it to `Release`. For the default APK and AAB outputs:

```bash
./gradlew --no-daemon clean \
  :app:assembleApiComFlowtimeRelease \
  :app:bundleApiComFlowtimeRelease
```

For another requested variant, derive the actual Gradle tasks from the repository instead of substituting strings blindly. Build only the requested output types. Confirm the tasks exist before relying on them. Expected outputs include the requested APK/AAB, `output-metadata.json`, variant-specific mapping when produced, and a manifest/checksum file tied to the exact source SHA.

## Signing and CI

Use protected GitHub Actions secrets when the selected variant requires signing. Do not place keystores or signing properties in source or upload them as artifacts. Verify APK/AAB signatures and version metadata before archive creation.

Upload the verified bundle to GitHub Actions Artifacts by default. Bugly mapping upload may remain non-blocking only when repository policy says so; `BUGLY_APP_KEY` and related values stay in protected secrets.

Packaging, verification, and required artifact upload define this Skill's success. Source tags, default-branch sync, and branch cleanup are owned by the code lifecycle and must not be performed by this pipeline.
