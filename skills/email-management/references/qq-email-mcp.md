# QQ Email MCP

Use for an existing personal QQ mailbox through `xieningqing/qq-email-mcp`; it is a community project, not a Tencent official MCP service. Source baseline: [README](https://github.com/xieningqing/qq-email-mcp/blob/e3b6015077ff3e1c4d69272e1fe67ff596fef613/README.md), [tools](https://github.com/xieningqing/qq-email-mcp/blob/e3b6015077ff3e1c4d69272e1fe67ff596fef613/docs/mcp-tools.md). Source metadata declares 0.1.1 and Node >=20.19; verify the installed distribution rather than assuming it matches that commit.

## Connect And Identify

An authorized setup task may configure one instance for one account. The user enables official IMAP/SMTP and provides an authorization code through the backend's trusted secret input; never request that it be written into this Skill or a repository. Do not place a code in command arguments/history.

Inspect installed initialization help before use. The upstream initializer supports explicit config/credential locations. Bind `QQ_EMAIL_MCP_CONFIG` to the verified absolute private native config so a same-named file in the working directory or package cannot override it. Configure and verify separate credentials, attachment and log paths for each instance; distinct config files alone do not establish credential isolation.

On non-Windows upstream uses host-derived-key encryption, explicitly described as obfuscation, not a strong vault. Do not enable it as a strong-protection credential solution. Use a separately verified keychain/controlled child-process credential injection or an explicitly selected alternative backend. The Skill's POSIX index does not fix upstream secret storage. Windows DPAPI and its ACL/identity behavior require native validation; the bundled index helper does not certify Windows setup.

Read `mail_status` and `mail_folders`. Match returned `account` to the selected account. `connected` (IMAP readable) and `ready` (including SMTP) differ; a read-only task need not enable sending to make ready true. Examine permissions and folder roles/capabilities. Register the non-secret local reference only after this verification; the helper itself always says unconnected.

## Tool Mapping

| Task | Native tool |
| --- | --- |
| List/filter/page | `mail_list`, `mail_search`, `mail_digest` |
| Body/segment/thread context | `mail_get` |
| Selected attachment metadata/download/extraction | `mail_attachment` |
| Create/replace draft | `mail_draft` |
| New/reply/reply-all/forward | `mail_send`, choosing its actual mode |
| Seen/unseen/star/move/archive/trash | `mail_update` |

Inspect each installed input schema; do not fabricate parameter names from this table. Keep opaque `message_ref` bound to instance/folder/UIDVALIDITY and use the exact returned cursors. List/search support recent-day and snippet controls in the source baseline; verify them before relying on them.

Default permissions are read-only. Draft, update and send need their respective grants. The send preview uses a single-use native confirmation token (source default TTL 10 minutes); some clients support elicitation. Wait for actual user permission, not an agent-generated response. Verify the installed native code binds the exact normalized payload/attachments before enabling a send; use [operation rules](operations.md) for mutation/unknown handling.

`mail_draft` is not `mail_send`. Draft replacement and safe move fallbacks must preserve recoverability. Upstream does not offer permanent deletion. Partial recipient acceptance and Sent-copy failure must remain distinct; do not compensate by resending. PDF/Office extraction is only as capable as the installed parsers and limits, not a guarantee for scan/encrypted documents.
