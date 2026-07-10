# Gradle Plugin Release

Use this reference for Gradle plugins, Android build plugins, or repository plugins.

## Inspect First

Look for:

- `java-gradle-plugin`, `kotlin-dsl`, `com.gradle.plugin-publish`, `maven-publish`.
- `gradlePlugin { plugins { ... } }` blocks.
- Plugin id, implementation class, display name, tags, website, and VCS URL.
- Functional tests using Gradle TestKit.
- Compatibility matrix for Gradle, Kotlin, AGP, and Java.
- Plugin portal or Maven repository credentials.

## Preflight

Before publishing:

- Run unit tests and functional TestKit tests.
- Run `validatePlugins` when available.
- Publish to Maven local and consume from a sample project if practical.
- Confirm plugin id and version are final.
- Confirm docs or release notes mention compatibility limits.

Typical commands:

```bash
./gradlew test functionalTest validatePlugins
./gradlew publishToMavenLocal
```

Use actual task names from the repo.

## Artifact Contract

A plugin release should include:

- Implementation artifact.
- Plugin marker artifact for each plugin id.
- POM metadata.
- Sources/Javadocs if required by destination.
- Signatures/checksums when required.

## Version and Compatibility

- Do not reuse a published plugin version.
- Treat Gradle/AGP/Kotlin compatibility as part of the release contract.
- For Android Gradle Plugin integrations, test at least the repo's minimum supported AGP and the current target AGP when feasible.

## Publishing Destinations

- Gradle Plugin Portal: usually `publishPlugins`; confirm credentials and irreversible version policy.
- Maven/internal repository: use `publish` or repository-specific tasks.
- Local validation: `publishToMavenLocal`.

Remote publish requires explicit user confirmation unless the user already asked to publish that exact plugin/version.
