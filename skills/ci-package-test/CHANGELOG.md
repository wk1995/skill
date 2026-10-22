# Changelog

## [Unreleased]

- No unreleased changes.

## [0.0.1] - 2026-10-22

- Change-Type: initial
- Summary: Introduce platform-independent CI package verification, explicit publication, PR-derived regression cases, and a reusable web test workbench covering plans, rounds, environments and observations.
- Compatibility: New portable Skill with the user-requested initial version 0.0.1; this initial release has not shipped. Renamed from the local draft android-ci-fir-test to ci-package-test while preserving its immutable sync ID. No prior released contract or migration. Ordinary CI archives artifacts; execution and publication follow the requested scope.
- Include acyclic prerequisite-case graphs, recursive dependency ordering, same-round/environment pass guards, exact prerequisite evidence and transitive stale-result detection. Keep original records while requiring fresh dependent validation after upstream retests; expose readiness and concrete prerequisite guidance in UI/AI.
- Clarify target-owned prerequisites versus outcome routing with a combined example and aligned English/Chinese flowcharts; document that current next branches do not support cross-case predicates. No runtime or persisted-format change.
- Include an offline interactive webpage graph with distinct dependency/outcome edges, environment-bound execution states, current/next highlights, failure/staleness markers and read-only case navigation. Export the same graph projection for AI.
- Include optional validated testLocation page/path/control hints, immutable round/annotation snapshots and read-only phone-test handoff copying. Hints remain unverified until matched to the live screen; no device commands or guessed coordinates. Existing hint-free cases/archives remain valid.
- Include explicit outcome-dependent next-test branches, frozen recursive targets, concrete per-environment UI/AI guidance, wait recovery conditions and outcome explanations; pre-execution blocked/skipped deferrals retain null execution time without fabricated starts. Preserve unresolved failures through running/partial/blocked/skipped retests until a same-case/environment pass; retain flat legacy cases without inventing branches.
- Include a shared machine-readable state contract, enforced round/execution lifecycle, append-only start/result/retest events and guarded AI state exports. Preserve legacy observation-only rounds explicitly; managed histories merge by prefix and reject divergence or downgrade.
- Include a working browser-local template with frozen definitions, mandatory smoke coverage, environment-bound append-only observations and JSON import/export.
- Include excerpt/context-pinned web annotations, append-only replies and resolution events, backward-compatible annotation archives, and stable browser-native annotation context without an automatic host/chat transport.
