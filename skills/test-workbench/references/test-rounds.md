# Regression cases, environments and repeat rounds

## Derive cases from the packaged change

Read the related PR at exact base/head, including complete diffs, affected callers, linked requirements and known regressions. Compare it with the package's source SHA. If changes are absent, keep their cases blocked and identify the mismatch; do not conflate a release PR's future contents with the current package.

For every case record:

| Field | Content |
| --- | --- |
| Identity | Stable case ID, title, version and plan |
| Traceability | PR base/head, relevant change or defect, package SHA/source |
| Coverage | Priority and multiple applicable test types |
| Preconditions | Account, data state, hardware/browser/runtime, OS/API, channel, duration |
| Procedure | Reproducible steps, concrete expected results, evidence to collect |
| Execution | Initially pending; results belong to separate observations |

For each newly authored case, also define outcome-dependent next tests or explicit retry/wait/done actions using [conditional-tests.md](conditional-tests.md). Keep failed (expectation violated), partial (incomplete verification), blocked (missing prerequisite) and skipped (deliberate non-execution) distinct. A diagnosed downstream pass or skipped retest cannot resolve the original failure.

Useful test types include smoke, functional, performance, compatibility, stability, security, usability, install/upgrade, and integration. Select applicable types rather than requiring all of them. A core start/pause/resume/end flow can be both smoke and functional. Test the observable result, such as remaining time continuing after resume, rather than only whether a control can be tapped.

Keep build checks and environment tests separate. A static compatibility check does not cover the corresponding runtime environment. One distribution channel does not cover another channel's identity or login flows. A short session does not cover a 90-minute background or overnight test. Record the required environment and duration instead of claiming equivalent coverage.

Use [execution-quality.md](execution-quality.md) to make that boundary explicit: link requirements to required checks and independent oracles, verify the complete tested component combination, and check actual samples/scenario coverage before accepting runner output. Keep invalid attempts and incomplete required work visible. Store these details in supported case/observation text and linked evidence; do not invent JSON fields or new result enums. The starter's all-pairs environment model needs separate applicable scopes or a verified project adapter for a sparse matrix.

## Round preparation and history

Use version → plan → round, permitting multiple plans per version and repeated rounds per plan. Reuse the existing template/data format when present; do not create another site for each case list. Requests to implement a complete test process or visualization include a working web workbench; a case-only request may return a document or structured data. Assessment, explanation and design requests deliver their requested findings/examples/proposal without starting implementation or execution.

Prepare a round from an **explicit selection**, never from a default copy of the complete plan. A focused defect retest includes only its selected cases plus recursive `dependsOn` prerequisites; smoke cases and prior failures outside that scope are excluded. Outcome `next` targets do not authorize adding cases. Targets outside the frozen scope report `out-of-scope` in the webpage/AI; prepare a new confirmed round to test them.

When the user requests regression coverage, propose prior failures, smoke, change-derived cases and optional unfinished cases. Confirm that candidate scope before creating it. Full regression must be explicitly selected; empty input rejects. Keep the original unresolved failures visible in their historical round even when they are outside the new scope.

The direct APIs share validation:

```javascript
const selection = {source: 'issue', planRevision: plan.revision, cases: ['CASE01', 'CASE02']};
const preview = previewRoundSelection(state, {planId: plan.id, selection}); // read-only
// Present preview.requestedCases, preview.cases and excluded plan cases; confirm the exact scope.
const next = createRound(state, {id, name, planId: plan.id, createdAt, selection});
```

Sources are `user`, `issue`, `change`, `smoke`, `failures` or `full-regression`. Sources describe the actual selection; they do not fetch or verify an Issue/diff. Full regression requires every current plan case ID explicitly. `planRevision` must match at creation; no old `changedIds`/`includeUnfinished` shortcut is accepted. The webpage requires a read-only preview followed by confirmation and invalidates preparation on selection/workspace changes. API integrations must present and confirm the same scope themselves; a source string alone is not proof that an external analysis occurred.

The saved `round.selection` retains `source`, `planRevision`, `requestedCases` and the ordered final `cases` IDs. Frozen definitions retain `selected` and/or `dependency` reasons. Recursive prerequisites precede dependents; no smoke classification is required for a focused round. The same round ID and exact definition are idempotent; conflicting reuse rejects. Imports/source writes preserve the immutable selection and reject mismatched IDs or extra cases outside its prerequisite closure.

Historical archives without `selection` keep their existing smoke and branch-closure validation; never invent a selection for old evidence. Version 0.0.7 accepts older archives, but the 0.0.6 reader cannot read new focused rounds without smoke or with external routes. Upgrade all readers/writers sharing an archive before creating focused rounds, retain a backup, and update direct callers to the explicit selection API. Archive schema/workflow integers stay 1; the Skill release is the user-selected 0.0.7 correction.

Resolve case content and classification independently: carry forward PR-updated steps and smoke promotions until a newer explicit edit supersedes them. A stale library must not revert them. An explicit current removal of a smoke label is authoritative. Preserve the previous library baseline or equivalent revision evidence to distinguish old data from intentional edits. Freeze the selected definition/classification in each round; later library edits affect future rounds and the current definition view, not old snapshots. Refresh stale preparation after relevant PR/library revisions change.

Separate definitions from append-only observations. Do not reset old results when preparing a new round or use existing passed results as the new round's execution evidence. Validate tooling with disposable data; never create a formal round or fabricate an environment result just to test a UI.

## Environment identity and package preparation

Register reusable test environments before execution: physical devices for mobile, browser/OS combinations for web, hosts for desktop, deployment/runtime for services, and consumer/toolchain combinations for libraries. Record identity and relevant configuration independently of the human-readable label. Similar model names do not establish identity.

Reuse existing automated device discovery and explicit imported-identity association through the [project integration procedures](project-integrations.md). Apply their shared identity/configuration checks to the webpage and any live AI tools. Preserve an explicitly selected current-result file layout without claiming absent workflow history; do not retrofit invented start events into old rounds.

Add the chosen environment to the current round and select it before saving any observation. Snapshot its profile/configuration in single and batch records. Reject missing/unknown profiles, environments outside the round and mismatched configuration before persistence. Manual registration remains possible without environment-discovery tools.

Prepare or install the exact verified package only for the requested stage. Preserve current data and settings. Compare identity/version/signature or runtime configuration as applicable; do not uninstall, clear state, force a downgrade or replace an environment to bypass a conflict without authorization. Verify the resulting package/deployment identity after success. Android-specific discovery and installation are optional examples in [android-example.md](android-example.md).

If automation can capture the screen but cannot reliably activate controls, verify the control method before judging the feature. Request manual cooperation or an explicitly approved environment setting change; do not mark failed input injection as a product defect. Avoid concurrent user and automated control during an operation, and restore temporary test settings afterward.

## State and machine-readable outcomes

Apply [state-machine.md](state-machine.md): keep definitions separate from per-round/case/environment execution state. New rounds use explicit lifecycle events; execution starts, outcomes and retests are append-only. The webpage and AI use one contract and expose guarded next actions. Preserve older observation-only rounds as legacy instead of fabricating transitions.

## Observations, imports, and outcomes

Each saved observation includes case/definition revision, round, package/source identity, registered environment/configuration snapshot, execution time with timezone, recorded time, tester, outcome, notes, and evidence links. Keep repeated results on the same environment and results from different environments independently. Pre-execution blocked/skipped deferrals have `executedAt: null`, an actual recording timestamp and a reason, without a fabricated start event.

For a multi-environment case, summarize each environment's latest applicable result; another environment passing must not clear an unresolved failure. A later pass on the same confirmed environment/configuration can supersede its earlier failure in the summary while retaining both observations. Make the summary policy visible and distinguish unsupported or partial coverage from full success.

On cross-workbench import, preserve original observation and environment snapshots. Associate a historical profile with a local environment only through explicit confirmation; store the association separately and never infer it from a shared model. Preserve summaries in existing snapshots and apply confirmed associations to subsequent summaries/rounds. Imported history lacking environment/time data stays visibly unknown; never invent it or bypass registration for new records.

Bind unsaved drafts to round/case/environment, restore that binding when returning, and keep the displayed environment equal to the saved observation's environment. Batch saves require the same validations as single saves. Saving a library classification must update current definition displays, filters, and exports while leaving historical rounds unchanged. Use revision checks and supported persistence interfaces; do not bypass an existing server's concurrency controls with direct file writes.

Keep results as passed, failed, partially executed, blocked or skipped; running and untested are execution states rather than new result records. Map explicitly to the workbench's supported statuses. In the bundled managed workflow, failures require notes and evidence; blocking/skipping require a reason, passed/failed/partial results require a started execution, while an unstarted case may be explicitly blocked/skipped with null execution time, and ending a round does not imply a pass. A product failure requires reproducible observed behavior and evidence. Describe nonfatal logs as follow-up observations unless a defect is confirmed. Do not invent a pass because the app opened, CI succeeded, or a crash was not seen.

Stop or defer cases when the required account, hardware, OS, duration, permissions or reliable controls are unavailable; continue independent applicable cases. Confirm the requested duration before starting a long test if scope is unclear. A discovered defect authorizes a report, not an unrequested source fix or PR.

Round ordering, environment registration, explicit identity associations and history are this workflow's requirements. The bundled browser template implements local registration, frozen round definitions and append-only observations; richer imported identity association or team collaboration must be implemented in the project workbench without rewriting historical records.
