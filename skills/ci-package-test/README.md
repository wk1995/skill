# CI Package Test

Language: **English** | [简体中文](README.zh-CN.md)

`ci-package-test` connects CI packages, PR-derived cases and a reusable web test workbench across platforms and distribution channels. The workbench organizes versions, plans, rounds, environments/devices, execution records and annotations. Ordinary CI archives artifacts; external publication requires an explicit request. The initial version remains `0.0.1`.

## How To Use It

```text
Build a test package through CI and prepare regression cases for this PR.
Improve our testing process and display cases, rounds, environments and results in a reusable web workbench.
Support saved web comments and Codex browser-native annotations, with excerpts, replies and resolution status.
Express case prerequisites: require LOGIN01 and CART01 to pass before PAY01 in this round/environment.
Define what to test next after pass, failure, partial execution, blocking or skipping; distinguish blockers from product defects.
Use machine-readable state machines for cases/executions and export current states, event history and allowed next actions for AI.
Use the existing workbench for the next round: failures first, all smoke cases, then cases from the release PR diff.
Prepare the web build in the specified test environment and record browser/configuration with each result.
Publish the verified artifact from CI run <run-id> to the specified distribution channel.
```

Complete test-process or web-display requests deliver a working web workbench, reusing an existing implementation or adapting the bundled [template](assets/workbench/). Build-only requests produce artifacts. Installation, execution, environment deployment and external publication follow the requested scope. For variant-based builds, Release is the default when supported.

The template supports version/plan/round navigation, multi-type cases, failure/smoke selection, environment registration, timestamped observations, immutable round definitions, JSON import/export and deep links. Storage is browser-local IndexedDB; shared collaboration needs a project-owned server. Serve a copied template with `python3 -m http.server 4317 --bind 127.0.0.1 --directory <workbench-directory>`. It starts empty: import a plan based on actual changes, not demonstration results.

Annotations can target a case, a field or an execution record; they retain the quoted text and original snapshot, support replies and resolve/reopen events, and are included in archives. Browser-native tools use the stable link/DOM context and a copy-context button. Sending a native annotation to chat is provided by the host; confirmed comments can be recorded in the workbench as native-origin annotations. There is no automatic chat send or writeback. See [annotations](references/annotations.md).

New rounds follow draft → ready → running → completed; executions are tracked separately per case/environment, with explicit start/retest and guarded outcomes. Events retain actor, time and original evidence. Ending a round does not mean all passed. **Export AI state snapshot** includes the shared contract, original archive, current states and allowed next actions. Older archives remain explicitly legacy; no history is fabricated. See [state machines](references/state-machine.md).

Cases can define explicit outcome branches to another test, retry, wait (with a recovery condition), or end that branch. The webpage and AI show the concrete target procedure per environment. Known failures remain unresolved through partial/blocked/skipped retests until a passing retest. Older flat cases show missing routing explicitly. See [conditional tests and outcome meanings](references/conditional-tests.md).

Use `dependsOn` for required prerequisite cases and `next` for outcome branches. The workbench orders prerequisites, rejects cyclic dependencies, blocks ineligible starts and exposes exactly which cases are missing. Upstream retests make downstream evidence stale until revalidated; original records remain intact. See [dependencies](references/dependencies.md).

See [SKILL.md](SKILL.md), [web delivery](references/web-workbench.md), [CI and publication](references/ci-and-publication.md) and [test rounds](references/test-rounds.md). Template tests: `node --test skills/ci-package-test/tests/*.test.mjs` from this repository (Node.js 18+). The immutable sync ID retains its original value across the rename.

## When It Triggers

- CI test-package delivery for mobile, desktop, web, services or libraries.
- Regression cases tied to a PR/change set and exact package.
- Creating, improving or operating a reusable web testing process with plans, rounds, environments and records.
- Follow-up execution or explicitly requested publication in this workflow.

## When It Does Not Trigger

- Local-only packaging without a CI or test-workbench task.
- Infrastructure changes without test-package delivery or process management.
- Unrelated websites or QA theory without an actionable testing workflow.
- Unrequested source version changes, branch promotion, fixes, PR creation, merges or tags.
