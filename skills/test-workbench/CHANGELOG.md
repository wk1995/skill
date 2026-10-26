# Changelog

## [Unreleased]

- No unreleased changes.

## [0.0.4] - 2026-10-26

- Change-Type: fix
- Summary: Make existing evidence-based acceptance concrete: reject empty or incomplete runs as proof of a pass, verify the complete tested component combination, and retain requirement/check/environment coverage. Clarify assessment versus implementation scope and user/project/build-default precedence.
- Compatibility: User-requested patch upgrade from 0.0.3 to 0.0.4. Preserves trigger boundaries, bundled runtime/UI, archive schema 1, workflow version 1, conclusion format/version, storage adapters, historical records and project integrations. Existing valid archives require no migration; no new persisted fields, statuses or universal device/measurement prerequisites are introduced.
- Add focused execution-quality guidance for independent oracles, invalid-attempt handling and bounded retries, App/BT/ISP/schema provenance, case-level runner result mapping, compatible measurement baselines, observer/resource/cleanup sequencing and relevant cross-language protocol checks. Distinguish these agent procedures from adapters that need project implementation and verification; retain current all-pairs environment semantics and deterministic conclusions.
- Align English/Chinese usage, reference routing and current-version documentation. Assessment requests return findings/examples without creating a website or operating devices. Product/runner fixes, test-data migration, CI dispatch and external publication remain within the separately requested stages.

## [0.0.3] - 2026-10-24

- Change-Type: fix
- Summary: Improve workbench UI adoption with complete definition-editing entry points, frozen next-test previews, round-wide annotation review and separate AI state export; restore the priority editor, reduce template header/card spacing and expose the selected workspace view.
- Compatibility: User-requested version 0.0.3. Preserves triggers, data schemas, source ownership, managed workflow/history, existing project current-result policies and all project adapters. Existing rounds remain frozen; AI export stays read-only and is distinct from a recovery archive. No migration or external publication is performed.
- Document concrete UI acceptance checks for optimistic edit conflicts, next-target snapshot provenance, annotation state/navigation and exports with unsaved drafts. Keep project-specific ADB, screenshot, PR and conditional conclusion/coverage tabs when adapting the template; optional layout choices are not universal storage requirements.

## [0.0.2] - 2026-10-23

- Change-Type: fix
- Summary: Preserve existing project integrations when applying the workbench workflow: ADB discovery/registration, historical environment associations, live AI/WebMCP operations, actual PR-diff preparation, selected local screenshot workflows, per-round single-file/current-result storage and conditional conclusion tabs.
- Compatibility: User-requested version 0.0.2. Clarifies project adoption and adapter verification without changing triggers, bundled runtime, persisted schemas, source modes or the managed append-only workflow. Existing project policies remain explicit; unsupported custom archives need a reviewed adapter, not a schema-number rewrite. No data migration is performed by this release.
- Add a focused integration guide with shared UI/AI/service guards, evidence migration/cleanup boundaries and disposable verification scenarios. Distinguish documented integration procedures from working starter capabilities; preserve Issue attachments as the new-project default.
- Keep English/Chinese usage documentation and reference routing aligned. Local screenshot and current-results-only exceptions do not claim Issue uploads or managed workflow history.

## [0.0.1] - 2026-10-22

- Change-Type: initial
- Summary: Introduce platform-independent CI package verification, explicit publication, PR-derived regression cases, and a reusable web test workbench covering plans, rounds, environments and observations.
- Compatibility: New portable Skill with the user-requested initial version 0.0.1; this initial release has not shipped. Renamed from the local drafts android-ci-fir-test / ci-package-test to test-workbench while preserving its immutable sync ID, existing ci-package-test/* protocol identifiers and browser database keys. No prior released contract or migration. Ordinary CI archives artifacts; execution and publication follow the requested scope.
- Include acyclic prerequisite-case graphs, recursive dependency ordering, same-round/environment pass guards, exact prerequisite evidence and transitive stale-result detection. Keep original records while requiring fresh dependent validation after upstream retests; expose readiness and concrete prerequisite guidance in UI/AI.
- Clarify target-owned prerequisites versus outcome routing with a combined example and aligned English/Chinese flowcharts; document that current next branches do not support cross-case predicates. No runtime or persisted-format change.
- Include an offline interactive webpage graph with distinct dependency/outcome edges, environment-bound execution states, current/next highlights, failure/staleness markers and read-only case navigation. Export the same graph projection for AI.
- Include optional validated testLocation page/path/control hints, immutable round/annotation snapshots and read-only phone-test handoff copying. Hints remain unverified until matched to the live screen; no device commands or guessed coordinates. Existing hint-free cases/archives remain valid.
- Rename the Skill to test-workbench and lead discovery/documentation with the existing full testing-workbench scope; retain CI/package integration, stable identity, all persisted formats and initial0.0.1.
- Specify the shared case/observation/conclusion field contract and both storage mappings, expose required fields in AI metadata, and include complete replayable format fixtures plus a read-only Node validator for plans, archives and exact revision-bound summaries. Preserve existing persisted formats and legacy compatibility.
- Add optional append-only record-to-Issue associations in both source modes, including file-mode records/commits, existing completed records, clickable webpage references and AI/conclusion exports. Keep screenshots/logs in linked Issues, replace the webpage evidence entry with Issue association controls, preserve legacy evidence and immutable outcomes, and avoid implicit Issue creation/comments/status synchronization.
- Define two authoritative data-source modes: GitHub Issues by default for new projects, or explicitly selected repository-tracked files with separate case definitions and execution records. Preserve existing selections, one-source ownership and explicit migration; distinguish primary writes from browser caches/exports. Document the GitHub Issues integration contract with deferred multi-user concurrency/strict remote history protection. Require gh 2.99.0+ plus command capability/access checks only for CLI media attachments; describe authorized upgrades, browser fallback and separate log-file handling. Included adapters preserve the archive state-machine contract; legacy browser storage remains explicitly accessible for preview/export.
- Include explicit outcome-dependent next-test branches, frozen recursive targets, concrete per-environment UI/AI guidance, wait recovery conditions and outcome explanations; pre-execution blocked/skipped deferrals retain null execution time without fabricated starts. Preserve unresolved failures through running/partial/blocked/skipped retests until a same-case/environment pass; retain flat legacy cases without inventing branches.
- Include a shared machine-readable state contract, enforced round/execution lifecycle, append-only start/result/retest events and guarded AI state exports. Preserve legacy observation-only rounds explicitly; managed histories merge by prefix and reject divergence or downgrade.
- Keep linked Skill CLI invocation functional; serialize source reads/writes and pending webpage navigation, and prevent read-only Git status checks from refreshing the index during an explicit data commit.
- Include GitHub Issues (default) and repository-file webpage read/write adapters through a loopback Node service, with local gh identity, verified chunked Issue/comment documents, coherent generation publication, shared history/revision validation and explicit data-only Git commits. Retain opt-in browser preview/legacy export without silent fallback.
- Persist machine-readable, revision-bound test conclusions with records in both sources and display them in the webpage/AI snapshot; file-mode commits include conclusions separately from definitions and execution records. Incomplete/skipped coverage is not passed, and test conclusions do not approve releases.
- Reject round archives whose version differs from their owning plan before persistence, including legacy history; preserve valid historical source snapshots across same-version library updates.
- Include a working browser-local template with frozen definitions, mandatory smoke coverage, environment-bound append-only observations and JSON import/export.
- Include excerpt/context-pinned web annotations, append-only replies and resolution events, backward-compatible annotation archives, and stable browser-native annotation context without an automatic host/chat transport.
