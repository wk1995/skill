---
name: ci-package-test
description: Connect CI packages with PR-derived regression cases and a reusable web test workbench across platforms and distribution channels. Improve and visualize plans, rounds, environments, execution records, web/native annotation context and repeat testing. Ordinary CI archives artifacts; external publication requires an explicit request.
metadata:
  sync_id: "android-ci-fir-test"
  version: "0.0.1"
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

# CI Package Test

Turn CI artifacts and actual code changes into an executable, visible testing process. The reusable web workbench is a core capability: manage version → plan → round, separate case definitions from observations, and preserve results across packages, environments and rounds. Support mobile, desktop, web, service and library projects using their existing toolchains.

## Establish scope

Inspect repository instructions, build/test configuration, workflows and any existing workbench. Determine the source ref, package target, build variant, PR/change set, environments and requested stages. Infer known inputs before asking. For variant-based builds default to `release` when supported; otherwise use the project's documented test-package mode.

A build-only request produces CI artifacts. A channel name, release variant or successful CI does not authorize external distribution. Publish only when explicitly requested or already authorized in a release flow. Installation, test-environment deployment, execution, source fixes and external website hosting follow the requested scope.

For “完善测试流程”, “以网页展示测试”, or a complete package-to-regression workflow, include the web workbench as a deliverable. Reuse and improve the current workbench; when absent, adapt [assets/workbench/](assets/workbench/) using [references/web-workbench.md](references/web-workbench.md). Do not stop at a prose checklist or generate a new app for every round.

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
- Represent testing data with a versioned, machine-readable contract and explicit state machines; read [references/state-machine.md](references/state-machine.md). Keep definitions separate from executions keyed by round/case/environment. Use the same transition validation for AI, the webpage, direct calls and imports; append events with actor/time/evidence and expose current state, guards and legal next actions. Never infer a pass from prose or overwrite a previous attempt. New bundled rounds use enforced lifecycle events; preserve legacy history without inventing transitions.
- Model prerequisite cases separately from outcome branches: read [references/dependencies.md](references/dependencies.md). Put required passes on the target's `dependsOn`; `next` selects by the current case's outcome, then checks the target's dependencies. Do not duplicate prerequisites on incoming routes or invent cross-case `when` fields. Validate an acyclic dependency graph, freeze recursive prerequisites and require current passes in the same round/environment before execution. Expose unmet prerequisites and stale dependency evidence in the webpage/AI, preserve historical results, and revalidate descendants after upstream retests.
- Define concrete next tests for each outcome when authoring cases: read [references/conditional-tests.md](references/conditional-tests.md). Include success, failure, partial, blocked and skipped branches with explicit targets or retry/wait/done actions. Explain partial completion, blocker recovery conditions and skip reasons; never hide a known failure behind another status. Show per-environment guidance and original evidence in the workbench and AI export. Old cases without branches stay explicitly unconfigured.
- Expose versions, multiple plans per version, multiple rounds per plan, case filters/details, registered environments/devices and append-only observations in the web workbench. Include CI/package/PR links, progress, defects, evidence and coverage gaps.
- Support persistent annotations with selected excerpts, definition snapshots, replies and resolved/reopened state. Keep annotations separate from outcomes, pin them to the correct case/round/observation, and include them in archive import/export. Read [references/annotations.md](references/annotations.md) for web comments and browser-native annotation linkage; native host transport is not an automatic website-to-chat API.
- Each round includes prior failed cases first, all current smoke cases, change-derived cases, then optional unfinished cases, deduplicated by ID. Smoke runs again after previous passes or an empty diff. Define smoke before starting a round if missing.
- Keep the current library authoritative. Preserve PR-updated steps and classifications until a newer explicit edit supersedes them; distinguish stale imports from intentional edits. Freeze each round's selected definitions.
- Register and select an environment before saving results. For mobile this includes physical device details; for web, desktop, services or libraries it includes browser, OS, runtime, deployment or consumer configuration. A shared model name does not establish identical environments.
- Reuse one workbench and import/update its data for later packages. Validate single/batch saves, imports, stale revisions and round/environment context before persistence. Preserve historical snapshots and observations.
- Test the workbench with disposable data, then deliver its local URL and export location. State whether storage is browser-local or shared; never claim collaboration from a local prototype.

## Execute and report

Execute the requested stages, preserving existing app/environment data. Distinguish unreliable automation from product defects. Report passed, failed, partial, blocked, skipped, running and untested cases, distinguishing round completion from all-pass. CI success, a different channel or a short run cannot replace the required environment/duration. For Android installation, optionally read [references/android-example.md](references/android-example.md).

Handoff includes source SHA, target/variant/version, CI artifacts/retention, verification evidence, publication outcome if requested, and the web workbench URL when part of the task. Include plan/round, environment, counts, defects/evidence and remaining coverage. A discovered defect authorizes a report, not an unrequested fix or PR.
