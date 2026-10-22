# Machine-readable testing state

Read this when creating cases, executing or importing results, adapting the webpage, or asking AI to continue testing. Use structured JSON with stable IDs and a versioned state-machine contract. Chinese/localized labels are presentation, not stored enum values. Keep `metadata.version` (Skill), `schemaVersion` (archive), and `workflow.version` (event contract) separate.

## Data and identity

- Plans and cases are definitions, with IDs, revision, source/build/PR, types, preconditions, steps and expected results. Do not put one mutable pass/fail flag on a case definition.
- A round freezes its definitions and package context. An execution is identified by `(roundId, caseId, environmentId)`; two devices never share execution state just because their labels match.
- Observations are immutable evidence with status, environment snapshot, executed/recorded timestamps, tester, notes and evidence. The owning round identifies plan/version/source/build and the case snapshot. Retests append observations and start events; they never erase previous results.
- Annotations remain separate event streams with their existing `open`/`resolved` projection. Comments preserve status; resolve/reopen events change it. Annotating a failure cannot make it pass.

The executable, JSON-compatible [contract](../assets/workbench/workflow.mjs) is shared by the model, UI action discovery and AI export. It declares states, transitions, guards, result requirements, identities and required fields. For another project, adapt this contract and its validator together; document explicit mappings for unsupported statuses instead of inferring them from prose. Do not create an unrelated second state machine just for AI.

## Round lifecycle

| Action | From | To | Guard |
| --- | --- | --- | --- |
| `prepare` | `draft` | `ready` | At least one registered environment attached; frozen cases include smoke |
| `begin` | `ready` | `running` | Valid event with actor, timezone timestamp and expected from-state |
| `complete` | `running` | `completed` | Every selected case on every attached environment has a terminal result |
| `reopen` | `completed` | `running` | Explicit reason |

`completed` means recording has ended, not that all tests passed. Failed, partial, blocked and skipped outcomes remain visible. Attach environments before `begin`; use a new round for additional environment scope after starting.

## Execution lifecycle

`untested` is the stored key for pending. `start` moves it to `running`. `record` moves `running` to `passed`, `failed`, `partial`, `blocked` or `skipped`. Each terminal state can start another attempt through `start`; no direct failed → passed rewrite is allowed. Execution events require a running round and an attached environment. A failed result requires nonempty `notes` and `evidence`; blocked and skipped results require nonempty `notes` explaining the reason. Evidence must describe an actual observation, not a fabricated path to satisfy validation.

Every event has an immutable ID, scope, action, expected `from`, computed `to`, actor, timestamp `at` and reason text. Execution events also identify case/environment and, for a result, the exact observation ID. `attemptId` in the projection is the corresponding start-event ID. Original attempt and result events stay in the archive.

Event-array order is authoritative. Replay validates every transition and observation reference before persistence; wall-clock timestamps do not reorder workflow history. Summaries use each environment's current execution state. A failed environment takes priority over blocked, partial, running, untested, skipped, then passed, so another device passing cannot clear a failure. A new round begins untested and must rerun smoke.

## Direct model use and AI handoff

`model.mjs` exports `createRound`, `transitionRound`, `startExecution`, `startExecutionBatch`, `record`, `recordBatch`, `validate` and `exportAI`. They validate direct invocation; UI-only guards are insufficient. Model functions return a new archive without writing. Persist through `store.update` or the project's authenticated revision-checked API. Batch transitions/results validate atomically.

An example round event input to `transitionRound(state, roundId, input)`:

```json
{"id":"<unique-event-id>","action":"prepare","from":"draft","actor":"<actual-operator>","at":"<ISO-8601-with-timezone>","reason":""}
```

Use actual source data and timestamps. Read the current state before constructing an action. AI must report missing guards or invalid transitions; it must not infer success from CI, comments, page navigation or a proposed next action. Writes still follow the user's requested scope.

The webpage's **Export AI state snapshot** produces:

```text
format: ci-package-test/ai-snapshot
contract: the shared JSON-compatible state machine and field contract
archive: unchanged source data, snapshots, observations and events
projection.rounds[]: roundId, state, guarded nextActions, per-environment executions
projection.annotations[]: annotationId, state
```

Each managed execution includes `state`, `attemptId`, `observationId` and legal next actions with required result fields. A round action reports `allowed`, missing guards and whether a reason is required. This is a read-only handoff for AI; use **Export archive** for backup/import. The exported snapshot contains the same evidence as the archive, so share it only within the requested context. AI never needs to scrape translated status labels.

## Legacy data and merge policy

New rounds have `workflow: {version: 1, events: []}`. Existing schema-1 rounds without `workflow` remain readable and are explicitly projected as `legacy`; their original observations and timestamp-based summaries remain intact. Do not fabricate missing start events, actors or lifecycle transitions. Continue with a new managed round. Legacy recording remains available for compatibility but does not claim workflow enforcement.

Import validates the entire incoming archive and the merged result. Managed event histories must match by prefix: merge a longer extension, retain a shorter known prefix, and accept exact repeats without changing the revision. Divergent event branches, rewritten IDs, missing result events and workflow downgrade/upgrade of the same historical round reject the whole import. For concurrent offline branches, retain both backups and reconcile explicitly into a new round; never sort/splice transitions to force acceptance. Older tools that omit workflow data cannot overwrite managed history. Additional formats require an explicit reviewed migration.
