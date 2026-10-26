# Deliver the testing process as a reusable web workbench

Use the [unified case/record/summary format](data-format.md) for required fields, references, source mappings and validated examples; both sources reconstruct the same archive.

Web delivery is part of complete test-process and visualization requests. Inspect the project's current tool first; retain its database and history. When none exists, copy `assets/workbench/` and `scripts/` together into a project-owned tools directory, preserving relative paths, and adapt the provided application. Keep one reusable app; later packages, versions, plans and rounds are data.

For an existing tool, use [project-integrations.md](project-integrations.md) before replacing adapters or UI. Retain verified ADB, identity-association, WebMCP, PR-diff and selected screenshot capabilities. Respect the project's explicit storage/history policy and conditional conclusion presentation. These capabilities are integration procedures, not extra implemented starter features; the acceptance checks below apply after any requested adapter work.

For UI changes, use [UI adoption and acceptance](ui-adoption.md) to retain the project layout while exposing complete editing, concrete next-step previews, round-wide annotations and AI export. These entry points must use existing validated operations and preserve frozen rounds.

## Included working template

Start the included [primary-source service](data-sources.md#included-webpage-adapters), for example from the Skill directory:

```bash
node scripts/workbench-server.mjs --repo OWNER/REPO
node scripts/workbench-server.mjs --mode repository-files --repo-root /absolute/project --data-dir testing/testflow
```

GitHub Issues is the default; file mode is explicit. Open the printed loopback URL, verify its source banner, initialize only a new workspace, and import an actual plan. Normal UI actions write through the connected adapter; success is shown only after source read-back. File mode saves working-tree data first and exposes a separate data-only Git commit button. Both modes persist and display revision-bound test conclusions. The starter uses plain browser modules and a Node18+ local service with no npm runtime dependencies; GitHub credentials stay in local gh. No external hosting or multi-user service is implied.

For legacy browser data or an isolated preview only, use a static HTTP server for `assets/workbench/` and explicitly open `?local=1` or the existing named `?workspace=<name>`. This preserves the original IndexedDB origin/name and allows export. Keep host/port stable when retrieving old data; a private session or cleared browser storage is not a backup. A plain static URL without a preview flag will not silently replace the default primary source with browser storage.

The template has three primary views: **Test cases** contains definitions/frozen procedures, guarded starts/skips/result entry and the flow graph; **Test records** contains saved outcomes, time, actor, environment, evidence and filterable whole-round attempt history; **Test summary** contains the full deterministic conclusion and exact case/environment evidence links. Record cards may navigate back to a case for retesting, but the record view has no start/skip controls or new-result form. A separate annotations view retains round-wide comments. Clicking statistic cards applies the existing filters and highlights the chosen result; the total card clears filters. Case statistics count current effective outcomes; record statistics count observations, including repeated attempts. List filters never change the summary.

The UI includes editable case prerequisites, guarded starts, unmet/stale dependency evidence, concrete per-outcome next-test guidance with frozen target procedures, editable `next` branches and outcome help, enforced round/execution state machines, guarded lifecycle and start/retest controls, AI state-snapshot export, version/plan/round navigation, case search/type/result filters, current definition editing, frozen round definitions, environment registration and attachment, observations with execution/recording time, web annotations and JSON import/export. Annotations support excerpts, snapshots, replies, resolution and reopen events. Deep links and field/observation DOM markers support native browser annotation context; the template does not implement an agent-specific send-to-chat transport. See [annotations.md](annotations.md). Preserve unsaved form/environment binding when changing case or round.

The optional `?workspace=<name>` URL isolates another browser-local workspace on the same origin; keep that URL stable for reuse. Deep links retain cases/records/summary/annotations views, selected environment and list filters, and update when changing rounds. Existing links without those optional parameters remain valid. Unsaved definition and execution drafts remain in memory while navigating; exporting, refreshing the page or closing it does not save them.

## Interactive flow and test positioning

The flow panel uses native SVG paths and accessible HTML node buttons, with no external renderer/runtime dependency. `flow.mjs` projects the frozen definitions and environment workflow also used by AI; `flow-ui.mjs` renders it. Solid edges are required prerequisites; dashed edges are grouped outcome routes, with available routes highlighted separately. Nodes show phase, selected/next markers and unresolved-failure/staleness warnings. Relationship details expose outcome labels. Wide graphs scroll inside the panel on narrow displays; the full graph is independent of list filters.

Select an attached environment in the graph or detail to see current states. Without a managed round/environment, show definition/legacy context or an environment prompt instead of fabricated results. Selecting a node opens its case, clears list filters and retains environment/history; it never starts execution. The next-test panel uses the same `nextTest`, frozen steps and expected result as detail/AI. Completed rounds retain evidence and disable executable route recommendations until reopened.

Optional [testLocation](test-location.md) supplies page/path/control hints for direct device testing. Editor, archive/round validation, annotation snapshots and AI share its field validator. Rendering/copying are read-only. Match declared hints against the live device view before acting; hints are not observed results.

## Plan input

Generate this shape from the actual PR/change set. All case types use the English enum keys exported by `model.mjs`; UI labels are Chinese and can be localized by the target project. Timestamps in archives include a timezone. Build/PR may be empty when unavailable; source must identify the tested revision.

```json
{
  "id": "release-regression",
  "revision": 0,
  "version": "<actual-version>",
  "title": "Release regression",
  "source": "<exact-source-sha>",
  "build": "<CI-run-or-artifact-URL>",
  "pr": "<PR-or-change-URL>",
  "cases": [{
    "id": "CORE01",
    "title": "<observable core behavior>",
    "priority": "P0",
    "types": ["smoke", "functional"],
    "preconditions": "<environment and data requirements>",
    "steps": "<concrete steps>",
    "expected": "<observable expected outcome>"
  }]
}
```

Plan IDs remain bound to a version; use a new ID for another version or separate plan. Increase `revision` for intentional case-library updates. An identical import is idempotent; stale/conflicting definitions are rejected. Round creation selects prior failures, every current smoke case and specified changed IDs (all library cases by default for the first round). The ordered union is deduplicated by ID, including IDs such as `constructor`. Existing rounds freeze package/source and case definitions. Add [conditional next-test branches](conditional-tests.md) when authoring new cases; reachable targets are frozen recursively with conditional selection reasons. Unvisited branches remain pending until explicitly tested/skipped.

An exported archive contains `schemaVersion: 1`, revision, plans, registered environments, rounds with observations, and an optional annotations array. New rounds also contain `workflow.version: 1` and append-only events; older rounds without workflow remain explicitly legacy. Read [state-machine.md](state-machine.md) for states, transition guards, AI exports and prefix-only workflow merge rules. Existing schema-1 archives without annotations remain readable and cannot clear local annotations. Import validates the entire archive first, merges new records, and rejects conflicting historical definitions/observations/annotation events or stale plans. It never replaces history blindly. Imported environment IDs are retained; do not merge similar labels automatically. Other legacy schemas require a reviewed migration adapter that retains unknown historical data. Rich cross-workbench identity associations need an explicit project feature.

Managed summaries use validated workflow replay for each case/environment; another environment cannot clear a failure. An `unresolvedFailureId` keeps a known failure in the overall summary through running/partial/blocked/skipped retests until an actual same-case/environment pass. Legacy observation-only summaries use each environment's latest execution time, then recording time. Exactly tied timestamps keep the more conservative outcome, with failure taking precedence, so archive merge order cannot silently clear a failure. Every attached environment is expected for every selected case; split plans when environments have different applicability.

## Persistence boundary and extensions

`dependencies.mjs` owns prerequisite validation/order/readiness; `workflow.mjs` owns the JSON-compatible contract and event replay; `model.mjs` owns archive validation and pure state transitions. `store.mjs` uses the connected HTTP adapter by default; `remote-store.mjs` validates the proposed archive and sends its expected revision. The service revalidates the whole state and retained history before writes. Explicit browser previews retain the original expected-revision IndexedDB transaction. An outdated tab must refresh and review before saving; a rejected operation leaves persisted state intact. Do not bypass this boundary with UI-only validation. Use the same model validation for single/batch operations and imports.

The included adapters implement the source contract in [data-sources.md](data-sources.md). Preserve the shared validation when adapting them; working-tree saves and commits are separate. Do not expose a local write service publicly to simulate collaboration. Add project-specific automated-test ingestion, coverage mapping or annotation integration only when useful to the requested workflow.

For the default [GitHub Issues mode](github-issues.md), multi-user concurrency coordination and strict remote history/audit protection are explicitly deferred for the initial single-operator phase. That scope decision does not disable the current local revision/model guards or claim distributed consistency from a local service. Use the same reference for the gh 2.99.0+ media gate, old-version upgrade/fallback handling and separate log-file upload path.

## Acceptance

Run `node --test <skill-directory>/tests/*.test.mjs` (Node.js 18+). Exercise the actual copied/built app in a browser with isolated data: import, edit classification/steps, create a round, register/attach an environment, reject missing registration, mark ready/start, start individual/batch executions, reject invalid transitions or missing reasons/evidence, append results, end/reopen with a reason, export AI state, reload, export/import and prepare a subsequent no-diff smoke round. Verify another environment's pass cannot clear a failure, and old rounds remain unchanged. Check stale-tab saves preserve the newer state.

For automated browser fixtures, serve the Skill directory and open `tests/browser-store.html`, `tests/browser-ui.html`, `tests/browser-annotations.html`, `tests/browser-workflow.html`, `tests/browser-routing.html`, `tests/browser-dependencies.html`, `tests/browser-flow.html` and `tests/browser-separation.html` and `tests/browser-stat-focus.html`. They create uniquely named disposable databases, test real transactions, deep links, annotations, graph/environment/navigation, locator validation and phone handoff, and report PASS/FAIL on the page. These checks complement the Node suite; they are not run by the shell gate.

Deliver the functioning URL, where data is stored, backup/export instructions, and tested limits. Do not mark demonstration observations as real product-test results or claim distributed collaboration from this local service.

For the optional end-to-end primary-adapter browser runner, install/provide Playwright in a test environment and run `node tests/browser-primary.mjs` from the Skill directory. `TESTFLOW_PLAYWRIGHT_MODULE` may point to an existing package directory and `TESTFLOW_CHROME` to a Chrome executable; neither is needed by the workbench runtime. The runner starts isolated loopback services, uses only an in-memory fake GitHub API plus disposable Git repositories, exercises both default URLs without browser-preview flags, and verifies real UI writes, failure retention, conclusions, reload and separate file commits. It creates no live Issues or product-test evidence.

## Issue evidence links

The result form accepts full Issue URLs (one per line); existing record cards support append-only associations even after round completion. Open those links to add screenshots/logs in GitHub. The workbench has no separate attachment entry; original evidence fields remain readable. File mode saves associations inside records and commits them with conclusions through the separate commit control. See [format, validation and API boundaries](data-sources.md#record-to-issue-associations).
