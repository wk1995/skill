# Release Model

Use this reference when designing a new release workflow or extending beyond the existing Android app flow.

## Target Types

| Target | Typical artifact | Typical destination | Key risk |
| --- | --- | --- | --- |
| Android app | APK, AAB, mapping.txt, metadata | App store, GitHub Artifact, internal QA | signing, versionCode, store rollout |
| Android component | AAR, POM, Gradle module metadata, sources/javadocs | Maven local/internal/Central/GitHub Packages | binary/API compatibility, coordinates |
| Gradle plugin | plugin marker, implementation jar, POM | Gradle Plugin Portal, Maven | plugin id/version compatibility |
| Repository release | archive, generated bundles, tag | GitHub Release/Artifacts | tag/source mismatch |
| Other platform | package-specific | package-specific | missing target-specific gates |

## Durable Invariants

- The released artifact must be traceable to one source commit.
- The version in source, artifact metadata, and tag must agree.
- Protected release branches should accept code only through the approved path.
- Tags should not be overwritten.
- Credentials must come from protected secret stores.
- Cleanup must happen after traceability is secured, not before.

## Release Contract Checklist

Use this checklist before writing or changing workflow logic:

- What branch or PR proves the release was reviewed?
- What file is the version source of truth?
- How are retry builds represented: new build number, new patch, or new tag?
- What artifacts are mandatory?
- What exact build tasks produce those artifacts?
- What validation proves artifact correctness?
- What remote mutations happen, in order?
- Which step is the success point?
- Which aftercare steps can fail without invalidating the release?
- What manual repair procedure is safe after partial failure?

## Versioning Guidance

- Apps often need monotonically increasing platform-specific build numbers.
- Libraries and plugins should default to SemVer unless the repo already defines a different scheme.
- Re-release of the same library/plugin version should generally be rejected; create a new patch/pre-release version instead.
- Re-release of an app version can use a build number increment if store/platform policy allows it.

## Failure Semantics

Classify each step:

- **Blocking before release:** failed tests, version mismatch, missing signing, missing credentials, incompatible branch source.
- **Release success point:** artifact creation or artifact publication, depending on the repository contract.
- **Aftercare:** tag, base branch sync, branch cleanup, comments, notifications.
- **Non-blocking telemetry:** symbol upload or notification, only if explicitly safe to continue.

Do not assume aftercare failure means the release failed. Report the exact boundary.
