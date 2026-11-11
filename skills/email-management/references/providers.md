# Backend Selection

Start with the user's selected account and tool. Read the selected backend's reference only. Installed help/schema and verified account identity control what is usable; a registered profile and a source README do not prove current authentication.

| Provider | Allowed index backend | Reference |
| --- | --- | --- |
| QQ personal | `qq-email-mcp`, or explicitly selected `himalaya` | [QQ](qq-email-mcp.md); [IMAP/SMTP](imap-smtp.md) for the alternative |
| NetEase 163/126 | `himalaya` | [IMAP/SMTP](imap-smtp.md) |
| Gmail / Google Workspace | `gws`, or explicitly selected `himalaya` | [Gmail](gmail.md); alternate protocol/API scope must be independently verified |
| Feishu mailbox | `lark-cli` | [Feishu](feishu.md) |
| Approved standard work mailbox | `himalaya` | [IMAP/SMTP](imap-smtp.md) |

For a CLI, discover the executable and inspect its version/help without logging in. For MCP, inspect the actual instance's tools and output schemas. Confirm the account/profile using a native identity result or a verified native account/config mapping plus a read-only mailbox check. If identity cannot be established, stop; do not guess a universal identity command.

Use the index `instance` as a choice that must match the backend's actual account/profile/connection. Native IDs retain their source and instance. Never silently fallback after a write begins. An explicit read-side switch must reverify identity, filters and references; do not reuse cursors from the previous backend.

Later providers (Graph/Outlook, iCloud, enterprise-specific presets, Agently Mail and preview Gmail MCP) are described in the roadmap, not accepted by the initial helper's provider enumeration. Add a new provider only with its configuration isolation, command mapping, local-data boundary and acceptance evidence; do not substitute Agently Mail for an existing personal QQ inbox.
