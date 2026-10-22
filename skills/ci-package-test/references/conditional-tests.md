# Conditional next tests and outcome meaning

Read this when authoring executable cases or determining what to test after an outcome. A lifecycle action such as `start` is not a concrete next test. Give newly authored cases observable nodes and explicit outcome branches, and show target prerequisites, steps and expected results in both the webpage and AI handoff.

## Choose the outcome from evidence

| Status | Meaning | Login example | Follow-up |
| --- | --- | --- | --- |
| `passed` | All required checks for this execution met expectations | Login succeeds and the expected identity is shown | Verify session persistence |
| `failed` | An observed behavior violates an expected result | Valid credentials yield an error or the wrong account | Capture diagnostics, report the defect; later retest the original case |
| `partial` | Only part was executed/verified; remaining work is unverified, with no new known failure hidden | Login succeeded, but session persistence has not been checked | Test the explicitly remaining part or retry the original case |
| `blocked` | A required prerequisite/dependency is unavailable and prevents execution or continuation | No valid account is available, or the required external test service is unavailable | Restore the named condition, then retry; independent cases may continue |
| `skipped` | An explicit scope/priority decision not to execute the case in this round | This authorized round excludes a browser/configuration | Record the reason and continue the defined independent case |

If 7 checks pass and 3 fail, use failed; do not describe that as merely partial. If 7 checks pass and 3 have not been verified, use partial and identify completed/unverified work. Once an environment prerequisite is confirmed healthy, a product's failure to connect or respond as specified is a failure, not automatically a blocker. An internal product failure may also block downstream cases: record the upstream case as failed and downstream cases as blocked, linking the upstream evidence in their notes. Skipping never changes failed into passed or establishes coverage. An execution that has not started may be explicitly blocked or skipped through `defer`, with a reason, `executedAt: null` and no fabricated start event. If execution already began, retain its real execution time and append the blocked/skipped result.

Existing known failures remain unresolved through start, partial, blocked or skipped attempts. Managed execution projections include `unresolvedFailureId`, and overall summaries remain failed until the same case/environment has a real passing retest. The current execution phase/result remains separately visible, so a skipped retest can coexist with an unresolved earlier failure. Another diagnostic case or device passing cannot clear it. Legacy observation-only rounds keep their previous summary contract and are explicitly marked legacy.

## Case branch format

Keep the existing identity, preconditions, steps and expected result, and add `next`. This illustrative excerpt assumes SESSION01, LOGIN_DIAG01 and OFFLINE01 are separately defined with concrete procedures in the same plan:

```json
{
  "id": "LOGIN01",
  "title": "Login with valid credentials",
  "priority": "P0",
  "types": ["smoke", "functional"],
  "preconditions": "A valid test account and reachable test service",
  "steps": "Enter credentials, submit, and inspect the current identity",
  "expected": "The home page shows the correct account",
  "next": {
    "passed": {"action": "test", "caseId": "SESSION01", "reason": "Verify the authenticated session survives reopening"},
    "failed": {"action": "test", "caseId": "LOGIN_DIAG01", "reason": "Collect reproducible error, response and log evidence"},
    "partial": {"action": "retry", "caseId": "LOGIN01", "reason": "Complete the unverified checks recorded in notes"},
    "blocked": {"action": "wait", "reason": "Restore prerequisites before retrying", "resumeWhen": "A valid account is available and the external test service is reachable"},
    "skipped": {"action": "test", "caseId": "OFFLINE01", "reason": "Continue independent authorized offline coverage"}
  }
}
```

Define exactly the five result keys when `next` is present. Each branch requires an action and a reason. Unknown branch fields reject rather than overwriting trusted execution context:

- `test`: a concrete `caseId` in the same plan; target definitions must contain actionable preconditions, steps and expected results.
- `retry`: `caseId` must equal the current case ID; retain earlier evidence. Retry is a recommendation, not permission for repeated automatic execution or environment changes.
- `wait`: requires `resumeWhen`, describing a concrete recovery condition. It has no target case; retry the current case explicitly after confirming the condition.
- `done`: this branch has no further test. It has no target case and does not close the round, mark other cases passed, or clear failures.

For multi-step work, split independently observable checks into stable case nodes when different outcomes require different next procedures. Do not add a universal diagnostics node to every project: define branches from actual changes, expected behavior and authorized scope. If partial completion needs a specific remaining subcase, route to that explicit node; notes must identify what was completed and what remains. Routed partial results require nonempty notes; old flat cases retain their previous archive contract.

## Prerequisites versus branches

Use [dependsOn](dependencies.md) for required upstream cases, separate from outcome-based `next`. A branch target with unmet prerequisites cannot start; guidance identifies an actionable ancestor instead. Explicit blocked/skipped branches may continue independent authorized work. Dependency cycles reject even though retry/routing cycles are permitted.

Put "this target needs another case to pass" on the target's `dependsOn`, so incoming routes and direct starts share one rule. `next` selects by the current case's five outcomes; it does not evaluate arbitrary conditions on other cases or accept `when` expressions. Choosing different targets based on another case's result would require a separately specified routing extension. See the [combined example and placement table](dependencies.md#where-to-put-the-condition), and the [routing/readiness flowchart](../README.md#routing-and-prerequisite-flow).

## Runtime and persistence

The shared contract is `CONTRACT.routing` in `workflow.mjs`; `routing.mjs` validates branch shape/targets and derives `nextTest`. Direct plan import, case edit, archive import and round validation all enforce it before the IndexedDB put. Old cases without `next` remain valid and show `unconfigured`; never guess or fabricate branches. The current-definition editor accepts `next` JSON; edits affect subsequent rounds and leave historical branch snapshots intact.

Round preparation recursively freezes all reachable targets after failed/smoke/change/unfinished selection, retaining `conditional-next` reasons and deduplicating IDs. Cycles terminate during selection; navigation never executes the graph automatically. All selected cases still require explicit outcomes per environment. An unvisited branch remains untested; deliberately excluded branches may be explicitly skipped with reasons. No inferred branch result or false all-pass claim is allowed. End-of-round checks still include conditional targets.

`nextTest(round, caseId, environmentId)` and the AI export's execution `nextTest` include source round/case/environment, latest state, exact observation ID, notes/evidence, unresolved failure ID, chosen action/reason, recovery condition or frozen target definition, and target's current state/availability. `nextActions` continues to mean legal lifecycle operations; `nextTest` means concrete test guidance. Closed rounds show the recommendation as unavailable until explicitly reopened. Opening a target only changes navigation, preserving current results and environment selection.

Validate malformed/missing branches, unknown targets, recursive/cyclic graphs, same-label environment isolation, editing/import conflicts, old archives, partial/blocked/skipped meaning, failure persistence, exact AI/UI agreement and read-only navigation. Use disposable fixtures, not fabricated product evidence.
