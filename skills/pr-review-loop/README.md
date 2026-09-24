# PR Review Loop

Language: **English** | [中文](README.zh-CN.md)

`pr-review-loop` reviews a named pull request. An authenticated PR author can
review, fix, push, and repeat when a project-scoped Skill or policy applies, or
a machine-wide policy lists that repository. `max_rounds` limits completed
reviews; the independent `comment` switch controls PR comments. The Skill
defines the workflow, not what a review must check.

## How To Use It

Name one pull request and any review focus:

```text
Review PR #25.
Review https://github.com/<owner>/<repo>/pull/42 and fix confirmed findings.
Review PR #25 for leaked tokens without changing code.
Continue the review loop on this PR.
```

A full loop reviews an exact base/head pair, fixes verified findings, pushes,
and reviews the new pair while cycles remain. The user's requested criteria are
checked first. Repository review standards and project documentation supply
other applicable checks. Conflicts and skipped checks are reported.

## Policy And Review Modes

The project policy is `<project-root>/.pr-review-loop.yml` from the PR base.
A project-scoped Skill discovered for the active Agent platform by
`metadata.sync_id: pr-review-loop` also applies to its own project. Neither
needs `comment_targets` for its own repository. A selected project Skill does
not inherit a machine-wide policy when its adjacent `pr-review-loop.yml` is
absent. When no project Skill exists, use the machine-wide copy and require its
`comment_targets` to list the PR repository for the fix loop.

Policy selection prefers a project policy file, then the selected Skill's
adjacent `pr-review-loop.yml`. Only a machine-wide Skill may use
`$XDG_STATE_HOME/skill/pr-review-loop.yml` (or
`$HOME/.local/state/skill/pr-review-loop.yml` when unset) if its adjacent file
is absent. The adjacent file wins when both exist. The PR cannot add its own
project Skill or policy for its review; the base or pre-existing installation
governs.

```yaml
comment: false
max_rounds: 10
review_retries: 3
# Machine-wide policy only:
comment_targets:
  - https://github.com/<owner>/<repo>.git
```

`comment: true` enables PR comments and `false` or an omitted key disables
them. `max_rounds` never changes this decision. The user's explicit comment
preference for this review takes priority. A project policy file decides its
repository's comment setting even if it omits the key, without inheriting an
install's grant. For a machine-wide Skill, `comment: true` applies only to a
repository in `comment_targets`; an explicit request to comment may permit an
unlisted repository, but does not enable its fix loop. A matching target alone
does not enable comments. See [the example](assets/pr-review-loop.example.yml).

Machine-wide targets are normalized to `host/owner/repo`, ignoring scheme,
`user@`, case, trailing slash, and `.git`. Only a remote identifying the PR's
own repository counts; a fork remote does not. If no such remote can be
verified, the target does not match.

Fixing also requires the authenticated hosting account to be the PR author,
positive `max_rounds`, push access, and no request to avoid code changes.
Unknown or different account, missing project or machine-wide eligibility,
`max_rounds: 0`, or a read-only request means one review with no edits, commits,
or pushes. Commenting in either mode depends only on its separate decision.
Every posted comment starts with `[<platform>][<model>]`; commits follow the
repository convention and identify the same platform and model.

## Review Cycles And Stopping

`max_rounds` counts completed reviews, including a clean review. Its default is
10. `0` means one read-only review and no fix loop; `1` permits one review and
its fix, but no review of the pushed head; `10` permits at most ten reviews.
The loop stops early on a clean review. When it reaches the limit after a fix,
it reports that the pushed head has not been re-reviewed. Failed attempts do
not count; `review_retries` defaults to three further attempts and does not
turn a failed attempt into a pass. Invalid limit values never start a fix loop.

If some findings cannot be fixed, the loop first completes and verifies the
fixable ones, pushes only when there is a verified change, then stops and
reports the unresolved findings. With no change, it stops without inventing an
empty commit. Comments are posted only when the independent policy enables
them; otherwise results remain in the conversation report.

An earlier passing result may be reused only when the PR base and head, this
review's criteria and scope, applicable standards, and evidence that the checks
ran are all unchanged. A new requested check or a changed base requires a new
review even when the head commit is unchanged. See [SKILL.md](SKILL.md) for the
full workflow and stop conditions.

## When It Triggers

- A specific PR is named and the user requests review.
- The user asks to review and fix, or continue reviewing after a fix, when the
  account, project or machine-wide target, and round limit permit the loop.
- The user requests a single review that may comment under the separate policy.

## When It Does Not Trigger

- No PR is identified; only a local diff, branch, file, or snippet needs review.
- The user wants only a local or in-conversation report, or forbids both PR
  comments and code changes.
- The task only administers a PR, such as creating, approving, or merging it.
- The task only resolves conflicts, rebases, repairs a worktree, or changes the
  review standard without requesting a PR review.
