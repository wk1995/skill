---
name: git-commit-message
description: Mandatory before every agent Git commit in any repository, including commit-and-push tasks, amend, message-file commits, and commits invoked through helpers. Check and normalize AI client/model attribution and optional machine/repository prefixes. Also use to configure policy or install its commit-msg hook; exclude read-only Git, staging alone, and push-only tasks.
metadata:
  sync_id: "git-commit-message"
  version: "1.0.1"
  triggering:
    include:
      - Before every agent-created Git commit in any repository, including amend, message-file commits, and helper-invoked commits.
      - A commit step within a larger task, such as fix then commit and push or deploy, even when the user does not name this Skill.
      - Install or configure automatic commit-message checks, machine prefixes, and repository-specific prefixes.
    exclude:
      - Git reads, staging without committing, branch management, and push-only requests.
      - Formatting pull-request comments, reviews, or release notes.
---

# Git Commit Message

## Commit boundary: every repository

Apply this Skill immediately before **each** agent-created commit, including a
commit step reached later in a larger coding, push, or deployment task. Do not
wait for the user to name the Skill. Recheck at the commit boundary even if the
initial task did not mention Git. This applies in new repositories and existing
clones, through shell commands or helper scripts, and on retries and amendments.

A missing repository policy means the documented defaults apply; a missing Git
hook means the agent must run the preflight itself. Neither is an exemption.
Reading this Skill or adding attribution by hand is not a completed check.
Execute the policy-aware preflight below before committing. Do not silently
continue if the script is unavailable or the preflight fails.

## Policy and identity

Before a commit, load machine prefixes from
`$XDG_CONFIG_HOME/git-commit-message/config.json` (default
`~/.config/git-commit-message/config.json`) and the target repository's
`.git-commit-message.json`, when present. Machine prefixes default to an empty
list and require repository `machine_prefix: true` to be used. Repository
`extra_prefixes` also default to an empty list; `repo_prefix: false` disables
them. `ai_prefix: false` disables attribution. When all three switches are
false, leave message bytes unchanged without requiring identity. There is no
global switch. Read [README.md](README.md) for configuration and commands.
The policy may be tracked for team sharing or kept untracked for local use;
both are read identically. Version control participation is optional.

Resolve the **current** client, its version, and model from trusted session
metadata or a verified host command. Supply these per invocation through
`AI_AGENT_CLIENT`, `AI_AGENT_CLIENT_VERSION`, and `AI_AGENT_MODEL`. Never infer a
client version from a CLI belonging to a different client, guess a model, reuse
an earlier session's identity, or persist identity in the shared repository
policy. Omit an unknown client or version; when attribution is enabled and the
model is unknown, resolve it with the user before committing.

The prefix is `[Client version][Model]`, `[Client][Model]`, or `[Model]`.
Enabled machine prefixes come first, followed by enabled repository
`extra_prefixes`, then the AI group. A shared machine/repository token appears
once, at its first position. Keep the meaningful subject and body;
do not replace existing project conventions with a different message style.

Keep machine settings outside repositories and Skill directories so this
device's marker is not distributed to other devices by Skill synchronization.
Do not enable machine prefixes in a repository unless the user requests it.
Both policy files are validated even when a prefix group is disabled.

For the requested automatic behavior, run `scripts/commit_message.py install`
against the selected repository. It installs a self-contained `commit-msg`
hook, which must be installed once in each clone. Installation is within scope
when the user asks to enable these checks. Never overwrite another hook or
change `core.hooksPath`: use the existing hook manager's integration point and
invoke this script's `hook` command instead. Report any integration still needed.

## Required preflight before each commit

1. Resolve the target repository, its policy, and the current session identity
   as above. Prepare the intended subject and body in a temporary message file;
   preserve requested amend, sign-off, and other commit semantics.
2. Supply the current identity in the environment and execute
   `python3 <skill-dir>/scripts/commit_message.py --repo <repository> hook <message-file>`.
   The `hook` subcommand also works without an installed Git hook and selects
   `fix` or `check` from repository policy. Run it even when a hook is installed;
   do not replace it with an unconditional `fix` in a check-only repository.
3. Only after exit status 0, commit that same file with `git commit -F`, supplying
   the same current identity in the commit command's environment. If a helper
   creates the commit, ensure it uses the checked message and identity; an
   unchecked helper commit does not satisfy this gate.
4. Remove the temporary file on success or failure. After a successful commit,
   inspect `git log -1 --format=%B` against the checked message and effective
   policy before pushing. Do not silently rewrite published history on mismatch.

This preflight does not install a persistent hook. Install or integrate one
only when automatic Git-level checks have been requested; keep the same
per-invocation identity requirement.

Configuration errors and missing required identity must stop before changing a
message or installing a hook. Do not bypass a failed check with `--no-verify`
or an alternate hooks directory. Autosquash messages are exempt by default to
preserve their target matching; see the guide for this configurable exception.
An installed hook also runs for manual commits and Git merge operations that
invoke `commit-msg`. Human callers must supply identity or select an appropriate
repository policy; do not label human work with a previous agent's identity.

This Skill formats messages; it does not authorize staging, committing,
amending, publishing, or changing repository identity. Follow the user's
existing authorization for those operations.
