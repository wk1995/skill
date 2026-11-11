# Gmail / Google Workspace CLI

Primary workflow uses `gws` and Gmail API. [Source README baseline](https://github.com/googleworkspace/cli/blob/cd3697e07eb520056dcf142d0c7439bbb9ba32e9/README.md). The project lives in the Google Workspace organization but explicitly is not an officially supported Google product. Commands are generated from discovery; verify installed version/help/schema rather than assuming a fixed tool surface.

## Identity, OAuth And Local Selection

Only an authorized setup task may initialize OAuth or change scopes. Users complete trusted authorization; do not read token caches to recover a missing identity. Distinguish personal Gmail, Workspace tenant policy and service-account impersonation; do not choose domain-wide delegation to bypass a denied user grant.

The source supports `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` for a private config directory. If selecting a stored `config_path`, verify the installed override works and bind it to that task's process. Check for inherited token/credentials-file overrides that could select a different identity; never print their values. Keep log-file overrides/staging outside Git and leave debug logging off unless needed for an authorized diagnosis.

Use a native Gmail profile/identity response, discovered via schema, for the selected authenticated user, and compare its actual email address. Do not infer identity from a local file's display name. Read-only scopes cannot create drafts/send; compose/modify/send scopes are not interchangeable. Consult [official scopes](https://developers.google.com/workspace/gmail/api/auth/scopes); ask for needed permissions only within an authorized task.

## Discover And Map

```text
gws gmail --help
gws schema gmail.users.getProfile
gws schema gmail.users.messages.list
```

If an installed release exposes different resource names, use that release's help instead of guessing. The API resource mapping is:

| Task | Gmail API resource/action to inspect |
| --- | --- |
| Current user | `users.getProfile`, explicitly selected user context |
| Search/pages/body | `users.messages.list/get` and `users.threads` |
| Attachments | `users.messages.attachments.get` or native helper support |
| Save/update draft | `users.drafts.create/update` |
| Submit | `users.messages.send` or `users.drafts.send` |
| Flags/archive/trash | Message label changes, `trash`, and correct native semantics |

Prefer installed `+triage`, `+reply`, `+reply-all`, `+forward` or `+send` shortcuts when their semantics fit and their help is verified. A shortcut named send must never be assumed draft-only: follow its documented side effects. Native draft IDs can change after updates; do not submit an unverified mutable draft merely because the user saw an earlier version.

Preserve Gmail's native query, page tokens, thread IDs and per-message source. Archive removes the Inbox association; it is not deletion or an IMAP folder move. Keep base64url MIME/attachment bytes private; use a verified native composer/data path and inspect actual size limits. Missing payload-binding support leaves automatic sending of that input unavailable under [operations](operations.md).

Google's [official remote Gmail MCP](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server) is a separate preview/qualification workflow. It is not the initial default, and its real tool list must not be inferred from the REST API. Do not connect to an arbitrary third-party Gmail service or upload mailbox data to solve a CLI limitation.
