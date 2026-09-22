# PR Review Loop

Language: **English** | [中文](README.zh-CN.md)

`pr-review-loop` runs a pull-request review loop: it reviews the current head, fixes the confirmed findings, commits and pushes the fix, and reviews again until a round reports no confirmed findings. It defines the loop — attribution, round order, the comment decision, stop conditions, and reporting — and deliberately does not define what a review must check.

## How To Use It

Point at one pull request and say what you want:

```text
Review PR #25 and fix what you find until it is clean.
Review https://github.com/<owner>/<repo>/pull/42, post the problems to the PR, then fix them.
Continue the review loop on this PR after the last fix.
```

Provide the pull request by number or link, and the repository if it is not the
current checkout. The loop resolves the exact head commit, reviews it, fixes and
pushes the findings, and repeats until a round is clean or a stop condition
applies.

## Comment Policy

**Commenting is off by default.** The loop writes findings to the pull request
only when a policy source enables it for that repository, so a machine-wide
install never comments on repositories you did not list. Naming a pull request
and asking for a review is not consent to comment; asking for comments for this
review is.

The policy is resolved from the first decisive source:

1. **This review** — you state, for this review, whether to comment.
2. **Project scope** — `<project-root>/.pr-review-loop/comment-targets.yml`.
3. **Install scope** — `comment-targets.yml` in the running Skill's directory,
   or `$XDG_STATE_HOME/skill/pr-review-loop/comment-targets.yml`
   (`$HOME/.local/state/...` when `XDG_STATE_HOME` is unset).
4. **Default** — no comment.

Both scopes use the same file name and the same keys:

```yaml
comment: false
comment_targets:
  - https://github.com/wk1995/skill.git
```

A remote that matches `comment_targets` gets comments; otherwise `comment`
decides that scope; otherwise the next source applies. Remotes are compared as
`host/owner/repo`, case-insensitively, ignoring the scheme, any `user@`, a
trailing slash, and a trailing `.git`. See
[assets/comment-targets.example.yml](assets/comment-targets.example.yml) for a
commented template.

To receive comments for one repository only, list its remote in the install
scope file. To turn commenting on or off for a project, commit the project scope
file with `comment: true` or `comment: false`.

Every comment the loop posts starts with `[<platform>][<model>]` — the agent
platform running the loop plus the detailed model name in use — and commits
follow the repository's commit convention with the same identity. See
[SKILL.md](SKILL.md) for the full loop contract, stop conditions, and
boundaries.

## When It Triggers

- A specific pull request is named and the user asks to review it.
- The user asks to review and fix a pull request, or to post findings as pull-request comments and then fix them.
- The user asks to keep reviewing a pull request until no problem is found, or to resume an unfinished review loop.

## When It Does Not Trigger

- No pull request is identified: reviewing a local diff, branch, file, or snippet that only needs an answer in the conversation.
- The user asks for a read-only review or a report and states that nothing should be commented on, committed, or changed.
- The request is pull-request administration rather than review: creating, editing, retitling, labeling, approving, closing, or merging.
- The task is resolving conflicts, rebasing, or repairing a worktree without a review request.
- The user wants to author or change the standards that review should apply.

When the request is review-only, use the repository's own review standard instead
of this loop; this Skill stops at the boundary of the loop and never decides what
a review must inspect.
