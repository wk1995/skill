# Unified test-data format, version 1

The Skill is now named `test-workbench`. Its existing `ci-package-test/*` protocol identifiers, schema versions and browser database keys are retained for compatibility; renaming the Skill does not require renaming or migrating stored data.

Use this format for **both GitHub Issues and repository files**. The storage adapter decodes its source into one normalized archive; the webpage and AI consume that archive and the same deterministic conclusion projection. Do not author a second format for Issues, scrape titles/labels/Markdown to infer results, or introduce field aliases such as `result` for an observation's `status`.

The executable field contract is `CONTRACT.data` in [workflow.mjs](../assets/workbench/workflow.mjs), included in every AI snapshot. [model.mjs](../assets/workbench/model.mjs) validates field values, identities and references; workflow replay validates legal event sequences; [conclusions.mjs](../assets/workbench/conclusions.mjs) computes the summary. The reference below describes those existing supported formats. Optional extensions must update their validators, producers and consumers together before the webpage can use them.

## Versions, identities and common conventions

| Value | Contract |
| --- | --- |
| Skill `metadata.version` | Skill release version, currently0.0.2; independent from data versions |
| Archive `schemaVersion` | Integer `1` |
| Round `workflow.version` | Integer `1` for managed execution; omission identifies legacy history only |
| Conclusion `format` / `version` | `ci-package-test/conclusions` / integer `1` |
| Source packet `format` | `ci-package-test/source-1`; a storage envelope, not another test-data schema |
| Product `plan.version` / `round.version` | Nonempty project version text; the round must match its owning plan's version |
| Revisions | Nonnegative integers; plan revision tracks definition edits, archive revision tracks confirmed workspace changes |
| IDs | Nonempty stable strings, independent of titles and GitHub Issue numbers. Plans, registered environments and rounds are unique within the archive; cases, observations, workflow events and Issue associations are unique within their owning plan/round collections |
| Times | ISO8601 timestamp with timezone, e.g. `2026-10-23T09:00:00Z`; actual execution time differs from recording time |
| Empty / absent | Required text fields stay present even when an allowed value is `""`. Optional collections may be absent; JSON `null` is allowed only where described |

Localized labels belong to presentation. Persist the exact English enum keys. Project metadata such as priority, environment kind and source/build strings follows the documented field types; the current validator does not enforce a universal priority scale, OS list, URL or source-SHA syntax. Verify the actual package independently.

## 1. Test-case definition

A case belongs to a plan. The required plan fields are `id`, `revision`, `version`, `title`, `source`, `build`, `pr` and `cases`. `build`/`pr` may be empty strings; `cases` is an array. New rounds require at least one case classified as smoke. Keep a case definition's outcome separate from every execution result.

| Case field | Required | Type / meaning |
| --- | --- | --- |
| `id` | Yes | Stable case ID |
| `title` | Yes | Nonempty title |
| `priority` | Yes | Nonempty project priority, conventionally P0/P1/P2 |
| `types` | Yes | Nonempty, unique array from `smoke`, `functional`, `performance`, `compatibility`, `stability`, `security`, `usability`, `install-upgrade`, `integration` |
| `preconditions` | Yes | Text; may be empty |
| `steps`, `expected` | Yes | Nonempty procedure and expected outcome text |
| `dependsOn` | No | Unique prerequisite case-ID array; all targets exist and the dependency graph is acyclic |
| `next` | No | When present, exactly five outcome branches; see below |
| `testLocation` | No | Validated application/page/path/control hints; see [test-location.md](test-location.md) |

```json
{
  "id": "PROFILE01",
  "title": "View the signed-in account profile",
  "priority": "P1",
  "types": ["functional"],
  "preconditions": "Signed in on the selected environment",
  "steps": "Open Profile and inspect account details",
  "expected": "Account details match the signed-in account",
  "dependsOn": ["LOGIN01"],
  "next": {
    "passed": {"action": "done", "reason": "This branch is covered"},
    "failed": {"action": "retry", "caseId": "PROFILE01", "reason": "Verify the fix"},
    "partial": {"action": "retry", "caseId": "PROFILE01", "reason": "Complete remaining checks"},
    "blocked": {"action": "wait", "reason": "Service unavailable", "resumeWhen": "Test service is available"},
    "skipped": {"action": "done", "reason": "Explicitly excluded this round"}
  }
}
```

`next` actions are `test`, `retry`, `wait`, `done`. All need a nonempty `reason`; test/retry require `caseId`, retry targets the same case; wait requires `resumeWhen`. Wait/done contain no case target. Put prerequisites on the target's `dependsOn`, then evaluate them for this round/environment; next branches do not support cross-case predicates. A missing next stays explicitly unconfigured. See [dependencies](dependencies.md) and [routing](conditional-tests.md).

## 2. Test-execution record

Records belong to a **frozen round**, not directly to a mutable library case. Required round fields: `id`, `name`, `planId`, `version`, `source`, `build`, `pr`, `createdAt`, `cases`, `environments`, `observations`. New rounds also carry `workflow: {"version":1,"events":[]}`; create them through the model to freeze definitions and select dependencies/smoke/failures correctly. `issueLinks` is optional.

An execution is identified by `(roundId, caseId, environmentId)`. A record's round, product version, source/build and frozen definition come from its owning round. The registered environment requires `id`, `label`, `kind`, `configuration`; attached/observed snapshots must match it exactly.

| Observation field | Required | Type / meaning |
| --- | --- | --- |
| `id` | Yes | Immutable observation ID; a retest creates another ID |
| `caseId`, `environmentId` | Yes | Existing frozen case and attached environment IDs |
| `environment` | Yes | Exact registered environment snapshot, not an arbitrary device label |
| `status` | Yes | Managed outcomes: `passed`, `failed`, `partial`, `blocked`, `skipped` |
| `executedAt` | Yes | Actual execution timestamp; `null` only for pre-execution blocked/skipped with a matching defer event |
| `recordedAt` | Yes | Recording timestamp with timezone |
| `tester` | Yes | Nonempty operator identity |
| `notes` | Yes | Text; failure/block/skip require a reason, and routed partial execution explains completed/unverified work |
| `evidence` | Yes | Legacy evidence text, may be `""`; new webpage records use Issue associations instead |

`untested` and `running` are execution phases, not new managed observation outcomes. The legacy reader retains its original status support without inventing lifecycle events.

Example **fragment**, taken from the [complete validated archive](../assets/examples/archive.json):

```json
{
  "id": "EXAMPLE-PROFILE-FAIL",
  "caseId": "PROFILE01",
  "environmentId": "EXAMPLE-ENV",
  "environment": {
    "id": "EXAMPLE-ENV",
    "label": "Disposable fixture browser",
    "kind": "browser",
    "configuration": "Example only; no real product/device was tested"
  },
  "status": "failed",
  "executedAt": "2026-10-23T09:00:00Z",
  "recordedAt": "2026-10-23T09:00:00Z",
  "tester": "Example operator",
  "notes": "FORMAT EXAMPLE ONLY: fixture profile differs; no actual issue was created",
  "evidence": ""
}
```

This failed record requires its association in `round.issueLinks`, with fields `id`, `observationId`, canonical HTTPS Issue `url`, `actor`, `createdAt`. Failed observations require notes and either such a link or legacy nonempty evidence. Store screenshot/log attachments directly in the linked Issue. Linking alone verifies URL structure, not Issue existence, access or attachment content. See [Issue associations](data-sources.md#record-to-issue-associations).

Managed observations **also require matching workflow events**. Round events contain `id`, `scope`, `action`, `from`, `to`, `actor`, `at`, `reason`; execution events additionally contain `caseId`, `environmentId`, `observationId` (empty on start). The model creates result events atomically with observations/links. Use `transitionRound`, `startExecution` and `recordBatch`, rather than pushing a fragment into storage. The complete example demonstrates prepare → begin → login start/pass → profile start/failure → complete; failure remains failed. Invalid references, states, times, stale dependencies, missing starts or conflicting history reject before publication. See [state machines](state-machine.md).

## 3. Test summary / conclusions

The structured test summary is the deterministic `ci-package-test/conclusions` document. Its `archiveRevision` must equal the supporting archive's revision; its `rounds[]` contains exactly that archive's round projections. Do not edit a computed verdict or regenerate it from Issue closure/labels/prose. Optional human explanations/recommendations can be retained as existing pinned annotations; they do not override the computed conclusion.

| Summary field | Required | Type / meaning |
| --- | --- | --- |
| `format`, `version` | Yes | `ci-package-test/conclusions`, integer1 |
| `archiveRevision` | Yes | Exact supporting archive revision |
| `rounds` | Yes | Array of summaries with `roundId`, `planId`, product `version`, `source`, `build`, `pr` |
| `rounds[].lifecycle` | Yes | `draft`, `ready`, `running`, `completed`, or `legacy` |
| `rounds[].verdict` | Yes | `passed`, `failed`, `blocked`, `partial`, `incomplete`, `legacy` |
| `rounds[].counts` | Yes | All seven integer counters: failed/blocked/partial/running/untested/skipped/passed; legacy uses `null` |
| `rounds[].executions` | Yes | One current projection per frozen case × attached environment; legacy uses `[]` |
| `rounds[].meaning` | Yes | Generated explanation of the conclusion's scope |

Each execution projection contains `caseId`, `environmentId`, `phase`, effective `result`, nullable `observationId` and `unresolvedFailureId`, boolean `dependencyStale`, and optional `issues` URLs. Counters count **case/environment pairs**, not all historical observations. An unresolved earlier failure keeps effective result failed across partial/block/skip/start; a stale passed/running execution is effectively blocked. Only a completed round with every pair currently valid and passed can conclude passed; missing/skipped coverage stays incomplete. A conclusion is not release approval. The [complete summary example](../assets/examples/conclusions.json) has lifecycle completed, one passed and one failed pair, verdict failed, and the failure's Issue reference.

## Storage mapping and rendering

| Logical data | Repository files | GitHub Issues source |
| --- | --- | --- |
| Definitions and registered environments | Generation `definitions.json`: archive `schemaVersion`, `revision`, `plans`, `environments` | Published manifest plus case-document references; case entity key includes plan and case ID |
| Round records and history | Generation `records.json`: the `rounds` array, including snapshots, observations, workflow and optional `issueLinks` | One entity per round ID; structured round JSON snapshot documents retain all fields/events |
| Test summaries | Generation `conclusions.json`: complete conclusion document | Index-owned `conclusions` structured document, referenced by the published manifest |
| Annotations | Generation `annotations.json`: annotation array | Structured annotation documents referenced by the manifest |

A reconstructed archive has `{schemaVersion, revision, plans, environments, rounds, annotations}`; old archives may omit annotations. The **entire archive** is the portable import/export format. `records.json` alone is not an importable archive, and `conclusions.json` never substitutes for execution records. File generations remain selected by the owned pointer/digest; editing owned snapshot files by hand invalidates it. Use the webpage/source adapter to write validated generations.

Issues use the existing `ci-package-test/source-1` marker, bounded JSON-string chunks, ordered comment IDs and digests. The index references only completely verified documents. A plain Markdown Issue or JSON pasted into an arbitrary comment is not automatically recognized or published as test data; use the adapter. Issue titles, labels, open/closed state, ordinary discussion and attachments are presentation/reference material. They cannot replace the required structured fields or events. See the [actual source protocol](data-sources.md#github-persistence).

Both readers follow: **decode the selected source → reconstruct archive → validate fields/references and replay workflow → recompute and compare saved conclusions → render the same archive/projections**. Invalid or unsupported source data produces an explicit error; preserve the previous published source and pending data, with no inference of success, empty-state replacement or source fallback. Invalid saves reject before publication. See [source failure boundaries](data-sources.md).

## Runnable examples and validation

These files are labelled **FORMAT EXAMPLE ONLY** and contain no real product-test evidence or verified Issue:

- [plan.json](../assets/examples/plan.json): importable two-case plan with dependency and all five next branches.
- [archive.json](../assets/examples/archive.json): complete frozen round, registered environment, started observations, Issue reference and lifecycle history.
- [conclusions.json](../assets/examples/conclusions.json): exact deterministic summary of that archive revision.

From the Skill directory, Node.js18+:

```bash
node scripts/validate-test-data.mjs --plan assets/examples/plan.json
node scripts/validate-test-data.mjs --archive assets/examples/archive.json --conclusions assets/examples/conclusions.json
```

The validator is read-only and uses the actual webpage/source validators; it needs no Git/gh or network access. It validates a complete plan/archive, not an isolated observation fragment or arbitrary Markdown. Conclusions may be omitted to check the archive and derive its summary internally; when supplied, they must match completely, including revision, identity, counters, verdicts and evidence references. Reordered object keys are harmless; missing/extra/modified summary fields or reordered arrays reject. Invalid JSON/options/data exit nonzero, preserving input files. The CLI prints a validation report, not a new saved summary or a test result. For another project, produce real definitions/records via the model, export/validate them, and save through the selected source adapter.
