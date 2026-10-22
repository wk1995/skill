# Deliver the testing process as a reusable web workbench

Web delivery is part of complete test-process and visualization requests. Inspect the project's current tool first; retain its database and history. When none exists, copy `assets/workbench/` into a project-owned tools directory and adapt the provided application. Keep one reusable app; later packages, versions, plans and rounds are data.

## Included working template

Serve the copied directory over loopback HTTP, for example:

```bash
python3 -m http.server 4317 --bind 127.0.0.1 --directory <workbench-directory>
```

Open the local URL and import a plan JSON file. The template starts empty and uses plain browser modules with no npm runtime dependencies. Browser-local IndexedDB persists the archive on that origin; keep the same host/port for reuse and a different port/origin for another project's workspace. Export backups and distinguish this local prototype from a shared service. A private browsing session or clearing site storage is not a backup. No hosting or external publication is implied.

The UI includes version/plan/round navigation, case search/type/result filters, current definition editing, frozen round definitions, environment registration and attachment, observations with execution/recording time, web annotations and JSON import/export. Annotations support excerpts, snapshots, replies, resolution and reopen events. Deep links and field/observation DOM markers support native browser annotation context; the template does not implement an agent-specific send-to-chat transport. See [annotations.md](annotations.md). Preserve unsaved form/environment binding when changing case or round.

The optional `?workspace=<name>` URL isolates another browser-local workspace on the same origin; keep that URL stable for reuse. Deep links also retain the cases/records view and update when changing rounds in either view.

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

Plan IDs remain bound to a version; use a new ID for another version or separate plan. Increase `revision` for intentional case-library updates. An identical import is idempotent; stale/conflicting definitions are rejected. Round creation selects prior failures, every current smoke case and specified changed IDs (all library cases by default for the first round). The ordered union is deduplicated by ID, including IDs such as `constructor`. Existing rounds freeze package/source and case definitions.

An exported archive contains `schemaVersion: 1`, revision, plans, registered environments, rounds with observations, and an optional annotations array. Existing schema-1 archives without annotations remain readable and cannot clear local annotations. Import validates the entire archive first, merges new records, and rejects conflicting historical definitions/observations/annotation events or stale plans. It never replaces history blindly. Imported environment IDs are retained; do not merge similar labels automatically. Other legacy schemas require a reviewed migration adapter that retains unknown historical data. Rich cross-workbench identity associations need an explicit project feature.

Summaries use each environment's latest execution time, then recording time. Exactly tied timestamps keep the more conservative outcome, with failure taking precedence, so archive merge order cannot silently clear a failure. Every attached environment is expected for every selected case; split plans when environments have different applicability.

## Persistence boundary and extensions

`model.mjs` owns validation and pure state transitions. `store.mjs` rechecks the expected revision inside one IndexedDB readwrite transaction before committing. An outdated tab must refresh and review before saving; a rejected operation leaves persisted state intact. Do not bypass this boundary with UI-only validation. Use the same model validation for single/batch operations and imports.

For team use, keep these contracts while moving persistence behind the project's authenticated API with revision checks, authorization, append-only observations and backups. Do not expose a local write service publicly to simulate collaboration. Add project-specific automated-test ingestion, coverage mapping or annotation integration only when useful to the requested workflow.

## Acceptance

Run `node --test <skill-directory>/tests/*.test.mjs` (Node.js 18+). Exercise the actual copied/built app in a browser with isolated data: import, edit classification/steps, create a round, register/attach an environment, reject missing registration, append results, reload, export/import and prepare a subsequent no-diff smoke round. Verify another environment's pass cannot clear a failure, and old rounds remain unchanged. Check stale-tab saves preserve the newer state.

For automated browser fixtures, serve the Skill directory and open `tests/browser-store.html`, `tests/browser-ui.html` and `tests/browser-annotations.html`. They create uniquely named disposable databases, test real transactions, deep-link context and annotation interaction, and report PASS/FAIL on the page. These browser checks complement the Node suite; they are not run by the shell gate.

Deliver the functioning URL, where data is stored, backup/export instructions, and tested limits. Do not mark demonstration observations as real product-test results or claim multi-user/cloud persistence from this template.
