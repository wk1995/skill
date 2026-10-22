# Prerequisite cases

Use `dependsOn` when a test needs successful evidence or prepared state from another case. This is separate from `next`: prerequisites control whether a case can start; outcome branches describe what to test afterward.

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
