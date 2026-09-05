# Android app build pipeline

Use this reference for APK/AAB build pipelines, build variants, and Android signing configuration. Use the requested variant; default to `release` when none is supplied.

## Inspect first

- Gradle wrapper, Java version, AGP version, repositories, and dependency locks.
- Application module and flavor/build-type matrix.
- `versionName` and `versionCode` sources; verify them but do not edit them here.
- Existing `signingConfig`, environment variables, and CI secret names.
- Existing workflows, Fastlane lanes, repository scripts, and output locations.
- Mapping, native symbols, baseline profiles, and `output-metadata.json` requirements.

## Signing environment

Keep the keystore and passwords in protected CI secrets or an approved secret manager. Materialize the keystore only for the build step, restrict file permissions, and remove it in an always-run cleanup step. Logs must not print secret values, keystore contents, passwords, or encoded material.

Prefer repository-supported Gradle properties or environment variables. Do not add a plaintext `keystore.properties`, JKS/P12 file, or credential to source control.

## Build and verify

Discover actual module, flavor, and build-type task names. Map the requested variant to real Gradle tasks; the following is the default `release` shape:

```bash
./gradlew --no-daemon clean :app:assemble<Flavor>Release :app:bundle<Flavor>Release
apksigner verify --print-certs path/to/app-release.apk
jarsigner -verify path/to/app-release.aab
```

Required outputs commonly include:

- Signed APK and/or AAB requested by the user.
- `output-metadata.json`.
- R8/ProGuard mapping.
- Native symbols or baseline profile outputs when configured.
- Build manifest containing source SHA, source tag if any, version, variant, Gradle/AGP/Java versions, and file checksums.

Verify package/application ID, variant, `versionName`, `versionCode`, signature identity, and checksum before upload.

## GitHub Actions Artifacts default

When configuring GitHub Actions and no destination is supplied, upload only verified outputs with `actions/upload-artifact`. Use a traceable name such as `<app>-<version>-<variant>-<short-sha>`, set an explicit retention period, and fail when required files are absent. Avoid uploading keystores, secret property files, Gradle caches, or unrelated build directories.

## Retry rules

Retry from the same source commit when failure is environmental. If a retry requires a different `versionCode` or source version, stop and request a new source release; this workflow must not modify and commit that value.
