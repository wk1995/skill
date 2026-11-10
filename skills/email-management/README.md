# Email Management

Language: **English** | [中文](README.zh-CN.md)

Manage selected QQ, NetEase, Gmail, Feishu and standard IMAP/SMTP mailboxes through existing CLI/MCP backends, with local-only account references, reading, search, drafts, authorized sending and basic management. Use for email-account setup and mailbox tasks; exclude mail-server administration and marketing campaigns.

## How To Use It

Describe the account and task, for example:

- “Connect my QQ test mailbox and verify read-only access first.”
- “Search the selected NetEase account for unread supplier mail from the last seven days.”
- “Save a Gmail reply draft in the original thread; show me the content before sending.”
- “Download the selected attachments to my private local directory.”
- “Search only these two accounts and preserve the source of every result.”

An available backend and the corresponding account permission are prerequisites. The Skill selects and operates tools; it is not a replacement mail client or a preauthenticated connection. It will identify missing tools or qualifications rather than silently installing software, switching accounts or sending a test email.

The bundled [private account helper](references/local-storage.md) can validate local paths, store non-secret account references, list/select them across sessions and remove a selected reference. It uses Python 3.10+ and POSIX private files; Windows storage mutations are explicitly unavailable until a verified ACL adapter is supplied. It never connects to mail, stores passwords/tokens, or executes a backend. Removing an account reference does not delete credentials, messages or attachments.

## When It Triggers

Email-account setup/selection; reading, searching and analyzing selected mailboxes; email composition and mailbox drafts; explicitly authorized sending/replying/forwarding; selected attachment downloads and basic message management.

## When It Does Not Trigger

Mail-server or tenant-wide administration, DNS/SPF/DKIM/DMARC, marketing campaigns, mass mailing, permanent deletion, general prose without email intent, or unrelated contact/calendar/chat/document work. An explicitly selected specialist Skill retains its task; this Skill does not duplicate its writes.

## Backends And Current Verification

| Mailbox | Workflow backend | Current verification boundary |
| --- | --- | --- |
| QQ | QQ Email MCP; Himalaya as an explicit alternative | Single-account MCP isolation and private credential setup required; real-mail tests pending |
| NetEase 163/126 | Himalaya IMAP/SMTP | Separate provider settings and actual protocol/authorization checks required; real-mail tests pending |
| Gmail / Workspace | gws CLI / Gmail API | Installed schema and OAuth policy checks required; real-mail tests pending |
| Feishu | lark-cli mail | User identity, mailbox activation and native draft/send flow required; command help inspected, real-mail tests pending |
| Standard work mailbox | Himalaya IMAP/SMTP | Administrator-approved protocols/TLS and per-action capability required; real-mail tests pending |

This is the initial `0.1.0` development implementation. The portable workflow, provider references and POSIX account helper are present; offline helper tests do not establish real account interoperability. Outlook/Microsoft 365, iCloud, enterprise presets, Agently Mail, official Gmail MCP preview and background/extended features remain roadmap items.

## Private Local Information

Keep **all real mailbox information** outside Git and Skill installations, including addresses, aliases, native config, credentials, message data, attachments, logs, test evidence and backups. The default account index is under the local XDG config directory, with state/cache/data separated. Only synthetic definitions and public provider information are distributable. See [local storage](references/local-storage.md) for implemented checks and platform limits.

Read [SKILL.md](SKILL.md) for the procedure, [operations](references/operations.md) for write and result rules, and [test design](doc/test-plan.zh-CN.md) for the 94 planned acceptance cases. [Implementation and validation](doc/implementation-and-validation.zh-CN.md) separates actual offline checks from pending integration.
