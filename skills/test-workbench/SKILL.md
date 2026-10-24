---
name: test-workbench
description: Manage a reusable web testing workbench with standardized cases, execution records and revision-bound summaries. Coordinate dependencies, next-test guidance, environments, Issue evidence, web/native annotations and repeat testing, using GitHub Issues by default or repository files. Connect exact CI packages and PR changes across platforms when requested; external publication requires an explicit request.
metadata:
  sync_id: "android-ci-fir-test"
  version: "0.0.3"
  triggering:
    include:
      - Build a test package through CI from a selected source ref for any platform or distribution channel.
      - Derive regression cases from a PR or change set and connect them to the exact package.
      - Improve, visualize, create or maintain the testing process as a reusable web workbench with cases, rounds, environments and records.
      - Add or use persistent web annotations and browser-native annotation context within this testing workflow.
      - Continue this workflow by preparing or installing a package, executing tests, recording results or preparing subsequent rounds.
      - Explicitly publish a verified CI artifact through the project's separate publication process.
    exclude:
      - Local-only packaging without a CI or test-process/workbench task.
      - Infrastructure work without test-package delivery or test-process management.
      - Unrelated website design or QA theory without an actionable testing workflow.
      - Unrequested source version changes, branch promotion, code fixes, PR creation, merging or tagging.
---

# Test Workbench

Manage an executable, visible testing process with standardized case definitions, execution history and revision-bound summaries; connect actual code changes and CI artifacts when part of the task. The reusable web workbench is a core capability: manage version → plan → round, separate case definitions from observations, and preserve results across packages, environments and rounds. Support mobile, desktop, web, service and library projects using their existing toolchains.

## Establish scope

Inspect repository instructions, build/test configuration, workflows and any existing workbench. Determine the source ref, package target, build variant, PR/change set, environments and requested stages. Infer known inputs before asking. For variant-based builds default to `release` when supported; otherwise use the project's documented test-package mode.

For a test-data/workbench task, select one authoritative source using [references/data-sources.md](references/data-sources.md): **GitHub Issues is the default for a new project**; **repository-tracked files** are the explicit alternative. Preserve an existing project's recorded choice unless a switch is requested. Both modes use the same case/execution state machines, dependencies, routing, annotations and flow graph. Browser storage and exports are caches/backups, not a third primary mode. Establish source identity and the actual read/write path before claiming a save; unavailable access or an absent adapter leaves that integration pending, never silently switches modes.

A build-only request produces CI artifacts. A channel name, release variant or successful CI does not authorize external distribution. Publish only when explicitly requested or already authorized in a release flow. Installation, test-environment deployment, execution, source fixes and external website hosting follow the requested scope.

For “完善测试流程”, “以网页展示测试”, or a complete package-to-regression workflow, include the web workbench as a deliverable. Reuse and improve the current workbench; when absent, adapt [assets/workbench/](assets/workbench/) using [references/web-workbench.md](references/web-workbench.md). Do not stop at a prose checklist or generate a new app for every round.

## Preserve project integrations

Read [references/project-integrations.md](references/project-integrations.md) when adopting or extending an existing workbench. For UI adoption or usability work, also read [references/ui-adoption.md](references/ui-adoption.md); distinguish the actual bundled UI from documented adapters and keep useful project navigation. Inventory the actual UI, service, data readers/writers and host tools before replacing anything. Preserve useful project capabilities even when absent from the bundled template:

- Android device discovery and registration through ADB, including USB/wireless identity deduplication and revalidation before selection.
- Explicit association of imported historical device records with a registered environment, preserving original snapshots and configuration boundaries.
- Live AI/WebMCP tools for reading context, navigating, preparing rounds and recording authorized observations through the same guarded operations as the webpage.
- Actual GitHub PR comparison and revision-bound change analysis before failure/smoke/change-based next-round selection.
- Existing local screenshot upload, preview and agent upload when selected by the project; keep Issue attachments as the default for new integrations.
- Project-selected per-round single-file/current-result storage and conditional conclusion tabs. Preserve the selected history policy; do not silently compact managed event history or add historical snapshots against the user's instruction.

These are integration procedures, not claims that the starter implements each adapter. Report implemented, verified and pending capabilities separately. Existing custom archives need an explicit format adapter; never rename their schema version or discard fields to make them pass the bundled validator. User-selected current-result archives retain their actual scope and must not be presented as managed append-only history.

## Package and verify

Read [references/ci-and-publication.md](references/ci-and-publication.md) before dispatching CI or publishing.

1. Resolve the requested remote ref to a commit. Preserve local changes if checkout switching is requested.
2. Inspect workflows and called scripts at the relevant ref. Choose a packaging path that archives outputs only; verify the active CLI identity and repository before remote writes.
3. Dispatch verified inputs and identify the exact run. Compare its actual checkout SHA with the intended source, including custom checkout inputs. Track completion; failed, skipped, mismatched or ambiguous runs are not usable packages.
4. Verify target-appropriate package identity, version, signature/provenance when applicable, checksum, required companion files and repository-specific checks. Record run/attempt, artifact names and actual retention.
5. If explicitly requested, publish the same verified bytes through the separate publication path. Verify its outcome before reporting a distribution URL.

Do not change source versions, bypass trusted-ref checks, rebuild silently for publication or replace required signing to force a build through. Static checks do not establish runtime coverage.

## Improve and visualize the testing process

Read [references/test-rounds.md](references/test-rounds.md) for cases, environments and history, and [references/web-workbench.md](references/web-workbench.md) for web delivery.

- Read the complete PR/change diff at exact base/head, including affected callers. Confirm which changes exist in the package. Cases for absent changes remain blocked.
- Prepare stable IDs, priorities, multiple test types, prerequisites, steps, expected outcomes and evidence requirements. New results remain pending.
- Use the [unified data format](references/data-format.md) for case definitions, execution records and test summaries in both primary-source modes. Keep required fields/enums, stable IDs, source/version/environment references and complete workflow history; decode storage envelopes into the same archive before rendering. Validate real data with `scripts/validate-test-data.mjs`; ordinary Issue prose/labels/closure cannot supply machine outcomes. Read the linked runnable format examples only as fixtures, never real evidence.
- Represent testing data with a versioned, machine-readable contract and explicit state machines; read [references/state-machine.md](references/state-machine.md). Keep definitions separate from executions keyed by round/case/environment. Use the same transition validation for AI, the webpage, direct calls and imports; append events with actor/time/evidence and expose current state, guards and legal next actions. Never infer a pass from prose or overwrite a previous attempt. New bundled rounds use enforced lifecycle events; preserve legacy history without inventing transitions.
- Model prerequisite cases separately from outcome branches: read [references/dependencies.md](references/dependencies.md). Put required passes on the target's `dependsOn`; `next` selects by the current case's outcome, then checks the target's dependencies. Do not duplicate prerequisites on incoming routes or invent cross-case `when` fields. Validate an acyclic dependency graph, freeze recursive prerequisites and require current passes in the same round/environment before execution. Expose unmet prerequisites and stale dependency evidence in the webpage/AI, preserve historical results, and revalidate descendants after upstream retests.
- Define concrete next tests for each outcome when authoring cases: read [references/conditional-tests.md](references/conditional-tests.md). Include success, failure, partial, blocked and skipped branches with explicit targets or retry/wait/done actions. Explain partial completion, blocker recovery conditions and skip reasons; never hide a known failure behind another status. Show per-environment guidance and original evidence in the workbench and AI export. Old cases without branches stay explicitly unconfigured.
- Expose versions, multiple plans per version, multiple rounds per plan, case filters/details, registered environments/devices and append-only observations in the web workbench. Include CI/package/PR links, progress, defects, evidence and coverage gaps.
- Display an interactive webpage flow graph from the frozen round and selected environment: distinguish prerequisite edges from outcome routes, show execution phases plus unresolved failures/stale evidence, highlight the selected case and actual `nextTest` target, and allow read-only case navigation. Keep the graph, detail guidance and AI projection consistent; a diagram must not start tests or fabricate results.
- When useful for direct phone/device operation, provide optional page, entry-path and control-locator hints using [references/test-location.md](references/test-location.md). Show/copy exact test context and declared hints in the webpage and AI handoff. Confirm the live device view before acting, retain actual evidence separately, and leave unknown locations explicitly missing.
- Support persistent annotations with selected excerpts, definition snapshots, replies and resolved/reopened state. Keep annotations separate from outcomes, pin them to the correct case/round/observation, and include them in archive import/export. Read [references/annotations.md](references/annotations.md) for web comments and browser-native annotation linkage; native host transport is not an automatic website-to-chat API.
- Each round includes prior failed cases first, all current smoke cases, change-derived cases, then optional unfinished cases, deduplicated by ID. Smoke runs again after previous passes or an empty diff. Define smoke before starting a round if missing.
- Keep the current library authoritative. Preserve PR-updated steps and classifications until a newer explicit edit supersedes them; distinguish stale imports from intentional edits. Freeze each round's selected definitions.
- Register and select an environment before saving results. For mobile this includes physical device details; for web, desktop, services or libraries it includes browser, OS, runtime, deployment or consumer configuration. A shared model name does not establish identical environments.
- Reuse one workbench and import/update its data for later packages. Validate single/batch saves, imports, stale revisions and round/environment context before persistence. Preserve historical snapshots and observations.
- Default new integrations to screenshots/logs stored directly in the linked GitHub Issue, including in file mode, with Issue association controls and clickable links. Preserve an existing project's explicitly selected local attachment workflow using [project-integrations.md](references/project-integrations.md#local-screenshot-adapter); do not remove a working upload/preview entry without a requested migration. Persist append-only `round.issueLinks` associations in managed archives, include references in conclusions/AI exports, and allow linking an existing record without rewriting its outcome. Saving an association does not upload attachments, verify access, create/comment/close an Issue or synchronize its status. See [references/data-sources.md](references/data-sources.md#record-to-issue-associations).
- Persist and display per-round, environment-bound test conclusions with their archive revision and supporting records; include known failures, skipped/incomplete coverage and stale dependency evidence. A computed test conclusion is not release approval. In file mode include conclusions in the same explicit Git commit as definitions and records.
- Test the workbench with disposable data, then deliver its local URL, primary-source location and export location. Report confirmed Issue writes versus file saves and Git commits separately. The bundled service is local and single-operator; never claim distributed collaboration.
- In the default GitHub Issues mode, read [references/github-issues.md](references/github-issues.md). Use the bundled loopback service and webpage adapters from [references/data-sources.md](references/data-sources.md). GitHub mode uses local gh credentials and verified Issue/comment writes; file mode saves validated snapshots and offers a separate data-only Git commit button. Explicit browser preview remains separate from primary persistence. The initial remote plan defers multi-user concurrency and strict remote audit protection, retaining existing local guards. Before an authorized CLI media upload, require gh 2.99.0+ and `--attach` in the exact command's help; older/missing support needs an authorized installation-channel upgrade or browser-upload fallback. Newer CLI versions still do not make log files supported media attachments.

## Execute and report

Execute the requested stages, preserving existing app/environment data. Distinguish unreliable automation from product defects. Report passed, failed, partial, blocked, skipped, running and untested cases, distinguishing round completion from all-pass. CI success, a different channel or a short run cannot replace the required environment/duration. For Android installation, optionally read [references/android-example.md](references/android-example.md).

Handoff includes source SHA, target/variant/version, CI artifacts/retention, verification evidence, publication outcome if requested, and the web workbench URL when part of the task. Include the selected data-source mode and repository/Issue or file references, confirmed persistence versus pending changes, plan/round, environment, counts, defects/evidence and remaining coverage. A discovered defect authorizes a report, not an unrequested fix or PR.
