# Regression cases, devices, and repeat rounds

## Derive cases from the packaged change

Read the related PR at exact base/head, including complete diffs, affected callers, linked requirements and known regressions. Compare it with the APK's source SHA. If changes are absent, keep their cases blocked and identify the mismatch; do not conflate a release PR's future contents with the current package.

For every case record:

| Field | Content |
| --- | --- |
| Identity | Stable case ID, title, version and plan |
| Traceability | PR base/head, relevant change or defect, package SHA/source |
| Coverage | Priority and multiple applicable test types |
| Preconditions | Account, app/data state, hardware, OS/API, channel, duration |
| Procedure | Reproducible steps, concrete expected results, evidence to collect |
| Execution | Initially pending; results belong to separate observations |

Useful test types include smoke, functional, performance, compatibility, stability, security, usability, install/upgrade, and integration. Select applicable types rather than requiring all of them. A core start/pause/resume/end flow can be both smoke and functional. Test the observable result, such as remaining time continuing after resume, rather than only whether a control can be tapped.

Keep build checks and device tests separate. A static native-library alignment check does not cover a real 16 KB environment. A FIR APK does not cover Play-specific login/signing flows. A short session does not cover a 90-minute background or overnight test. Record the required environment and duration instead of claiming equivalent coverage.

## Round preparation and history

Use version → plan → round, permitting multiple plans per version and repeated rounds per plan. Reuse the existing template/data format when present; do not create another site for each case list. When no workbench exists, a case document or structured data is sufficient unless a web app was requested.

Prepare each round as an ordered union by stable case ID:

1. Previous failed cases, retaining unresolved failure context.
2. All current smoke cases, even if passed previously or no code changed.
3. Cases derived from the selected release PR diff.
4. Optional unfinished cases when within the requested scope.

Retain all selection reasons when deduplicating. If no smoke definition exists, define the core smoke set before starting a round. Never silently omit failures or smoke due to a stale library, inherited object keys, filtering, or a changed display category.

Resolve case content and classification independently: carry forward PR-updated steps and smoke promotions until a newer explicit edit supersedes them. A stale library must not revert them. An explicit current removal of a smoke label is authoritative. Preserve the previous library baseline or equivalent revision evidence to distinguish old data from intentional edits. Freeze the selected definition/classification in each round; later library edits affect future rounds and the current definition view, not old snapshots. Refresh stale preparation after relevant PR/library revisions change.

Separate definitions from append-only observations. Do not reset old results when preparing a new round or use existing passed results as the new round's execution evidence. Validate tooling with disposable data; never create a formal round or fabricate a device result just to test a UI.

## Device identity and installation

Device operations require the requested installation/testing stage. Discover devices with `adb devices -l`; select an explicit serial with `adb -s` when operating. Resolve unauthorized/offline devices and multi-device ambiguity first. Read model, manufacturer, OS/API, ABI, build fingerprint, and page size where available, and record the transport used. Do not assume a wireless endpoint is a permanent physical identity.

Maintain a reusable registered device profile, add it to the current round, and select it before saving any result. Snapshot the tested configuration and profile identity into each observation, including single and batch operations. Reject missing/unknown profiles, devices outside the round, and stale configuration before persistence. Manual registration remains available when ADB is unavailable. Same model/OS does not establish that two profiles are one physical phone.

Before installation, compare APK and installed package/signature/version. Preserve existing app data using a supported replacement install such as `adb -s "$SERIAL" install -r "$APK"`. Do not uninstall, clear data, or force a downgrade to bypass a conflict without the user's authorization. If the phone blocks installation, request the necessary on-device action. Verify the installed package/version and, where readable, APK digest after success.

If automation can capture the screen but cannot reliably activate controls, verify the control method before judging the feature. Request manual cooperation or an explicitly approved device setting change; do not mark failed input injection as a product defect. Avoid concurrent user and automated control during an operation, and restore temporary test settings afterward.

## Observations, imports, and outcomes

Each saved observation includes case/definition revision, round, package/source identity, registered device/configuration snapshot, execution time with timezone, recorded time, tester, outcome, notes, and evidence links. Keep repeated results on the same phone and results from different phones independently.

For a multi-device case, summarize each device's latest applicable result; another phone passing must not clear an unresolved failure. A later pass on the same confirmed device/configuration can supersede its earlier failure in the summary while retaining both observations. Make the summary policy visible and distinguish unsupported or partial coverage from full success.

On cross-workbench import, preserve original observation and device snapshots. Associate a historical profile with a local physical device only through explicit confirmation; store the association separately and never infer it from a shared model. Preserve summaries in existing snapshots and apply confirmed associations to subsequent summaries/rounds. Imported history lacking device/time data stays visibly unknown; never invent it or bypass registration for new records.

Bind unsaved drafts to round/case/device, restore that binding when returning, and keep the displayed device equal to the saved observation's device. Batch saves require the same validations as single saves. Saving a library classification must update current definition displays, filters, and exports while leaving historical rounds unchanged. Use revision checks and supported persistence interfaces; do not bypass an existing server's concurrency controls with direct file writes.

Keep results as passed, failed, partially executed, blocked, or untested (map explicitly to the workbench's supported statuses). A product failure requires reproducible observed behavior and evidence. Describe nonfatal logs as follow-up observations unless a defect is confirmed. Do not invent a pass because the app opened, CI succeeded, or a crash was not seen.

Stop or defer cases when the required account, hardware, OS, duration, permissions or reliable controls are unavailable; continue independent applicable cases. Confirm the requested duration before starting a long test if scope is unclear. A discovered defect authorizes a report, not an unrequested source fix or PR.

Source: [Android Debug Bridge documentation](https://developer.android.com/tools/adb), checked on 2026-10-22, for device targeting and replacement installation. Round ordering, device registration, explicit identity associations, and history rules are workflow requirements distilled from the referenced conversation, not Android platform guarantees.
