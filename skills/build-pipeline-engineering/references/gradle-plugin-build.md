# Gradle plugin build pipeline

Use this reference for Gradle plugins, Android build plugins, and plugin marker artifacts.

## Inspect first

- `java-gradle-plugin`, `kotlin-dsl`, `com.gradle.plugin-publish`, and `maven-publish` configuration.
- Plugin ID, implementation class, source-declared version, marker publications, and implementation publication.
- TestKit functional tests and Gradle/Kotlin/AGP/Java compatibility matrix.
- Plugin Portal or Maven credentials only when publication is explicitly requested.

## Build and verify

Use repository task names; typical checks are:

```bash
./gradlew --no-daemon test functionalTest validatePlugins
./gradlew --no-daemon publishToMavenLocal
```

Verify the implementation artifact, every plugin marker, POM/module metadata, sources/docs when required, checksums, and compatibility evidence. Consume the local publication from a sample build when practical.

By default in GitHub Actions, upload the verified local publication and manifest to GitHub Actions Artifacts. `publishPlugins` or remote Maven publication is separate and must use the exact already-verified source and version; never change the version or create a tag here, and never reuse an already published version.
