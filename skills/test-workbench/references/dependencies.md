# Prerequisite cases

Use `dependsOn` when a test needs successful evidence or prepared state from another case. This is separate from `next`: prerequisites control whether a case can start; outcome branches describe what to test afterward.

## Where to put the condition

| Requirement | Definition |
| --- | --- |
| After LOGIN01 passes, continue with PAY01 | `LOGIN01.next.passed` targets PAY01 |
| PAY01 requires both LOGIN01 and CART01 to pass before execution | `PAY01.dependsOn` lists both IDs |
| Select different targets according to another case's result | A separate routing-condition capability would be needed; the current `next` format has no cross-case predicates |

Keep each prerequisite on the target, so every path to that target and direct starts use the same guard. Do not duplicate it in every incoming `next` branch or add unsupported `when` fields. A failed prerequisite does not implicitly choose another route, skip the target or mark it failed. The configured route still identifies the requested target; guidance first identifies the missing prerequisite. Explicit independent branches remain available through their declared outcomes.

The [English](../README.md#routing-and-prerequisite-flow) and [Chinese](../README.zh-CN.md#路由与依赖流程) flowcharts show the same routing and readiness checks.

For example, use these definition excerpts together (complete the normal case fields, and define CART01 with concrete steps and an expected result in the same plan):

```json
{
  "id": "LOGIN01",
  "next": {
    "passed": {"action": "test", "caseId": "PAY01", "reason": "Verify payment after login"},
    "failed": {"action": "retry", "caseId": "LOGIN01", "reason": "Retain defect evidence and explicitly retest login when ready"},
    "partial": {"action": "retry", "caseId": "LOGIN01", "reason": "Complete the unverified login checks"},
    "blocked": {"action": "wait", "reason": "Restore login prerequisites", "resumeWhen": "The test account and required external service are available"},
    "skipped": {"action": "done", "reason": "No further test on this login branch; other selected cases still need explicit outcomes"}
  }
}
```

```json
{
  "id": "PAY01",
  "title": "Submit an order with a valid cart",
  "priority": "P0",
  "types": ["smoke", "functional"],
  "dependsOn": ["LOGIN01", "CART01"],
  "preconditions": "The same environment has an authenticated account and the expected cart",
  "steps": "Submit the prepared cart and inspect the order",
  "expected": "The order is created with the expected account, contents and amount"
}
```

LOGIN01 and CART01 must be defined in the same plan. All listed prerequisites must currently pass in the same round and environment. Empty/omitted `dependsOn` means no case dependency. Other devices, previous rounds, partial results, skipped cases, blocked cases, unresolved failures and stale passes do not satisfy a prerequisite. Passing a prerequisite supplies recorded evidence; it does not transfer session data or credentials between environments. Check the target case's actual preconditions too.

After a valid LOGIN01 pass, the declared route requests PAY01. If CART01 is untested, running, failed, partial, blocked, skipped or stale, `nextTest` recommends CART01 (or its first unmet ancestor) instead, and starting PAY01 rejects. Once CART01 has a current valid pass, recomputing the recommendation from LOGIN01 points to PAY01. Merely opening CART01 or PAY01 changes navigation only. If CART01 has no `next` definition, its own recommendation remains explicitly unconfigured; return to LOGIN01's route or open PAY01 rather than inventing a new branch. The blocked start does not itself append a blocked observation.

## Graph and selection

Dependency IDs must be unique and known; self-dependencies and dependency cycles reject. A dependency is not merely a suggested order. For example, LOGIN01 → PAY01 in `next` and PAY01 depending on LOGIN01 is valid: routing may contain cycles, but the dependency graph must be acyclic.

Round preparation includes recursive prerequisites and branch targets, freezes all selected definitions, and orders prerequisites before dependent cases while preserving the relative order of available independent cases. Dependency precedence may move a prerequisite ahead of a failed/smoke case; selection reasons retain the original failure/smoke/change/conditional reasons plus `dependency`. Never silently drop a mandatory prerequisite to retain a display order.

Do not auto-execute prerequisites, invent passing results or mark downstream cases failed because an upstream case failed. The upstream observed violation remains failed; downstream execution cannot start until prerequisites are valid. Pending cases stay pending with explicit unmet dependencies. An operator may record them blocked (or explicitly excluded/skipped) without fabricated execution time; independent branches may continue. Existing explicit blocked/skipped `next` routes remain authoritative for independent work, with dependency checks applied to their targets.

## Guards, history and freshness

The shared dependency module validates definitions and computes readiness; workflow replay enforces it before a start event. Single and batch starts, direct calls and imported history all use the same guard. A batch cannot start an unpassed prerequisite and its dependent together: starting the prerequisite is not passing it, and rejection preserves the entire batch's prior state.

At start, replay derives `dependencyEvidence` containing each direct prerequisite's exact observation ID. This is projected from validated history, not trusted caller-provided metadata. Later upstream attempts/outcomes invalidate dependent evidence, including transitively. A prerequisite passing again with a new observation does not silently renew downstream old passes; retest each dependent against the current evidence. Stored observations, timestamps, frozen definitions and old events remain unchanged.

- `dependenciesSatisfied`: all prerequisite cases currently have valid passes in this environment.
- `unmetDependencies`: case IDs with current state, observation ID, unresolved failure and stale flags.
- `dependencyEvidence`: prerequisite observation IDs pinned when the current attempt started.
- `currentEvidence`: current prerequisite observation IDs, for comparison.
- `dependencyStale`: a started attempt's prerequisite evidence no longer matches or a prerequisite is no longer valid.
- `validPass`: the current state is passed, no failure is unresolved, and prerequisite evidence is current.

A dependency change during execution rejects passed/failed/partial saves from that stale attempt; record why execution was blocked or stopped, then restart after prerequisite passes are current. The actual observation stays in history if it was recorded before the upstream change. A stale dependent pass cannot close the round as completed; fresh validation or an explicit non-pass result is required. An unresolved product failure still takes priority over dependency blocking in the overall summary.

## Webpage and AI

The current-definition editor accepts prerequisite IDs. The webpage disables an ineligible start and displays unmet cases and stale evidence. The AI snapshot exposes readiness and evidence; `nextActions` omits illegal starts/results. `nextTest` follows the declared dependency chain to the first actionable prerequisite, including its concrete steps and expected result. A stale passed case instead requires its own fresh retest after prerequisites recover. During a stale running attempt, guidance says to record a block first. Navigation is read-only and retains environment selection.

Model validation runs on plan edits/import, frozen round definitions and archive merge; UI-only disabling is insufficient. Definition changes affect future rounds and never rewrite existing dependency snapshots. Old dependency-free archives remain valid without migration. Dependency/result validity is derived from recorded test evidence, not an automatic assertion about the live product or environment.
