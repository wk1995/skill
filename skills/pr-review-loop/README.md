# PR Review Loop

Language: **English** | [中文](README.zh-CN.md)

`pr-review-loop` reviews a named pull request and selects a mode before it starts. When the account that would comment is the pull-request author and the applicable configuration lists that repository address, it fixes confirmed findings, commits, pushes, and reviews again by default. Otherwise it reviews one head without changing code and comments only if the comment policy permits it; with commenting off, it reports in the conversation. It defines attribution, mode selection, round order, limits, stop conditions, and reporting, but not what a review must check.

## How To Use It

Point at one pull request and say what you want:

```text
Review PR #25.
Review https://github.com/<owner>/<repo>/pull/42 and fix what you find if the full loop is enabled.
Continue the review loop on this PR after the last fix.
```

Provide the pull request by number or link, and the repository if it is not the
current checkout. The Skill resolves the exact head commit and the review mode.
The full loop repeats after each pushed fix until a round is clean or a stop
condition applies; comment-only mode reviews one head and stops.

## Comment Policy

**Commenting is off by default.** The loop writes findings to the pull request
only when a policy source enables it for that repository, so a machine-wide
install does not comment on an unlisted repository without an explicit request
for this review. Naming a pull request and asking for a review is not consent to
comment; asking for comments for this review is.

The policy is resolved from the first source that exists, and only an explicit
enable turns commenting on:

1. **This review** — you state, for this review, whether to comment. This is the
   only source that can enable commenting for a repository no configuration
   lists.
2. **Project scope** — `<project-root>/.pr-review-loop.yml`. A repository that
   has this file is decided by it, so the install scope is never read for that
   repository.
3. **Selected Skill install** — use the host's Skill discovery and
   `metadata.sync_id: pr-review-loop` to identify a project-scoped copy for this
   agent platform. It takes priority over a machine-wide copy. Read
   `pr-review-loop.yml` beside the selected project Skill; if absent, do not
   read the machine-wide copy. Only when no project Skill exists, select the
   machine-wide copy: read its adjacent file first, then
   `$XDG_STATE_HOME/skill/pr-review-loop.yml` (`$HOME/.local/state/...` when
   unset) if the adjacent file is absent. Used for comments only when no
   project-scope file exists. A PR cannot add its own project Skill or policy to
   change this choice for its review.
4. **Default** — no comment.

The two scopes use different file names and the same keys, and the same file
also carries the limits from [Loop Limits](#loop-limits):

```yaml
comment: false
comment_targets:
  - https://github.com/<owner>/<repo>.git
max_rounds: 10
review_retries: 3
```

A remote that matches `comment_targets` gets comments and can qualify for the
full loop; otherwise `comment: true` enables comments only; otherwise commenting
stays off. Remotes are compared as `host/owner/repo`,
case-insensitively, ignoring the scheme, any `user@`, a trailing slash, and a
trailing `.git`, and a repository must publish the remote that equals the pull
request's own `host/owner/repo` — a fork's remote never matches. See
[assets/pr-review-loop.example.yml](assets/pr-review-loop.example.yml) for a
commented template.

To receive comments across the repositories a selected install serves, list
their remotes in its policy file. A project Skill takes priority over the
machine-wide install even without a policy file; it does not inherit the
machine-wide policy. To turn commenting on or off for one project, commit its
project scope file with `comment: true` or `comment: false` — committing that
file for the round limit alone leaves commenting off for the repository.

Every comment the loop posts starts with `[<platform>][<model>]` — the agent
platform running the loop plus the detailed model name in use — and commits
follow the repository's commit convention with the same identity. See
[SKILL.md](SKILL.md) for the full loop contract, stop conditions, and
boundaries.

## Review Modes

The Skill compares the authenticated account that would comment with the pull
request's author, using the hosting service's account identity rather than a Git
commit name. For the address check, it reads the project-scope file from the
pull request's base state if present; otherwise it reads the selected Skill
install's policy file. The address is configured only when `comment_targets` in
that selected file explicitly matches the pull request's own repository remote.
`comment: true` or a request to comment can enable comments, but cannot by itself
enable the full loop.

| Situation | Result |
| --- | --- |
| Same commenting account as pull-request author, repository address configured, and no request to avoid code changes | Full review loop by default: comment if enabled, fix, verify, commit, push, and review again |
| Different or unknown account, address not configured, or review requested without code changes | Review one head without edits, commits, or pushes; comment if enabled, otherwise report in the conversation |

Even an explicit request to fix does not bypass an account or address mismatch;
the report explains why only a single review ran. A request to avoid comments
and code changes entirely stays outside this Skill.

## Loop Limits

The full loop stops at a round limit instead of running forever, and retries a review
that fails to run:

| Limit | Config key | Default | Counts |
| --- | --- | --- | --- |
| Rounds | `max_rounds` | 10 | Completed rounds that produced confirmed findings |
| Retries | `review_retries` | 3 | Further attempts after a review attempt fails |

Only rounds that produced findings count toward `max_rounds`; a round that passed
and an attempt that failed do not. The limit is checked before a round starts, so
once ten rounds have produced findings the loop does not start an eleventh: it
stops editing, names any fix that is pushed but no longer re-reviewed, delivers a
round-count summary — the round count against the limit, the findings per round,
the recurring root causes, and the decision needed now — and escalates instead of
looping. A review that could not be performed at all is retried up to
`review_retries` times, each retry changing the approach and recording the
failure; retries consume no round, post no comment, and never turn a review that
did not run into a passing round. Each limit can be stated for a single review or
set in the project-scope file or selected Skill install's policy file; unlike the
comment decision, a limit omitted by the project file is inherited from the
selected install. A project Skill never inherits a machine-wide limit.
See [SKILL.md](SKILL.md) for the full rules.

## When It Triggers

- A specific pull request is named and the user asks to review it; the account and configured address select the mode.
- The user asks to review and fix a pull request or to keep reviewing after each fix; the full loop runs only when its account and address conditions are met.
- The user asks for a review without code changes but permits pull-request comments; the single-review mode comments only when the policy enables it.

## When It Does Not Trigger

- No pull request is identified: reviewing a local diff, branch, file, or snippet that only needs an answer in the conversation.
- The user asks only for a local or in-conversation report, or forbids both pull-request comments and code changes.
- The request is pull-request administration rather than review: creating, editing, retitling, labeling, approving, closing, or merging.
- The task is resolving conflicts, rebasing, or repairing a worktree without a review request.
- The user wants to author or change the standards that review should apply.

For a local-only request, use the repository's own review standard instead of
this Skill. The Skill never decides what a review must inspect.
