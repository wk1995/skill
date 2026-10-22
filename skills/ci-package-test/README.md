# CI Package Test

Language: **English** | [简体中文](README.zh-CN.md)

`ci-package-test` connects CI packages, PR-derived cases and a reusable web test workbench across platforms and distribution channels. The workbench organizes versions, plans, rounds, environments/devices and execution records. Ordinary CI archives artifacts; external publication requires an explicit request. The initial version remains `0.0.1`.

## How To Use It

```text
Build a test package through CI and prepare regression cases for this PR.
Improve our testing process and display cases, rounds, environments and results in a reusable web workbench.
Use the existing workbench for the next round: failures first, all smoke cases, then cases from the release PR diff.
Prepare the web build in the specified test environment and record browser/configuration with each result.
Publish the verified artifact from CI run <run-id> to the specified distribution channel.
```

Complete test-process or web-display requests deliver a working web workbench, reusing an existing implementation or adapting the bundled [template](assets/workbench/). Build-only requests produce artifacts. Installation, execution, environment deployment and external publication follow the requested scope. For variant-based builds, Release is the default when supported.

The template supports version/plan/round navigation, multi-type cases, failure/smoke selection, environment registration, timestamped observations, immutable round definitions, JSON import/export and deep links. Storage is browser-local IndexedDB; shared collaboration needs a project-owned server. Serve a copied template with `python3 -m http.server 4317 --bind 127.0.0.1 --directory <workbench-directory>`. It starts empty: import a plan based on actual changes, not demonstration results.

See [SKILL.md](SKILL.md), [web delivery](references/web-workbench.md), [CI and publication](references/ci-and-publication.md) and [test rounds](references/test-rounds.md). Template tests: `node --test skills/ci-package-test/tests/workbench.test.mjs` from this repository (Node.js 18+). The immutable sync ID retains its original value across the rename.

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
