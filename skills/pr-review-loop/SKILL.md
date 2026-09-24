---
name: pr-review-loop
description: Drive a pull-request review loop that reviews the current head, fixes and pushes the confirmed findings, and reviews again until one round produces no confirmed findings. Commenting on the pull request is off by default and happens only when the comment policy enables it for that repository, and every posted comment is labelled with the platform and model that produced it. The loop runs at most ten rounds by default, retries a review that fails to run up to three times, and explains why so many rounds were needed when it stops at the round cap. Use when a request names a pull request and asks to review it, to review and fix it, or to keep reviewing until it is clean. Do not use when no pull request is identified, when the user asks for a read-only review or a local report, or for pull-request administration such as creating, retitling, approving, or merging.
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
      - "Post review findings as comments on a pull request, then fix, commit, and push them, when the comment policy enables comments for that repository or the user asks for comments for this review."
      - "Keep reviewing a pull request after each fix until a round reports no findings."
      - "Resume an unfinished review loop on a pull request whose head has moved since the last round."
    exclude:
      - "No pull request is identified: reviewing a local diff, branch, file, or snippet that only needs an answer in the conversation."
      - "The user asks for a read-only review or report and states that nothing should be commented, committed, pushed, or changed."
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
   comment on the PR    comment the pass
   only if the policy   only if the policy
   enables it           enables it, then stop
        |
   fix -> verify -> commit -> push
        |
   next round (back to review)
```

It owns attribution, round ordering, the comment decision, the evidence each
round leaves behind, and the stopping conditions. It does **not** own the review
method — the passes, matrices, severity scale, invariants, and completion
criteria applied inside a round come from an external source listed in
[Where The Review Method Comes From](#where-the-review-method-comes-from).
Never restate the method here, and never manufacture or inflate findings to keep
the loop running.

## Comment Policy

Commenting is **off unless a policy source enables it**. A machine-wide Skill
that comments by default writes to repositories the user never asked it to write
to, and a loop that grants itself write access cannot be reviewed by the same
standard it applies. Resolve the policy before round 1 and record both the
decision and the source that made it.

Resolve from the first source that exists. A source enables commenting only by
an explicit enable; every other outcome, including a file that is silent about
commenting, is a decision of no comment.

1. **This review** — the user states, for this review, whether to comment. This
   is the only source that can enable commenting for a repository that no
   configuration lists. It decides commenting only: it never pulls a request
   that [Trigger Gate](#trigger-gate) excludes back into the loop.
2. **Project scope** — `<project-root>/.pr-review-loop.yml` in the repository
   under review. When this file exists it decides that repository, so the
   install scope is not consulted for it: committing the file for another key,
   such as a round limit, must never hand this repository's comment decision to
   a different file.
3. **Install scope** — `pr-review-loop.yml` in the directory of the install that
   is executing this loop: the machine-wide allowlist when the machine-wide
   install is running, the project's own allowlist when a project-level install
   is running. Only the running install is read — when both exist, the other one
   is ignored and the two are never merged. Say which install was read. This
   scope applies only to a repository with no project-scope file. When that
   directory must stay clean or read-only, the same file may instead live at
   `$XDG_STATE_HOME/skill/pr-review-loop.yml`, or
   `$HOME/.local/state/skill/pr-review-loop.yml` when `XDG_STATE_HOME` is unset.
4. **Default** — no comment.

The two scopes use different file names — `.pr-review-loop.yml` for the project
scope and `pr-review-loop.yml` for the install scope — but the same keys, and
the same file also carries the limits in [Loop Limits](#loop-limits):

```yaml
# This scope's decision when no target below matches. Only `true` enables
# commenting; omitting the key or writing `false` leaves commenting off.
comment: false
# Repositories that receive comments, matched by git remote.
comment_targets:
  - https://github.com/wk1995/skill.git
  - git@github.com:wk1995/other-repo.git
# Round and retry limits; see Loop Limits.
max_rounds: 10
review_retries: 3
```

Within one file, an explicit enable is:

- the pull request's remote matches an entry in `comment_targets` → comment;
- otherwise `comment: true` → comment;
- otherwise nothing is enabled, and `comment: false` and an omitted key leave
  commenting off for that repository.

Match remotes by normalizing both sides to `host/owner/repo`: drop the scheme
and any `user@`, rewrite `git@host:owner/repo` as `host/owner/repo`, drop a
trailing `/` and a trailing `.git`, and compare case-insensitively. Compare
against the remote whose normalized value equals the pull request's own
`host/owner/repo` — the repository that hosts the pull request. A remote that
points at a different repository on the same host, such as a fork, never
matches. When no remote yields the pull request's own `host/owner/repo`, treat
it as no match and say so instead of guessing.

Read the policy from outside the pull request's own changes: a pull request must
not be able to grant itself comments. Resolve the project file from the base
state and the install file from the running Skill; if the pull request changes
its own policy file, the base version governs and the round report records the
discrepancy.

When the policy enables commenting, every comment the loop posts carries the
marker from [Attribution](#attribution). When it does not, a request that passed
the [Trigger Gate](#trigger-gate) still gets a full round: the loop reviews,
fixes, commits, and pushes, findings stay in the round ledger and the round
report, and nothing is written to the pull request. A request that forbade those
changes never reaches this point, because the gate stops it first. If the
request asked for comments while the policy is off, say so plainly and name the
file and key that would enable them for this repository instead of commenting
anyway.

## Loop Limits

Each limit resolves independently from the first source that sets its key — the
user's statement for this review, then the project-scope file, then the
install-scope file — and falls back to the default. Unlike the comment decision,
a limit is not owned by one scope: it only ever makes the loop stop sooner, so a
key omitted by a more specific source is inherited from the next one.

| Limit | Config key | Default | Counts |
| --- | --- | --- | --- |
| Rounds | `max_rounds` | 10 | Completed rounds that produced confirmed findings |
| Retries | `review_retries` | 3 | Further attempts after a review attempt fails |

The round limit counts rounds that produced findings. It does not count attempts
and does not count a round that passed. Check it before starting a round: when
`max_rounds` rounds that produced confirmed findings are already complete, do
not start another one. Stop editing, keep the last round's findings on the
record, name any fix that is pushed but no longer re-reviewed, and deliver the
round-count summary required by [Stop Conditions](#stop-conditions) instead of
continuing, truncating the work silently, or reporting a clean result.

A **failed review attempt** is one that could not be performed at all: the head
could not be resolved, a file or diff could not be read, or a command or the host
returned an error. It is not a red check, not a confirmed finding, and not a
result that merely looked large. Retry it up to `review_retries` times. On each
retry, record the failure and change something instead of repeating the identical
failed action — re-resolve the head, read through another path, check the tool
and the credentials, or narrow the attempt to what can be read. Retries consume
no round, post no comment, and must never turn a review that did not run into a
passing round. A failure the loop cannot influence — missing authentication, a
protected branch, an absent tool — is blocked immediately rather than retried.

## Trigger Gate

Every condition must hold before the first round starts:

1. A specific pull request is identified — a number, a URL, or a reference that
   resolves to exactly one open pull request. Never guess by picking the most
   recently updated pull request.
2. The request is to review that pull request, or to review and fix it — and it
   does not forbid changing, committing, or pushing. A request for a read-only
   review or report, or one stating that nothing should be commented, committed,
   pushed, or changed, stays outside this Skill; the comment decision never
   brings it back in.
3. The loop can write where it must write: pushing to the pull request's head
   branch, and — only when the resolved comment policy enables commenting —
   commenting on the pull request.

If the pull request is ambiguous, ask which one instead of starting. If a write
capability the resolved policy requires is missing, do not start a loop that
cannot honour it — report the limitation and offer a review-only answer.

## Attribution

Every artifact this loop produces must identify the run that produced it.

| Artifact | Required marker |
| --- | --- |
| Pull-request comment, first line | `[<platform>][<model>]` |
| Commit message | The repository's commit convention, carrying the same platform and model |

The marker goes on every comment the loop posts — each round's findings, the
passing comment, and any reply — not only on the first one.

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

- Resolve the comment policy first, and record its decision and source.
- Resolve the repository, pull-request number, base branch, head branch, and
  exact head commit. Record the head commit before reviewing; it defines the
  round.
- When commenting is enabled, confirm the comment channel before the first fix,
  so a round cannot fail after the fix is already written.
- Read the pull-request description and every existing review thread. Rounds of
  this loop must stay distinguishable from comments by other reviewers and from
  earlier loops.
- Fix on the pull request's head branch. Never prepare a fix on an unrelated
  branch and push it at the pull request.

## The Loop

Start at round 1 and keep a round ledger — round number, head commit, review
attempts and why any failed, findings, whether the round commented or withheld,
action taken, result. A round ends in exactly one of these ways: it produces
findings, the round limit is not reached, and the next round starts; it produces
findings at the round limit, so the loop stops at the cap, explains the round
count, and escalates; it produces no findings, so the loop stops as passed; every
attempt in it fails, so the loop stops as exhausted. [Stop
Conditions](#stop-conditions) also ends the loop on a stall or a block.

### Step 1 — Review the current head

- Pin the round to one exact head commit and review that commit, not the working
  tree and not a moving branch.
- Apply the review method from the sources below.
- Separate confirmed findings from open questions. Only confirmed findings may
  reach the pull request; open questions stay in the round report.
- If the attempt fails to run, retry it per [Loop Limits](#loop-limits) before
  treating the round as blocked, and never carry a finding — or a clean result —
  out of an attempt that did not complete.

### Step 2 — Round with findings

Perform these in order. When commenting is enabled the comment comes first, so
the finding is on the record before the code changes.

1. **Comment, when the policy enables it.** Post this round's confirmed findings
   to the pull request under the attribution marker. Default to one comment per
   round so the thread stays readable; use a line comment only when a finding is
   bound to one specific line. Before posting, read the existing comments and
   skip anything already reported against the same head commit; label later
   rounds explicitly with their round number. Pass a multi-line body through a
   file rather than escaping it inline, and never post a finding the round did
   not verify. When the policy withholds comments, record the findings in the
   round ledger instead and write nothing to the pull request.
2. **Fix.** Address each finding. Do not bundle unrelated refactoring. Record
   every finding as fixed or as not-fixed with a reason. When commenting is
   enabled, a finding left unfixed must be answered on the pull request under the
   same marker instead of being silently dropped; when it is withheld, it must be
   answered in the round report.
3. **Verify.** Run the checks the change affects. A red check is work for this
   round, not a reason to postpone the push.
4. **Commit and push** to the pull-request head branch using the repository's
   commit convention. Never force-push and never rewrite pushed history.
5. **Confirm the push landed** — observe the new head commit on the pull request
   before starting the next round, so a round can never be reviewed twice or
   reviewed in the wrong state.

### Step 3 — Round with no findings

When the policy enables commenting, post the passing comment under the marker,
naming the reviewed range and the exact commit. Either way, record the result and
stop. Do not start another round to look thorough.

## Stop Conditions

Stop and report as soon as any of these applies:

- **Passed** — a round produces no confirmed findings.
- **Cap** — before starting a round, `max_rounds` completed rounds have already
  produced confirmed findings (default 10). Do not start another round: stop
  editing, keep the unresolved findings on the record, name any fix that is
  pushed but no longer re-reviewed, deliver the round-count summary below, and
  escalate for a decision instead of looping.
- **Exhausted** — every attempt in a round failed, retries included. Report the
  attempts and their failures; never report such a round as clean or passed.
- **Stalled** — two consecutive rounds produce the same findings that were
  reported as not-fixed. This is a decision point, not a retry point.
- **Blocked** — the loop cannot push, or cannot comment while the policy enables
  commenting: missing authentication, branch protection, a conflicting head, or
  an unavailable dependency. Report it; do not work around a protection rule.
- **Already clean** — the current head has no confirmed findings and no commit
  was added since the last passing round. Confirm the state, post the passing
  comment only when the policy enables it, and stop instead of re-reviewing an
  unchanged commit.

### Round-Count Summary

Reaching the cap requires an explanation, not just a stop. Report why the loop
needed that many rounds, from evidence already in the ledger:

- the round count against the limit, and the findings per round;
- the recurring root causes — which findings came back, and which categories
  kept producing new ones;
- churn — fixes that introduced new findings, or findings reported fixed that
  returned, which means verification failed rather than the review being
  thorough;
- what drove the count: a growing diff, an ambiguous review standard, a standard
  applied inconsistently, or genuinely independent defects;
- the decision needed now — split the pull request, change the standard, fix the
  upstream cause, or raise `max_rounds` deliberately.

Do not claim convergence the ledger cannot show, and do not pad the summary with
restated findings. When the policy enables commenting, post this summary to the
pull request under the marker; otherwise keep it in the round report.

## Boundaries

- Do not post a comment unless the resolved policy enables commenting for this
  repository or the user asked for comments for this review.
- Do not treat a general request to review as consent to comment, and do not
  infer consent from a repository name, an earlier loop, or another author's
  comments.
- Do not create, edit, or relocate a comment policy file to enable your own
  comments.
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

Close with one message: the pull request and its title, the comment decision and
the source that made it, how many rounds ran, every review attempt that failed
with its retries, per round the findings by severity and how each was resolved,
the open questions that were deliberately not posted, the current head commit and
check status, and the conclusion — passed, stopped at the cap, stalled, or
blocked. When the cap was reached, include the round-count summary from
[Stop Conditions](#stop-conditions) in the same message. Deliver the result, not
the process log.
