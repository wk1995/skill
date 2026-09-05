# Android component build pipeline

Use this reference for Android libraries, SDK modules, AARs, Maven components, and their build evidence.

## Inspect first

- Modules using `com.android.library`, `maven-publish`, `signing`, Dokka/Javadoc, or repository build scripts.
- Maven coordinates and publication names already declared by source.
- Consumer ProGuard rules, manifest entries, resources, native libraries, and transitive dependencies.
- Public API/binary compatibility tasks and supported Android/Java/Kotlin toolchains.
- Target repository only when the user requests publication beyond the default GitHub Actions artifact archive.

## Build and local validation

Use actual module and task names. A common validation sequence is:

```bash
./gradlew --no-daemon :module:test :module:lint :module:assembleRelease
./gradlew --no-daemon :module:publishToMavenLocal
```

The artifact contract may require:

- AAR or JAR.
- POM with correct dependencies.
- Gradle module metadata.
- Sources and Javadoc/Dokka archives.
- Consumer rules, native payloads, signatures, and checksums.
- A manifest tying coordinates and files to the exact source commit.

Inspect the AAR/JAR contents and the locally published metadata before upload. Do not change coordinates or source version files from the artifact workflow.

## Destination

With GitHub Actions and no explicit publish destination, archive the verified component bundle in GitHub Actions Artifacts. Publishing to Maven, Nexus, Artifactory, GitHub Packages, or Central is an additional explicitly requested action; reject attempts to overwrite an existing immutable version.
