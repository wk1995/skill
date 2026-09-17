---
name: pr-review-loop
description: Drive a pull-request review loop that reviews the current head, posts each round's confirmed findings to the pull request under an attributed marker, fixes them, commits and pushes the fix, and reviews again until one round produces no confirmed findings. Use when a request names a pull request and asks to review it, to review and fix it, or to keep reviewing until it is clean. Do not use when no pull request is identified, when the user asks for a read-only review or a local report, or for pull-request administration such as creating, retitling, approving, or merging.
metadata:
  sync_id: "pr-review-loop"
  version: "0.1.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/pr-review-loop
  triggering:
    include:
      - "Review a specific pull request, or review and fix it, including requests that identify the pull request by number, link, or unambiguous reference."
      - "Post review findings as comments on a pull request, then fix, commit, and push them."
      - "Keep reviewing a pull request after each fix until a round reports no findings."
      - "Resume an unfinished review loop on a pull request whose head has moved since the last round."
    exclude:
      - "No pull request is identified: reviewing a local diff, branch, file, or snippet that only needs an answer in the conversation."
      - "The user asks for a read-only review or report and states that nothing should be commented, committed, or changed."
      - "Pull-request administration without review: creating, editing, retitling, labeling, approving, closing, or merging a pull request."
      - "Resolving conflicts, rebasing, or repairing a broken worktree when no review was requested."
      - "Authoring or changing the standards that code review should apply."
---

# PR Review Loop

## Scope

This Skill owns the loop and only the loop:

```text
review current head
        |
   confirmed findings?
        |             \
       yes             no
        |               \
comment on the PR        post the passing comment
under the marker               |
        |                      stop
   fix -> verify -> commit -> push
        |
   next round (back to review)
```

It owns attribution, round ordering, the evidence each round leaves behind, and
the stopping conditions. It does **not** own the review method — the passes,
matrices, severity scale, invariants, and completion criteria applied inside a
round come from an external source listed in
[Where The Review Method Comes From](#where-the-review-method-comes-from).
Never restate the method here, and never manufacture or inflate findings to keep
the loop running.

## Trigger Gate

Every condition must hold before the first round starts:

1. A specific pull request is identified — a number, a URL, or a reference that
   resolves to exactly one open pull request. Never guess by picking the most
   recently updated pull request.
2. The request is to review that pull request, or to review and fix it.
3. The loop can write where it must write: commenting on the pull request and
   pushing to its head branch.

If the pull request is ambiguous, ask which one instead of starting. If a write
capability is missing, do not start a loop that cannot finish — report the
limitation and offer a review-only answer.

## Attribution

Every artifact this loop produces must identify the run that produced it.

| Artifact | Required marker |
| --- | --- |
| Pull-request comment, first line | `[<platform>][<model>]` |
| Commit message | The repository's commit convention, carrying the same platform and model |

Resolve the two values before writing anything:

- `<platform>` — the agent platform actually executing this loop, in its own
  product spelling.
- `<model>` — the detailed name of the model actually in use, as specific as the
  session allows. Prefer an exact versioned identifier; fall back to the most
  specific family name the context supports.

If the model cannot be determined from the session, ask before the first write.
A placeholder marker is allowed only when the user accepts it, and the round
report must say which marker was used. Never write a marker claiming a platform
or model other than the running one. When a repository defines a stricter commit
prefix, that convention governs commits while the comment marker keeps the
`[<platform>][<model>]` shape.

## Preconditions

- Resolve the repository, pull-request number, base branch, head branch, and
  exact head commit. Record the head commit before reviewing; it defines the
  round.
- Confirm write access and the comment channel first, so a round cannot fail
  after the fix is already written.
- Read the pull-request description and every existing review thread. Rounds of
  this loop must stay distinguishable from comments by other reviewers and from
  earlier loops.
- Fix on the pull request's head branch. Never prepare a fix on an unrelated
  branch and push it at the pull request.

## The Loop

Start at round 1 and keep a round ledger — round number, head commit, findings,
action taken, result. Every round ends in exactly one of three ways: findings →
another round; no findings → stop as passed; cap reached → stop and escalate.

### Step 1 — Review the current head

- Pin the round to one exact head commit and review that commit, not the working
  tree and not a moving branch.
- Apply the review method from the sources below.
- Separate confirmed findings from open questions. Only confirmed findings may
  reach the pull request; open questions stay in the round report.

### Step 2 — Round with findings

Perform these in order. The comment comes first so the finding is on the record
before the code changes.

1. **Comment.** Post this round's confirmed findings to the pull request under
   the attribution marker. Default to one comment per round so the thread stays
   readable; use a line comment only when a finding is bound to one specific
   line. Before posting, read the existing comments and skip anything already
   reported against the same head commit; label later rounds explicitly with
   their round number. Pass a multi-line body through a file rather than
   escaping it inline, and never post a finding the round did not verify.
2. **Fix.** Address each finding. Do not bundle unrelated refactoring. Record
   every finding as fixed or as not-fixed with a reason. A finding left unfixed
   must be answered on the pull request under the same marker instead of being
   silently dropped.
3. **Verify.** Run the checks the change affects. A red check is work for this
   round, not a reason to postpone the push.
4. **Commit and push** to the pull-request head branch using the repository's
   commit convention. Never force-push and never rewrite pushed history.
5. **Confirm the push landed** — observe the new head commit on the pull request
   before starting the next round, so a round can never be reviewed twice or
   reviewed in the wrong state.

### Step 3 — Round with no findings

Post the passing comment under the marker, naming the reviewed range and the
exact commit, then stop. Do not start another round to look thorough.

## Stop Conditions

Stop and report as soon as any of these applies:

- **Passed** — a round produces no confirmed findings.
- **Cap** — a round limit was reached (default 5) with findings still open. Stop
  editing, keep the unresolved findings on the record, and escalate for a
  decision instead of looping.
- **Stalled** — two consecutive rounds produce the same findings that were
  reported as not-fixed. This is a decision point, not a retry point.
- **Blocked** — the loop cannot comment or push: missing authentication, branch
  protection, a conflicting head, or an unavailable dependency. Report it; do not
  work around a protection rule.
- **Already clean** — the current head has no confirmed findings and no commit
  was added since the last passing round. Confirm the state, post the passing
  comment for that head, and stop instead of re-reviewing an unchanged commit.

## Boundaries

- Do not merge, approve, close, retitle, label, or delete branches.
- Do not edit or delete another author's comments. Reply by quoting and adding
  the marker.
- Do not force-push, rewrite pushed history, or bypass a protection rule.
- Do not change files unrelated to the findings.
- Do not comment unverified claims, and do not let a passing check stand in for
  a review that was not performed.
- Do not continue the loop past a stop condition.

## Where The Review Method Comes From

This Skill deliberately defines no review criteria. At the start of each round,
resolve the method from the first applicable source and use it as authoritative
for what that round must check:

1. the repository's own review standard — a review playbook, contribution guide,
   or repository instructions;
2. the project's documentation for review, testing, and release expectations;
3. criteria the user stated for this specific pull request;
4. the host's general code-review capability.

Record in the round report which source was used, and say so plainly when no
source was found instead of silently reviewing with no standard.

## Round Report

Close with one message: the pull request and its title, how many rounds ran, per
round the findings by severity and how each was resolved, the open questions that
were deliberately not posted, the current head commit and check status, and the
conclusion — passed, stopped at the cap, stalled, or blocked. Deliver the result,
not the process log.
