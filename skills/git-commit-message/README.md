# Git Commit Message

Language: **English** | [简体中文](README.zh-CN.md)

Check and normalize Git commit messages with AI client, optional client version,
and model attribution, opt-in machine prefixes, and repository-specific prefixes.
Use before executing `git commit` and when configuring machine or repository
policy or installing its `commit-msg` hook; Git reads,
staging alone, and PR comments are outside its scope.

## How To Use It

Ask your agent: “Before committing, apply git-commit-message using this session's
client, version when known, and model.” Or: “Enable automatic commit-message
checks here; add the project prefix PROJ-42.” See [SKILL.md](SKILL.md) for the
agent workflow and safety boundaries.

The portable Skill provides instructions; installing it in a Skill directory
alone does **not** register a Git hook. Install the hook once in each clone for
automatic execution, including commits made from a terminal. Python 3.10+ and
Git 2.45+ must be available on `PATH` (macOS/Linux; native Windows is untested).
From the target worktree, set `tool` to the
absolute path of this Skill's `scripts/commit_message.py`:

```sh
python3 "$tool" install

# Example values only: use the actual current client and model.
AI_AGENT_CLIENT='Codex' AI_AGENT_CLIENT_VERSION='1.2.3' \
AI_AGENT_MODEL='example-model' git commit -m 'fix: repair login'
```

Results (one space separates client and version):

| Available identity | Subject |
| --- | --- |
| Client, version, model | `[Codex 1.2.3][example-model] fix: repair login` |
| Client and model | `[Codex][example-model] fix: repair login` |
| Model only | `[example-model] fix: repair login` |

Identity comes from these environment variables on **each invocation**. Unknown
client/version values are omitted, and a version without a client is ignored.
An enabled AI prefix requires `AI_AGENT_MODEL`; missing identity stops the
commit instead of guessing. No identity is saved by installation. Human commits
also encounter the installed policy: provide appropriate identity, configure
`ai_prefix: false`, or disable the policy. Never reuse stale agent identity.

### Machine Configuration

Create `$XDG_CONFIG_HOME/git-commit-message/config.json`, or
`~/.config/git-commit-message/config.json` when `XDG_CONFIG_HOME` is unset or
empty. A nonempty `XDG_CONFIG_HOME` must be absolute. The same file serves all
Agent clients on this device and is reloaded on every invocation:

```json
{"schema_version": 1, "extra_prefixes": ["work"]}
```

On another device, use `{"extra_prefixes": ["home"]}`. The machine file accepts
only `schema_version` and `extra_prefixes`; both are optional. Missing files
mean no machine prefixes. Keep it outside the repository and Skill directory;
it is not included in Skill synchronization.

**Machine prefixes are off by default**, even when this file exists. A
repository must opt in with `"machine_prefix": true`. Enabled groups appear
in this order: `[machine][repository][client version][model]`. Identical values
shared by the machine and repository groups appear once at the first position.

### Repository Configuration

Create `.git-commit-message.json` in the worktree root; it is reloaded on every
invocation, including from subdirectories and linked worktrees. Version control
is optional: commit it to share the policy with the team, or keep it untracked
for local use. Both work identically. For local use, add
`/.git-commit-message.json` to the local exclude file located by
`git rev-parse --git-path info/exclude`; a team may instead put that rule in
`.gitignore`. Ignore rules apply only to untracked files. The file contains
policy only, never per-session identity. No configuration means these defaults:

```json
{
  "schema_version": 1,
  "enabled": true,
  "machine_prefix": false,
  "repo_prefix": true,
  "ai_prefix": true,
  "extra_prefixes": [],
  "mode": "fix",
  "skip_autosquash": true
}
```

| Key | Meaning |
| --- | --- |
| `enabled` | `false` leaves messages unchanged and requires no identity. |
| `machine_prefix` | Default `false`; `true` adds this device's configured prefixes first. |
| `repo_prefix` | Default `true`; `false` suppresses the repository's `extra_prefixes`. |
| `ai_prefix` | `false` omits the AI client/model group and requires no identity. |
| `extra_prefixes` | Default `[]`; repository strings without brackets, after machine prefixes and before the AI group. |
| `mode` | `fix` automatically normalizes prefixes; `check` rejects noncanonical messages without changing them. |
| `skip_autosquash` | `true` exempts subjects beginning `fixup! `, `squash! `, or `amend! ` to preserve autosquash matching. |

All keys are optional. Unknown/duplicate keys, invalid types, duplicate prefix
values, brackets, control characters, or surrounding whitespace in tokens are
rejected. Both files are validated even when `enabled` or a group switch is
false. Neither file is modified by message checks or hook installation.

To combine this device's `work` marker with a shared project marker:

```json
{"machine_prefix": true, "extra_prefixes": ["PROJ-42"]}
```

Output: `[work][PROJ-42][Codex][example-model] fix: repair login`.
The same repository on the home device produces `[home][PROJ-42]...` instead.
Set `machine_prefix: false` to keep the project and AI groups only. Set
`repo_prefix: false` to suppress configured repository values without deleting
them. `ai_prefix` independently controls the AI group.

For extra project prefixes:

```json
{"extra_prefixes": ["PROJ-42", "backend"]}
```

Output: `[PROJ-42][backend][Codex 1.2.3][example-model] fix: repair login`.

For **only** a project prefix, without AI attribution:

```json
{"ai_prefix": false, "extra_prefixes": ["PROJ-42"]}
```

For no prefix requirements: `{"enabled": false}`. Alternatively,
`{"ai_prefix": false, "extra_prefixes": []}` retains subject validation without
adding anything. Disabling a prefix stops requiring it; it does not remove
previously written prefixes or rewrite history.

### Commands And Existing Hooks

```sh
python3 "$tool" --repo /path/to/project install
python3 "$tool" --repo /path/to/project uninstall
python3 "$tool" check /absolute/path/to/message.txt
python3 "$tool" fix /absolute/path/to/message.txt
python3 "$tool" hook /absolute/path/to/message.txt
```

`--repo` precedes the subcommand. Relative message paths are relative to the
process's current directory, not `--repo`. `hook` honors repository `mode`;
`check` is always read-only; explicit `fix` is a manual correction command.
Agents must honor check-only policy rather than silently calling `fix`.

Installation copies a self-contained executable to the default `commit-msg`
path. It works after the Skill source is moved or deleted. Reinstallation of
identical content is idempotent and repairs its executable mode. Uninstallation
removes only an identical copy; modified or older hooks are preserved for
manual reconciliation. Default Git hooks are shared by linked worktrees;
install/uninstall therefore affects this clone's linked worktrees too, with
each worktree reading its own policy.

Existing differing hooks, symlink/hardlink hooks, symlink hook directories, and
any configured `core.hooksPath` are refused without replacement or config edits.
For Husky, pre-commit, or another hook manager, integrate this command into its
existing `commit-msg` entry point using that manager's supported mechanism:

```sh
python3 /absolute/path/to/commit_message.py hook "$1"
```

Propagate its nonzero exit status so the commit fails. This integration needs
the script to remain at that path. No existing hooks are automatically chained.
Installation and removal validate policy before any write; they do not require
identity. Automatic upgrades of differing installed copies are not supported.

### Message Preservation And Limits

Only the first nonblank subject is normalized; put it before any comment lines.
Leading comment lines are rejected because Git's cleanup mode may retain them
as the actual commit subject. Known current
prefix tokens are reordered and deduplicated; other bracketed content is kept.
An existing different client/model group is retained as subject content: remove
it explicitly when amending attribution. The body, trailers, comments, UTF-8
text, and LF/CRLF endings are preserved. Empty/comment-only/prefix-only subjects
are rejected. Message files must be regular UTF-8 files, not symlinks or
hardlinks. Non-UTF-8 Git commit encodings are unsupported. An explicit Git
comment prefix is honored; `core.commentChar=auto` is unsupported. A prefix
that Git would treat as a comment is rejected before any edit.

Merge and amend messages are checked when Git invokes this hook. Autosquash
messages are exempt by default; setting `skip_autosquash: false` also normalizes
them, which can prevent autosquash matching. Rebase/cherry-pick paths that do
not invoke `commit-msg` are not covered. Local hooks can be bypassed by Git
options such as `--no-verify` or a different hooks directory; this is a local
workflow convention, not server-side enforcement. See the authoritative
[Git hook documentation](https://git-scm.com/docs/githooks),
[hooks path configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath),
and [autosquash message behavior](https://git-scm.com/docs/git-commit).

## When It Triggers

- An agent is about to execute `git commit`, including `--amend` or `-F`.
- Install, remove, configure, check, or fix commit-message attribution hooks.
- Configure machine prefixes, opt in per repository, or independently disable
  machine, repository, or AI prefix groups.

## When It Does Not Trigger

- Git inspection, staging alone, branch creation, or pushing existing commits.
- PR comments/reviews, release notes, or non-Git text formatting.
- Permission to commit, amend, or publish without an existing user request.
