# Android Component Release

Use this reference for Android libraries, SDK modules, AARs, or Maven-published components.

## Inspect First

Look for:

- Modules using `com.android.library`, `maven-publish`, `signing`, Dokka/Javadoc, or custom publish scripts.
- Maven coordinates: `groupId`, `artifactId`, `version`.
- Publication names and repositories.
- Public API surface and binary compatibility checks.
- Consumer ProGuard rules, manifest entries, resources, native libs, and transitive dependencies.
- Release notes or changelog expectations.

## Preflight

Before publishing a component:

- Confirm the module is meant to be public/internal and identify the target repository.
- Run unit tests and relevant Android instrumentation checks if available.
- Run lint and API/binary compatibility checks if the repo has them.
- Build and inspect the AAR.
- Publish to local Maven first when possible.

Typical commands:

```bash
./gradlew :module:test :module:lint :module:assembleRelease
./gradlew :module:publishToMavenLocal
```

Use actual module names and task names from the repository.

## Artifact Contract

A component release should account for:

- AAR/JAR.
- POM with correct dependencies.
- Gradle module metadata when enabled.
- Sources and Javadoc/Dokka artifacts if required.
- Signatures and checksums for public repositories.

## Versioning

Use SemVer unless the repository defines a different policy:

- Patch: compatible bug fix.
- Minor: backwards-compatible API addition.
- Major: breaking API or behavior change.
- Pre-release: alpha/beta/rc artifacts should publish to an appropriate channel.

Do not overwrite an already published component version. Create a new version instead.

## Publishing Destinations

- `publishToMavenLocal`: validation only.
- Internal Maven/Nexus/Artifactory/GitHub Packages: check repository credentials and permissions.
- Maven Central: use staging/close/release flow and signing.

If repository publishing is remote and irreversible, require explicit user confirmation before running it.
