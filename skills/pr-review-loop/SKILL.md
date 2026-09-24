---
name: pr-review-loop
description: Review a specific pull request. Run the fix, commit, push, and re-review loop when the authenticated account is the pull-request author and either a project-scoped policy or Skill applies or a machine-wide policy lists the pull-request repository. The independent comment switch controls PR comments; max_rounds controls review cycles, with zero allowing one read-only review. Every posted comment carries the platform and model marker. The fix loop has review-cycle and retry limits. Use for requests to review a named pull request or continue its review. Do not use for a local-only report, a request forbidding both comments and code changes, or pull-request administration.
metadata:
  sync_id: "pr-review-loop"
  version: "0.2.0"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/pr-review-loop
  triggering:
    include:
      - "Review a specific pull request identified by number, link, or unambiguous reference; select loop or single-review mode from the authenticated account, pull-request author, project scope, machine-wide targets, and max_rounds."
      - "Review and fix a pull request, or keep reviewing it after each fix, when the same-account and project-scope or machine-wide target conditions permit the loop."
      - "Review a pull request without changing code and post confirmed findings only when the independent comment policy enables comments for that repository or the user requests comments for this review."
      - "Resume an unfinished review loop on a pull request whose head has moved since the last round."
    exclude:
      - "No pull request is identified: reviewing a local diff, branch, file, or snippet that only needs an answer in the conversation."
      - "The user wants only a local or in-conversation report, or forbids both pull-request comments and code changes."
      - "Pull-request administration without review: creating, editing, retitling, labeling, approving, closing, or merging a pull request."
      - "Resolving conflicts, rebasing, or repairing a broken worktree when no review was requested."
      - "Authoring or changing the standards that code review should apply."
---

# PR Review Loop

## Scope

This Skill selects a review mode, runs the configured number of review cycles,
and independently decides whether to post PR comments. `comment` never enables
fixing or changes `max_rounds`; `max_rounds` never enables commenting. The
review method — passes, matrices, severity, and completion criteria — comes
from [Where The Review Method Comes From](#where-the-review-method-comes-from).
Never manufacture findings to keep the loop running.

## Comment Policy

Commenting is **off by default**. Resolve the selected project Skill and policy
before the first review, and record the source of each decision:

1. **This review** — the user explicitly enables or disables PR comments for this
   review. This choice controls comments only and cannot enter a loop excluded
   by the [Trigger Gate](#trigger-gate).
2. **Project policy** — when this project has a project-owned copy with
   `metadata.sync_id: pr-review-loop`, put `pr-review-loop.yml` beside that
   copy's `SKILL.md`. In this repository the path is
   `<project-root>/skills/pr-review-loop/pr-review-loop.yml`. Create it as a
   local file and add that exact path to the project's `.gitignore` by
   default. A user may remove that ignore rule to commit a shared project
   policy. Read a tracked policy only from the PR base; use an untracked local
   policy only if it was present before the review began. Never use a symlink
   or a policy introduced or changed by the PR head to authorize its own
   review. For existing projects, a committed
   `<project-root>/.pr-review-loop.yml` in the PR base remains a fallback when
   the Skill-adjacent file is absent. The selected project file decides
   comments for this repository; a missing `comment` key means off and never
   inherits an install-level comment grant.
3. **Selected Skill install** — use the host's discovery and
   `metadata.sync_id: pr-review-loop` to select a project-scoped copy for this
   Agent platform before a machine-wide copy. When no project policy decides
   comments, read only the selected copy's
   adjacent `pr-review-loop.yml`; a project copy without that file does not
   inherit a machine-wide policy. Only if no project copy exists, select the
   machine-wide copy, reading its adjacent file first, then
   `$XDG_STATE_HOME/skill/pr-review-loop.yml` (or
   `$HOME/.local/state/skill/pr-review-loop.yml` when unset) if the adjacent
   file is absent. Name the selected copy and file.
4. **Default** — no PR comment.

In the selected source, only an effective `comment: true` enables comments;
`false` or an omitted key disables them. A project policy or project-scoped
Skill applies to its own project without a target list. A machine-wide policy
must match the PR repository through `projects` or the legacy
`comment_targets` list before it can enable comments or a fix loop. A matching
project entry may set `comment: false` and still permit the fix loop. An
explicit request to comment for this review may enable comments on an unlisted
repository, but does not make it eligible for a fix loop. An explicit request
not to comment always wins. A request merely to review is not a request to
comment.

Project and legacy install policies use these keys:

```yaml
comment: false
max_rounds: 10
review_retries: 3
# Include this key only in a machine-wide policy:
comment_targets:
  - https://github.com/<owner>/<repo>.git
```

For a machine-wide Skill, prefer a `projects` mapping keyed by repository.
Each entry may set `comment`, `max_rounds`, and `review_retries` independently.
For each omitted key, use that key in `defaults`, then the legacy top-level
value, then the built-in default (`comment: false`, `max_rounds: 10`, or
`review_retries: 3`). A `projects` entry is itself a loop target even when
`comment` is false. A legacy `comment_targets` entry remains a loop target;
when both match, the `projects` entry supplies any keys it sets. An unmatched
repository gets neither a fix loop nor policy-enabled comments. Do not combine two normalized
`projects` keys for the same repository; report the ambiguity and use one
read-only review without policy-enabled comments or fixes.

```yaml
defaults:
  comment: false
  max_rounds: 10
  review_retries: 3
projects:
  github.com/example/project-a:
    comment: true
    max_rounds: 3
    # review_retries inherits defaults.review_retries: 3
  github.com/example/project-b:
    review_retries: 2
    # comment and max_rounds inherit false and 10 from defaults
```

Require `projects` and `defaults` to be mappings, each project's values to be
a mapping, and every supplied `comment` to be a boolean. Require non-negative integer limits
for every level; invalid or ambiguous policy cannot authorize a write. Match
machine-wide project keys and legacy targets against the PR's own
`host/owner/repo`, not a fork remote. Normalize both sides: drop the scheme
and any `user@`, rewrite
`git@host:owner/repo` as `host/owner/repo`, remove a trailing `/` or `.git`,
and compare case-insensitively. If no remote resolves to the PR repository,
treat the target as unmatched and explain why. Machine-wide defaults or legacy
`comment: true` without a matching project or target never grant comments.

Check the project policy's tracked-file state before using it. A tracked
policy is shared project configuration and must come from the PR base; an
untracked policy is local configuration. Never copy either form into a general
Agent build or another Skill copy. Read the legacy root policy only from the
PR base so the PR cannot grant itself a new policy. Recognize a project Skill
only if the host discovered it before this PR's head changes, either in the
base state or as a pre-existing project
installation. Never let the PR introduce or replace the Skill or policy that
governs its own review. If project copies with the same `sync_id` are ambiguous
or unverifiable, do not guess their install policy or loop eligibility; report
the ambiguity and use only a separately verified base project policy or
machine-wide policy. If the PR changes its policy file, the base version still
governs this review; record the discrepancy.

When enabled, every posted comment has the marker from [Attribution](#attribution).
When disabled, retain findings and resolutions in the round ledger and report
them in the conversation. Fixing and reviewing continue under their own rules,
regardless of the comment decision.

## Select The Review Mode

Compare the authenticated hosting account with the PR author on the same host.
Use host account identities, not `git config user.name` or a commit author. If
either identity is unknown, do not assume a match. This account check governs
who may push fixes; it is independent of the comment switch.

The PR is eligible for a fix loop when either (a) a trusted Skill-adjacent
project policy or legacy base policy exists, or a pre-existing project-scoped
Skill is selected for this Agent platform, or (b) the selected machine-wide
policy's `projects` or legacy `comment_targets` matches the PR's own
repository under the rule above. Project scope needs no
`comment_targets`. An explicit request to comment does not create loop
eligibility. A request to fix cannot override an account mismatch or missing
machine-wide target or project entry.

| Condition | Mode |
| --- | --- |
| Author account matches, project scope applies or a machine-wide project entry or legacy target matches, `max_rounds` is positive, and the user permits code changes | Review and fix for at most `max_rounds` completed review cycles; comment only if independently enabled |
| Account differs or is unknown, scope does not qualify, `max_rounds` is zero, or the user requests no code changes | Review one base/head pair and report findings; post to the PR only if independently enabled; never edit, commit, or push |

A request for only a local report remains outside this Skill. State the selected
mode and evidence before the first review.

## Loop Limits

Resolve each limit independently from the first source setting its key: this
review's user instruction, the trusted Skill-adjacent project policy, the
legacy base project policy when no Skill-adjacent policy exists, the selected
Skill install
policy's matching `projects` entry, its `defaults`, its legacy top-level keys,
then the built-in default. Do not inherit a machine-wide policy from an existing
project Skill with no adjacent file. Limits do not confer comment permission.
Require `max_rounds` and `review_retries` to be non-negative integers; a
missing or invalid value never implies an unlimited loop. Report invalid input
before attempting a fix and use one read-only review if it can be performed.

| Limit | Config key | Default | Counts |
| --- | --- | --- | --- |
| Review cycles | `max_rounds` | 10 | Completed reviews, including a passing review |
| Retries | `review_retries` | 3 | Further attempts after a review attempt fails to run |

`max_rounds: 0` performs one read-only review and no fix cycle. A positive
value is the total number of review cycles allowed: `1` permits one review and
its fix, but no review of the resulting head; `10` permits at most ten reviews,
regardless of whether comments are posted. Check the limit before starting
another review. Stop after a passing review, an unfixable finding, or the final
allowed review and any verified fix. When the final fix is pushed, identify it
as not yet re-reviewed; never call it passed. Count a review with findings as
one cycle even if no fix is possible. A failed attempt consumes no cycle.

A **failed review attempt** is one that could not be performed at all: the base
or head could not be resolved, a file or diff could not be read, or a command or
the host returned an error. A red check or confirmed finding is not an attempt
failure. Retry up to `review_retries` further times, recording what failed and
changing the approach each time. Retries post no comments and cannot turn an
incomplete review into a passing one. Missing authentication, protection rules,
or unavailable required tools block immediately when the loop cannot influence
them.

## Trigger Gate

Every condition must hold before reviewing:

1. A specific pull request is identified — a number, a URL, or a reference that
   resolves to exactly one open pull request. Never guess by picking the most
   recently updated pull request.
2. The request is to review that pull request. A request for only a local or
   in-conversation report, or one that forbids both comments and code changes,
   stays outside this Skill. A request forbidding code changes but allowing
   comments can use single-review mode.
3. The selected mode has its required capabilities: fix-loop mode needs push
   access to the pull request's head branch; either mode needs comment access
   only when the resolved comment policy enables commenting.

If the pull request is ambiguous, ask which one instead of starting. If a write
capability the selected mode requires is missing, do not start work that cannot
honour it — report the limitation and offer an answer in the conversation.

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

- Resolve the repository, PR number, base branch and exact base commit, head
  branch and exact head commit. Pin each review to that base/head pair.
- Resolve and record separately: authenticated account and PR author, project
  or machine-wide scope, target eligibility where required, `max_rounds`, the
  comment decision, and the source of each value.
- When commenting is enabled, confirm comment access before reviewing or
  fixing, so a review cannot fail after a fix is written.
- Read the PR description and existing review threads, distinguishing earlier
  loops and other reviewers' comments from this run.
- For a fix loop, work on the PR's head branch. Never push an unrelated branch
  at the PR.

## The Loop

In single-review mode, review one pinned base/head pair, report confirmed
findings or a pass, and stop. Post to the PR only if commenting is enabled.
Never edit, commit, or push in this mode, including when `max_rounds` is zero.

In fix-loop mode, keep a ledger of cycle number, base/head commits, review
attempts, criteria and standards applied, findings, comment decision, fixed and
unfixed dispositions, checks, push result, and stop reason. Count each completed
review, even a clean one. Start another cycle only when a new head exists and
the count is below `max_rounds`. A clean review, unfixable finding, exhausted
attempts, block, or cap ends the loop.

### Step 1 — Review the current base/head pair

This step applies to both modes.

- Pin the exact base and head commits; review that pair rather than the working
  tree or a moving branch. Record the method and criteria used.
- Check the user's criteria for this review first, followed by applicable
  repository and project standards. Separate confirmed findings from open
  questions; only confirmed findings may reach a PR comment.
- If the attempt cannot run, retry as described in [Loop Limits](#loop-limits).
  Do not treat an incomplete attempt as a completed cycle or a clean result.
- Before posting any finding or pass, or before fixing, confirm that the PR
  still has the pinned base/head pair. If either changed, resolve the new pair and review it before claiming
  the result applies to the current PR. Do not push onto a conflicting head.

### Step 2 — Round with findings

Fix-loop mode only. In this order:

1. **Comment, when enabled.** Post confirmed findings under the attribution
   marker. Prefer one comment per cycle. Before posting, read the existing
   comments and skip a duplicate finding for the same base/head pair. Use a
   line comment only for a line-specific finding. When disabled, record the
   findings in the ledger without posting anything.
2. **Fix what can be fixed.** Record each finding as fixed or not-fixed with a
   reason. If any finding cannot be fixed, complete the safe fixes that can be
   made in this cycle, then stop after their verification and push. Do not open
   another review cycle with known unfixable findings. Report every unresolved
   finding, replying on the PR under the marker only when commenting is enabled.
3. **Verify.** Run checks affected by the fixes. Resolve failed checks before
   pushing. If verification cannot pass, stop as blocked and report the state;
   do not claim a fix was delivered.
4. **Commit and push only when there is a verified change.** Use the repository's
   commit convention, do not force-push, and confirm the new head landed on the
   PR. If nothing could be changed, do not manufacture an empty commit or push;
   stop and report the unresolved findings. If a push is blocked, preserve the
   local change and report its location and status.
5. **Choose the next transition.** If any finding is not-fixed, stop as
   partially fixed or unfixable and report it. Otherwise, if the cycle count
   equals `max_rounds`, stop at the cap and identify the pushed head as not yet
   re-reviewed. If cycles remain, review the new base/head pair.

### Step 3 — Round with no findings

Record a passing result for the exact base/head pair and the criteria and
standards checked. Post a passing comment only when enabled. Stop without
starting another cycle.

## Stop Conditions

Stop and report as soon as one applies:

- **Passed** — a completed review finds no confirmed issues for its pinned
  base/head pair and recorded review scope.
- **Single review** — read-only mode ends after one completed review, with
  findings or a pass; `max_rounds: 0` never enters a fix cycle.
- **Partially fixed / unfixable** — one or more confirmed findings cannot be
  fixed. Verify and push only the fixes that can be made, then stop, listing
  what remains and what was changed. With no verified change, stop without a
  commit or push.
- **Cap** — the configured number of completed reviews was reached. A passing
  final review is Passed; after a final finding round, report remaining issues
  and any pushed fix that was not re-reviewed. Do not claim convergence.
- **Exhausted** — every attempt in a cycle failed, retries included. Report
  attempts and errors; never treat the cycle as clean.
- **Blocked** — required push or enabled comment access fails, the PR base/head
  conflicts, or a required dependency is unavailable. Report the state and do
  not bypass protection rules.
- **Already clean** — reuse an earlier passing result only if the PR base and
  head commits, the user's requested criteria and scope, the applicable review
  standards, and the evidence that those checks completed are all unchanged.
  If any is changed or unknown, perform a new review. A reused pass must never
  imply that new criteria were checked.

### Cycle-Count Summary

At the cap, state the cycle count against `max_rounds`, findings and fixes per
cycle, recurring causes, and any pushed head without a fresh review. Explain
what would need another cycle. Post this summary to the PR only if commenting
is enabled; otherwise include it in the conversation report.

## Boundaries

- Do not post a comment unless the resolved policy enables commenting for this
  repository or the user asked for comments for this review.
- In single-review mode, do not edit files, commit, or push, even if the request
  asked for fixes; explain why the fix-loop conditions were not met.
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
combine applicable sources in this order:

1. **This review's user request** — check every criterion the user stated for
   this pull request first, and honor an explicit focus or scope limit. A general
   repository standard must not hide a check the user specifically requested.
2. **Repository review standard** — apply its required playbook, contribution
   guide, or repository instructions to the remaining applicable coverage.
3. **Project documentation** — apply relevant review, testing, and release
   expectations not already covered.
4. **Host code-review capability** — fill gaps when the preceding sources leave
   a check unspecified.

Use the instruction priority that governs the run when sources conflict. State
the conflict, what was checked or skipped, and why; do not silently replace the
user's requested check with a general checklist. Record every source used and
the user-specific checks completed in the round report. If no source is found,
say so plainly instead of silently reviewing with no standard.

## Round Report

Close with one message: the pull request and its title, the selected mode and its
account/scope evidence, `max_rounds`, the independent comment decision and its
source, completed review count, failed attempts and retries, per-cycle base/head
pair and method sources, user-specific checks, findings and dispositions, checks
and pushed fixes, open questions, current PR base/head and check status, and the
conclusion — passed, single-review findings, partially fixed, unfixable, cap,
exhausted, or blocked. Identify any pushed fix not yet re-reviewed and include
the cycle-count summary at the cap. Deliver the result, not the process log.
