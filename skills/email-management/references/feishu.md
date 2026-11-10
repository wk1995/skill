# Feishu Mail

Use the user's activated Feishu mailbox with official `lark-cli mail`; a Feishu login or a third-party mailbox bound in the client does not prove this API is available. [Official baseline guidance](https://github.com/larksuite/cli/blob/1bfdcc2c1a0ed0296ddb6349d251bdd75145bc5a/skills/lark-mail/SKILL.md). Help inspected locally on lark-cli 1.0.73; real-mail integration remains untested. Feishu and international Lark contexts need separate identity/qualification checks.

## Discover And Verify

```text
lark-cli --version
lark-cli mail --help
lark-cli mail +triage --help
lark-cli mail user_mailboxes profile --help
```

Select the verified native CLI profile using the installed global `--profile` option when needed. The account index's `instance` is the intended profile choice, not proof the CLI is using it. Discover the profile API/schema and native user-auth flags from help; verify actual identity and activated mailbox before a query. User identity is required for writing/sending in this workflow. Do not broaden to bot/tenant-wide access to evade an authorization failure.

Only a user-authorized setup task may perform native login such as the baseline's mail-domain user authorization. Keep native token/cache/config/log files in verified local private storage; the account helper does not create or audit those files for the CLI. Do not print authorization caches. Prefer native scope-specific recovery instructions to guessing endpoints or output shapes.

## Operation Mapping

| Task | Installed 1.0.73 help family |
| --- | --- |
| Metadata/search | `mail +triage` |
| One/full multiple message(s) | `mail +message`, `mail +messages` |
| Thread | `mail +thread` |
| New mailbox draft | `mail +draft-create`, or a native draft-default compose path |
| Preserve draft structure | `mail +draft-edit` |
| Reply/reply-all/forward | `mail +reply`, `mail +reply-all`, `mail +forward` |
| Compose/send | `mail +send`; actual send requires its native confirmation flag |
| Existing drafts send | `mail +draft-send` or the verified native draft-send resource |
| Mark/move/trash | `mail +message-modify`, `mail +message-trash` and verified raw resources |

Inspect each selected command's current help/schema, including `--as user`, message IDs, body-file/patch-file handling and confirmation controls. Shortcuts defaulting to drafts do not prove every raw API is draft-only. Native high-risk `--yes` and `--confirm-send` flags are not user consent.

Use reply/forward modes for parent-message context rather than a new-mail draft. Preserve original attachments/quotes on edits and reread concurrent revisions. Return genuine draft links if produced, never build guessed URLs. If a mutable remote draft or local body/attachment file cannot be bound to confirmed content, do not automatically submit it; use the [operation rules](operations.md).

A returned download URL is not a local attachment. Retrieve only selected, authorized content using a validated private writer. No automatic read receipt, IM sharing, rule creation, recall, scheduled send or watcher setup is included in an ordinary email query. A send-status API can supply later evidence when available; submission acceptance alone is not delivery/read confirmation.
