# Build pipeline model

Use this reference when designing a new build pipeline or when the target does not fit a more specific reference.

## Target types

| Target | Typical outputs | Default CI destination | Key risk |
| --- | --- | --- | --- |
| Android app | APK, AAB, mapping, metadata | GitHub Actions Artifacts | signing, variant, `versionCode` |
| Android component | AAR, POM, module metadata, sources/docs | GitHub Actions Artifacts | coordinates and dependency metadata |
| Gradle plugin | implementation JAR, marker, POM | GitHub Actions Artifacts | marker and compatibility mismatch |
| Native component | SO/framework/archive, manifest | GitHub Actions Artifacts | toolchain and ABI mismatch |
| Other package | platform-specific bundle | GitHub Actions Artifacts | missing target-specific validation |

An explicitly requested registry, store, or repository overrides the default destination, but it does not change the source boundary.

## Durable invariants

- Resolve the requested source ref to one exact commit and record it in build evidence.
- Honor the requested build variant. When no variant is supplied, use `release` and report that default explicitly.
- Read version identity from source or declared build inputs; never commit version changes from this workflow.
- Pin the toolchain and use repository-owned build scripts when available.
- Load credentials only from protected secret stores and never expose them in logs or artifacts.
- Build once, verify once, and upload that verified output rather than rebuilding per destination.
- Generate a manifest and checksums sufficient to connect each output to source, variant, toolchain, and workflow run.
- An artifact workflow may consume a tag but never creates, moves, or deletes source tags or branches.

## Contract checklist

- Which commit or tag is the immutable input?
- What runner, toolchain, dependency locks, and cache keys are required?
- What exact task or script produces each output?
- Which variant, ABI, flavor, or publication is expected? If omitted, has `release` been recorded as the default?
- Which secrets and protected environment provide signing?
- How are signature, metadata, and artifact version verified?
- Which companion outputs—mapping, symbols, POM, module metadata, manifest—are mandatory?
- What artifact name and retention period are used in GitHub Actions Artifacts?
- Which failures are blocking, and which optional uploads may warn?

## Failure semantics

- Source-ref mismatch, missing toolchain, build failure, signature failure, or required-output mismatch blocks upload.
- Upload failure means the artifact run is incomplete even if local packaging succeeded.
- Optional telemetry or symbol upload may warn only when repository policy explicitly makes it non-blocking.
- A retry uses the same resolved source commit. If a source version change is required, stop and return it to the source lifecycle.
