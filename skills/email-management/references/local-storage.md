# Private Local Account References

Read before discovering/saving accounts or handling local outputs. All real account metadata and mail data stay outside version control, Skill sources/installations, artifacts and synchronization inputs. A private index is not a credential vault or a connected-account assertion.

## Implemented Helper

`scripts/email_accounts.py` uses Python 3.10+ and the standard library. It does not run Git, a mail client, a shell command, a credential reader or a network call. All commands require POSIX storage and `O_NOFOLLOW`; unsupported platforms fail before mutation. No Windows ACL adapter is supplied. Do not bypass that rejection with ad-hoc file writes.

Commands below use `<skill>` to mean the current Skill directory, not an installation recommendation. Obtain a private absolute path from the user's task or the validated defaults. Do not create a real profile inside the checkout just to feed the helper.

```text
python3 <skill>/scripts/email_accounts.py paths
python3 <skill>/scripts/email_accounts.py list
python3 <skill>/scripts/email_accounts.py show --account <id>
python3 <skill>/scripts/email_accounts.py check-path --path <absolute-external-path>
python3 <skill>/scripts/email_accounts.py put
python3 <skill>/scripts/email_accounts.py put --replace
python3 <skill>/scripts/email_accounts.py remove --account <id>
```

`put` reads exactly one JSON profile from stdin, so private fields need not appear in process arguments. Prepare that input in memory or a user-authorized private file, never a tracked template containing real values. `--replace` is only for an intentional update to the same local ID; it is not permission to replace a different account silently.

`list` omits addresses and native paths. Use `show` only for the user-selected account when its details are needed. Its stdout is private task context, not material to paste into Git, a PR or a shared test report. Errors omit input values and OS path strings. A `put` result always includes `connected: false`; validate native identity and required capabilities independently. `remove` only removes the local reference, retains the previous index in the private backup and never deletes native credentials, messages or downloads.

All commands support a preceding `--root <absolute-external-base>` for an explicitly selected private/test namespace. It contains `config/`, `state/`, `cache/`, `data/`. It does not change the OS home or other applications' settings. Invalid explicit paths do not fall back to defaults.

## Default Locations And Format

| Purpose | Default external location |
| --- | --- |
| Account index | `${XDG_CONFIG_HOME:-$HOME/.config}/email-management/accounts.json` |
| Optional state/evidence | `${XDG_STATE_HOME:-$HOME/.local/state}/email-management/` |
| Re-creatable cache | `${XDG_CACHE_HOME:-$HOME/.cache}/email-management/` |
| User-kept data/attachments | `${XDG_DATA_HOME:-$HOME/.local/share}/email-management/` |

Only `put`/`remove` create config storage. `paths`, `check-path`, `list` and `show` do not create directories/locks. The helper reports/validates the other roots but does not automatically populate caches, archives, evidence or an entire mailbox.

Initial account format is JSON, not the earlier design's proposed `accounts.toml`: `{"schema_version":1,"accounts":{"<id>":<profile>}}`. JSON permits strict duplicate-key detection and atomic editing using only the standard library. No earlier implementation or user file is migrated. Native Himalaya/QQ TOML files remain native and are not converted.

Profile fields:

| Field | Meaning |
| --- | --- |
| `id` | Local choice ID; lowercase letters/digits/hyphens, at most 63 characters |
| `address` | Actual ASCII email address, checked again against the backend before use |
| `provider` | `qq`, `netease`, `gmail`, `feishu`, `imap-smtp` |
| `backend` | An allowed choice from the provider table |
| `instance` | Explicit local native account/profile or MCP-instance choice; lowercase letters/digits/hyphens/underscores, at most 63 characters |
| `config_path` | Optional absolute private native file/directory reference; mandatory for Himalaya and QQ MCP |

All other keys reject, including password/token/authorization-code/credential fields and asserted capabilities. Address duplicates across local IDs reject conservatively. Changing an existing ID's content requires `--replace`; registering the same content is a no-op. QQ MCP accounts cannot share the same instance or native config reference. This checks references, not whether native credential or attachment files are truly isolated: verify those separately using the provider procedure.

Synthetic shape, **not a real profile to register**:

```json
{"id":"example","address":"person@example.invalid","provider":"gmail","backend":"gws","instance":"example"}
```

A native configuration pointer may be registered before that backend creates the file, but does not imply readiness. When an existing reference is present, the helper checks private ownership/mode and rejects final symlinks and hard-linked files; it never opens the native configuration contents. A damaged index or unsafe existing reference is reported, not silently overwritten or redirected to another account. Preserve the file/backup for a user-authorized repair.

## Mutation Boundary And Recovery

Both direct mutation methods and CLI entry points validate the platform, all selected roots, profile whitelist, existing index and owned file identities before creating a directory/lock. Paths resolve through existing ancestors and reject Git worktrees, bare repositories and directories under a `SKILL.md`, including linked/case aliases to them. The running Skill and its ancestor cannot be selected as the private base.

Storage roots and QQ native configuration references use filesystem identity for existing paths. For paths awaiting creation, potentially equivalent spellings that differ only in case or Unicode normalization are treated as aliases. Select distinct paths before retrying a rejected registration or setup.

New private directories use `0700`, files use `0600`. Insecure existing owned storage rejects without chmod repair. Each mutation takes an exclusive private `.accounts.lock`, rereads the index, writes a same-directory temporary file, retains the previous valid index as `accounts.json.bak`, atomically replaces the index and fsyncs. Writes use an open directory descriptor; final links/hardlinks are not followed. Failure retains recoverable data and cleans only its own temporary file/lock. A post-replacement fsync failure may leave the new index visible: read it back before explicitly retrying.

An existing lock is not automatically stolen or removed. Inspect it locally and resolve the owning operation before an explicit retry; do not delete an unknown process's files. If the main index is damaged, preserve both it and its backup; this version does not auto-restore a backup, migrate schemas or purge private data. Reads and no-op mutations still validate the owned paths; a successful no-op is not a network health check.

These checks constrain this helper. They are not an OS sandbox against another process with the same user's authority moving parent directories or changing files concurrently. Native clients may create their own configuration, logs, caches and downloads: bind/verify their actual private paths separately. `check-path` is a diagnostic, not a race-free file writer for another program; do not use it to claim arbitrary backend file writes are guarded by this helper.

## Git And Distribution

Only synthetic profile shapes and public provider instructions are distributable. Do not read or copy actual local files during builds. Ignore rules for `.email-management/` and `email-management.local.*` are secondary precautions; tracked or renamed private copies still require inspection. Never force-add them. Do not upload real execution evidence under a default Issue attachment workflow. Stop before publication if private content has entered the proposed output; preserve local originals and report without rewriting shared history automatically.

The repository builder rejects `.email-management`, `email-management.local.json` and `email-management.local.toml` anywhere in selected build inputs. Move any such data outside the checkout before rebuilding.
