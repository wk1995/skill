## Summary

Describe the concrete problem, resulting behavior, and scope. Explain necessary
coupling if independently reviewable behaviors are combined.

## Invariants And Affected Entry Points

List the properties that must remain true and the new or existing entry points
that depend on them, including unchanged callers of changed helpers or state.
For documentation-only changes, identify the affected rules and consumers.

## Validation

### Version Decision

Follow [the versioning policy](https://github.com/wk1995/skill/blob/main/docs/versioning-policy.md).
For each affected versioned component, state its version field, previous release,
proposed version, and PATCH / MINOR / MAJOR / no-bump decision with compatibility
evidence. For repository-only changes, state why no component version is affected.
A MAJOR bump needs a concrete old/new behavior example and migration steps, or
an explicit first-stable contract and readiness evidence. Link the owning
changelog entry with its UTC date when assigning a release version.
The owning entry must include the policy's `Change-Type`, `Summary`, and
`Compatibility` fields and any required breaking/stable evidence. CI compares
the declaration with the actual version increment; reviewers verify its truth.

### Checks

- [ ] I ran `bash tests/pr-review-gate.sh origin/main` from a clean, committed worktree.
- [ ] I reviewed deletions, renames, executable-bit changes, and generated files in the full PR diff.
- [ ] I added negative and state-sequence tests for changed behavior where applicable.
- [ ] I traced every destructive or persistent entry point from validation to its first mutation and tested direct invocation without relying on a prior `--check`.
- [ ] I exercised applicable path-identity, nesting, recursive reserved-name, and missing-executable cases from `docs/pr-review-playbook.md`.
- [ ] I confirmed rejected operations leave source data, unselected state, existing outputs, and snapshots unchanged.
- [ ] I verified external product claims against current authoritative documentation or versioned product configuration.
- [ ] For each confirmed defect, I checked sibling entry points and representations governed by the same invariant and recorded the results below.
- [ ] I verified affected distributed commands from real artifacts outside the source checkout where applicable.

Explain inapplicable checks in the ledger; do not check boxes for work not done.

## Evidence

Follow [the review playbook](https://github.com/wk1995/skill/blob/main/docs/pr-review-playbook.md). Fill in the ledger
before the first review and update its evidence after fixes. A linked review
document containing the same fields can replace the inline tables.

- Exact base SHA:
- Exact reviewed head SHA:
- Environment (OS, filesystem, runtime; controlled substitutes):
- Gate command and result (clean committed head):

| Invariant / finding | Entry point and validation → first mutation | Scenario / sequence | Test or command | Result and observed state | Gap / reason / residual risk |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Use PASS, FAIL, NOT RUN, or N/A with evidence; explain every NOT RUN or N/A.
For mutations, record preserved inputs, unselected locations, and persisted state
after rejection or failure. Record authoritative sources and version scope for
external product claims. Identify carried-forward evidence by its original head
SHA and explain why it still applies; rerun affected cases and the final gate.

## Finding Resolution (When Fixing Review Findings)

| Original finding / trigger | Violated invariant | Sibling entry points checked | Fix commit | Regression evidence |
| --- | --- | --- | --- | --- |
| | | | | |

Link repeated independent confirmations to the original finding. State whether
the regression fails on the affected version and passes after the fix, or explain
why the old version was not run. Link to ledger rows for the expanded coverage.
