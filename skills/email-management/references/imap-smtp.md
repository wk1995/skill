# Himalaya / Standard IMAP And SMTP

Use for NetEase 163/126, approved standard work mailboxes and explicitly selected alternatives. Source baseline: [Himalaya README](https://github.com/pimalaya/himalaya/blob/42134fd20ca6d37aa86e02d6777487231cfe7032/README.md) and [features/version](https://github.com/pimalaya/himalaya/blob/42134fd20ca6d37aa86e02d6777487231cfe7032/Cargo.toml). That source is 2.2.1; older binary/package managers may expose different commands, flags or no MCP. Inspect actual `--version`/`--help`, never silently upgrade.

## Configuration And Identity

Read [local storage](local-storage.md). Obtain the user's actual service, TLS endpoints and authorization method; a custom work domain is insufficient. NetEase free 163 and 126 need separate official settings/protocol authorization; enterprise products are not the same preset. Server-specific client identification and folder mappings must be verified by read-only checks.

Configure through an authorized native setup with keychain/approved secret-command input. Do not keep raw passwords in a tracked TOML. Inspect native config selection and all merged sources: the baseline loads multiple user config paths, with a home rc file able to override earlier settings. Use an installed explicit config selector when available, otherwise verify the entire native selection and its private locations. Do not invent a universal `--config` argument or assume `config_path` in the local index controls the binary automatically.

Use native `account list` / `account check` help and a selected read-only mailbox check to verify the native account choice. Bind the actual account selector to `instance`; verify what the installed selector accepts. A server-only SMTP configuration cannot browse an inbox; IMAP-only access need not pass an SMTP readiness check. Never disable TLS validation to make a connection work.

## Command Families

These are baseline families to inspect with `--help`; preserve the installed account/backend selectors and JSON option on each call:

| Task | Baseline family |
| --- | --- |
| Folder roles | `himalaya mailbox list` |
| Metadata/pages | `himalaya envelope list` |
| Search | `himalaya envelope search` |
| Body | `himalaya message read` |
| Attachments | `himalaya attachment ...` |
| Draft MIME store | `himalaya message add` targeting the verified Drafts role |
| Compose/reply/forward | `himalaya message compose`, `reply`, `forward` |
| Flags/move | `himalaya flag ...`, `himalaya message ...` |

The baseline uses `--json` and a cross-backend search DSL. Do not feed Gmail query text as an IMAP DSL or silently drop unsupported clauses. Treat numeric/native references as account/folder-bound; requery after UIDVALIDITY changes or moves. Inspect read command flags to preserve unread state. Raw IMAP and bulk delete/expunge are not shortcuts around the Skill's selected-operation boundary.

Draft MIME, thread headers, attachments and SMTP submission remain native responsibilities. Prefer verified composer support to ad-hoc shell-generated MIME. A draft/send path reading a mutable file needs verified immutable bytes/content binding; `--send` is not user authorization. Keep native file staging private and use the [operation/result rules](operations.md).

## Optional MCP

In the baseline `himalaya mcp` serves one selected account via stdio. Inspect its actual tools: metadata/body/attachment operations use the shared API. It lists read tools by default; `--allow-write` and `--allow-send` separately expose native mutations. Do not enable either just to inspect mail. CLI tools do not automatically inherit that MCP permission isolation.

MCP attachment results are embedded bytes rather than the CLI's arbitrary local-file output; composers can accept inline attachment data. Verify actual schema and size limit. Decode to disk only through a verified bounded local writer; tool output being called read-only does not certify safe file handling elsewhere. Multi-account configuration does not make one MCP instance a freely switchable account router.
