# Execution quality and acceptance

Use the relevant sections when preparing, executing or accepting tests. These procedures make the existing evidence-based workflow concrete; they do not add archive fields, result enums or automatic runner/device integrations. Existing valid archives remain readable without migration. A persisted record or valid JSON archive proves neither that an experiment ran nor that its evidence is sufficient.

## 1. Establish what would prove the case

Before executing a case, identify its requirement, applicable environment, required checks, observable oracle and pass rule. Reuse a project's existing verification matrix. Keep this information in supported `preconditions`, `steps`, `expected` and linked evidence; the table below is a report layout, not a JSON schema.

| Requirement / case | Applicable environment | Required check | Method and independent oracle | Pass rule / evidence |
| --- | --- | --- | --- | --- |
| Purchase recovery / PURCHASE01 | Configured iOS device and store account | Error classification and visible recovery | Package assertions; actual purchase-sheet/page behavior and entitlement read-back | Both required checks verified; retain test report and interaction evidence |
| Media transfer / MEDIA01 | Compatible App + BT + ISP combination | Full transfer and data integrity | End-to-end response and received file checksum | Expected bytes received; transport-only success does not close the App requirement |

Examples are definitions only, never observed results. A compile gate, source keyword check or mocked callback does not establish device behavior. Confirm the actual test target, toolchain and supported platform from current configuration: an iOS-only package may need an iOS destination rather than host `swift test`; a source consistency job does not execute its consumers.

Keep required and optional checks explicit. All required checks must be satisfied before recording the case as passed. Record a known expectation violation as failed even when other checks are incomplete. Otherwise use partial for incomplete verification or blocked for a concrete prerequisite/tooling obstruction; explain the remaining work. A started execution may have no valid measurements: record that fact rather than fabricating sample timestamps or a successful check. A pre-execution blocked/skipped deferral uses the existing null execution time.

Document genuine non-applicability with the rule and scope decision; a missing account, unavailable device, unsupported tool on the chosen host or failed prerequisite is a blocker, not proof that the requirement is inapplicable. The starter evaluates every frozen case × attached environment. Where appropriate, use separate applicable plans/rounds with their own smoke/dependency/route closure and an explicit overall coverage report. Preserve prior failures and required coverage across that split. Do not exclude pairs by UI filters, add a `not-applicable` status, or count skipped pairs as passed. A sparse applicability matrix needs a verified project adapter; it is not a starter feature.

## 2. Check that an execution produced valid evidence

Inspect the runner and analyzer before trusting an exit code or success banner. Discover which files, scenarios, sample counts and duration the selected case actually requires. Use project thresholds; do not impose universal counts or time limits on unrelated cases.

Before accepting a pass, check the applicable conditions:

- The intended cases were discovered and executed; a green suite with zero discovered tests cannot close them.
- Required input/output files exist, parse and belong to this attempt, case, environment and component combination. Old files left in a directory are not evidence for a new run.
- All required scenario groups exist. For a solo-versus-concurrent comparison, require both solo groups and their concurrent counterparts; two empty transition arrays matching is not a verified equivalence.
- Valid samples meet the declared minimum, actual execution duration meets the selected case, and any required channel/route was observed. A short run cannot close a long-duration case.
- The independent oracle supports the expected result; command acceptance, tool health or an intended route alone does not establish the downstream effect.

For example, an analyzer can print `CONCURRENT_OK` and exit 0 with empty directories or a missing concurrent group. Preserve its stdout and exit code, but do not record a product pass. Record the missing evidence and the relevant partial/blocked outcome. An intentionally empty media library is valid for an empty-library case when its emptiness is independently confirmed; it cannot satisfy a large-catalog stress case.

Treat experiment validity and product outcome separately. A wrong decoder, disconnected recorder, missing scenario or inadequate duration makes that measurement unusable. Preserve each attempt and reason, including rejected samples. Retain any independently confirmed product failure. A valid failing attempt cannot be discarded as noise merely because a later retry passes; keep both and apply the existing unresolved-failure policy.

Use the project's bounded retry policy, or choose a scope-appropriate bound before retrying an unreliable step. State the recovery condition and stop when it is unmet or the bound is reached. Keep reruns separate; do not cherry-pick successful samples or keep rerunning until the summary becomes green.

## 3. Freeze the complete tested combination

When behavior crosses repositories or devices, record all participating components. Reuse actual build manifests and existing project version reports. A useful evidence table is:

| Component | Repository and exact source | Package identity and SHA-256 | CI run / attempt / artifact | Installed/runtime read-back | Compatibility evidence |
| --- | --- | --- | --- | --- | --- |
| App | Actual repo + commit | Application id, variant, version, digest | Exact available provenance | Actual installed package/version/configuration | Declared protocol/API support |
| BT / ISP firmware | Each actual repo + commit | Image identity, digest and companion symbols | Each image's provenance | Flash/OTA result and runtime version or available alternative | Capability response / schema / command version |
| RPC schema / service | Source commit or resolved dependency/deployment | Generated contract or deployed build identity | When available | Actual consumer resolution/runtime endpoint | Supported contract version |

Include only components used by the case. Unknown values stay unknown with their verification limit; never infer a firmware SHA from its filename, use the CLI checkout as the installed revision, or assume every consumer uses the latest schema. Capture unresolved local source modifications when relevant; a commit alone cannot describe a dirty build.

Verify expected compatibility using declared requirements and observed capabilities before running dependent cases. Historical example: an updated BT sent a new media command while ISP still answered the old command ID. That combination blocks the intended new-protocol integration case; it does not establish a regression in the new App. An explicitly requested old/new compatibility case can legitimately exercise mixed versions, with its own expected behavior. Do not update the devices simply to make the matrix uniform.

Keep the round's primary `source`/`build` meaning intact and link the full combination through supported text and the selected evidence store. Include runtime configuration in the registered environment snapshot. When relevant installed state changes, use a new configuration/profile and round as needed; do not rewrite historical snapshots or relabel old observations. The starter has no structured component manifest validator. Automatic comparison requires a project adapter that updates validation, UI/AI projection and persistence together.

## 4. Reuse runners through an explicit result mapping

Prefer existing Gradle/JUnit, XCTest/xcresult, CTest, probe JSON or JSONL tooling. Preserve the production command and verification boundary. A useful adapter follows:

`read current context → preflight → explicit execution start → invoke runner → collect raw output → validate completeness → map actual result → guarded save → read-back`

Retain the actual executable/runner/analyzer version, working directory, sanitized arguments, start/end times, exit or signal status, discovered/executed counts and raw output references. Redact credentials and private device identifiers before tracked/shared evidence; do not paste tokens or unrestricted environment dumps. Keep the actual time distinct from import time.

Map at the case level, not merely the suite level. A successful suite proves only its discovered assertions. Nonzero exit can mean a product assertion failed, a build failed or the runner never started; classify using the concrete output. Preserve mixed results and partial execution. Missing reports, malformed output, duplicate result identities, old-context output and unsupported report versions must not produce passing observations.

Use the same revision, frozen definition, environment, workflow and evidence guards as UI saves. A batch must validate atomically; reject stale context before the first persistence mutation and retain its draft/raw output. Reimporting the same attempt must be idempotent, using stable project-defined IDs; a retest gets new attempt/start/observation IDs. Historical imports without real start events remain legacy or require an explicit format adapter, not invented lifecycle events.

Verify an adapter with disposable inputs: a valid run, zero discovered tests, empty/missing/malformed reports, missing required scenario, mixed pass/fail, timeout/interruption, stale round/environment, duplicate import, and rejected batch with no partial save. These are relevant acceptance scenarios, not claims that the starter ships a runner parser or executor.

## 5. Compare measurements on compatible terms

For performance, stability, power or acoustic cases, retain the project's measurement definition/version, units, required and actual duration, warmup/stable-window selection, sample count, aggregation method, thresholds, analyzer version and raw data references. Put the acceptance rule in `expected`; reference actual values and method in the observation evidence/notes. Do not add unrecognized metric fields to the archive.

Select a baseline with compatible hardware, runtime, scenario and measurement method, explicitly identifying which component changed. Separate firmware, routing, load and analyzer changes when drawing conclusions. If methods differ, retain both results and mark the comparison unsupported, or reanalyze both raw datasets with the same supported method while preserving original reports.

Examples:

- A battery value 10 seconds after unplug and a value after the required stable recovery window answer different questions. Retain transition samples as diagnostics; apply the project's stable-window gate before using them for accuracy or power estimates. A project's 90-second window is not a portable default.
- Audio-route success needs actual route and sink/output evidence. Loudness measurements need declared channel health, calibration, adequate active signal and comparable coupling. An obsolete latency method cannot be compared directly with its replacement.
- One media item repeated many times can exercise transfer load; it cannot close a case requiring hundreds of unique media IDs and multiple pages.

The starter stores notes/evidence but does not compute these comparisons or validate measurement limits automatically. Keep computed conclusions unchanged; the recorded outcomes must reflect the actual checks first.

## 6. Coordinate physical resources and restore state

For hardware or multi-process cases, reuse the project's actual setup and cleanup procedures. Identify the selected phone/glasses/board, exclusive resources (serial port, charging pin, recorder, audio route, PSU), relevant initial state, required observers, trigger and restoration. Record ownership to avoid concurrent control by another session. Do not kill another session's daemon or seize a busy resource to make a test run.

Start listeners/recorders and confirm readiness before triggering events. Correlate command responses and asynchronous events using request/session IDs or documented clock mappings; record filter, capture window, matched count and decoded payload. A missed event with a late listener is inadequate evidence, not automatically a product failure. A command success without the expected event does not pass an event case.

When charging and serial share a pin, use the supported App/RPC recording or OTA path for the charging scenario; do not demand an unavailable concurrent serial capture. Hardware power limits, flash timing and destructive actions remain governed by the project and requested scope.

Record temporary changes such as volume, routing, keep-awake, power output and logging, and arrange cleanup for success, failure, timeout and cancellation. Restore only state owned and changed by this run. Report cleanup success and remaining changes separately from the product outcome; incomplete cleanup can block the next case. The starter does not implement resource leasing or device cleanup.

## 7. Cover protocol interoperability when it is the requirement

Language-local encode/decode round trips establish their own codec boundary. For an interoperability change, select shared known payloads and run the relevant producer → consumer combinations (for example Kotlin → C, C → Swift). Include expected semantics, not only bytes the same implementation emitted.

Choose compatibility and boundary cases justified by the changed contract: supported old/new schemas, unknown enum/field handling, oneof/default/absence semantics, declared size/count limits and malformed/truncated payloads. Use an independent protocol expectation or reviewed fixture source; generated output alone is not an oracle. Preserve actual consumer schema versions and distinguish codec interoperability from transport/device end-to-end coverage.

Reuse the project's fixtures and commands. Add permanent automation only when requested or needed within the authorized implementation, and explain the uncertainty it tests, the changes requiring repeat regression and the efficiency benefit over existing checks. Do not mandate every language pair or every boundary for an unrelated schema edit.

## 8. Handoff and capability boundary

Report actual coverage, remaining required checks, invalid attempts, product defects, combination/baseline identity and evidence location. Include restoration blockers where relevant. Keep a valid archive's computed conclusion as-is; describe limitations beside it rather than editing its verdict. A prior report later found inadequate retains its original records; append a linked caveat and use the supported retest/reopen flow if authorized.

Version 0.0.4 clarifies agent execution and acceptance. It preserves archive/workflow/conclusion versions, triggers, storage modes, existing UI and history. Runner adapters, structured combination checks, sparse applicability, metric engines and resource managers require actual implementation and verification before being advertised as automated capabilities. Do not migrate existing data or fix a discovered product/runner defect without the corresponding request.
