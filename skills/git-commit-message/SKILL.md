---
name: git-commit-message
description: Check and normalize Git commit messages with AI client, optional client version, and model attribution, opt-in machine prefixes, and repository-specific prefixes. Use before executing git commit and when configuring machine or repository policy or installing its commit-msg hook; do not use for Git reads, staging alone, or PR comments.
metadata:
  sync_id: "git-commit-message"
  version: "0.1.0"
  triggering:
    include:
      - Before an agent executes git commit, including amend and message-file commits.
      - Install or configure automatic commit-message checks, machine prefixes, and repository-specific prefixes.
    exclude:
      - Git reads, staging without committing, branch management, and push-only requests.
      - Formatting pull-request comments, reviews, or release notes.
---

# Git Commit Message

Before a commit, load machine prefixes from
`$XDG_CONFIG_HOME/git-commit-message/config.json` (default
`~/.config/git-commit-message/config.json`) and the target repository's
`.git-commit-message.json`, when present. Machine prefixes default to an empty
list and require repository `machine_prefix: true` to be used. Repository
`extra_prefixes` also default to an empty list; `repo_prefix: false` disables
them. `ai_prefix: false` disables attribution; `enabled: false` disables all
prefix requirements. Read [README.md](README.md) for configuration and commands.
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

Before each agent commit, supply the current identity in that command's
environment, even when a hook is already installed. If persistent installation
was not requested, prepare the message in a temporary file, run `fix` (or
`check` when repository mode is `check`), and pass that file to `git commit -F`.
Do not let a one-off `fix` override a repository's check-only policy. Remove the
temporary file afterward. Preserve explicitly requested commit semantics.

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
