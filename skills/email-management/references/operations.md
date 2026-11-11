# Mail Operations And Result Rules

Read after the selected provider reference. These are execution rules for the Agent and native backend, not a new common mail API. The bundled account helper does not enforce or perform remote operations.

## Queries

Use explicit selected accounts, folder roles, user time zone and an inclusive-start/exclusive-end interval. Map to the native query grammar; if its date precision differs, disclose the boundary and filter only metadata actually obtained. Preserve every filter and per-account cursor when paging. Start with metadata, obtain body segments only as needed and report any incomplete range.

Retain account/instance identity when merging results. Identical Message-ID or subject across mailboxes does not establish one shared record. Honor verified non-marking reads; avoid automatic read receipts. Keep inferred tasks as text unless the user requested a separate integration action.

## Drafts And Threads

Distinguish conversation wording from a mailbox draft. Saving a draft requires the user's saving intent, native write permission and a verified account. Report `draft_saved` only after native success. Return real links when provided; do not construct one from guessed IDs.

Use the provider's reply/reply-all/forward mode when there is a parent message. Preserve thread ID or In-Reply-To/References as applicable. Deduplicate reply-all recipients against the sender's verified address/aliases, expose final To/CC, and do not infer hidden BCC. Forward only explicitly selected attachments.

Reread ownership and revision before editing. Preserve attachments, MIME structure and unchanged fields. With no reliable conditional update or safe replacement, another draft may be saved under the user's intent while preserving the original; do not delete the old one first. Concurrent human edits require re-preparation. Report actual old/new references and partial failures.

## Sending

For every direct new-send, reply, reply-all, forward or draft-send entry:

1. Check the actual account/instance, applicable native reference and current sending permission. Preparation that saves a draft separately requires draft-write authorization.
2. Show final sending account/alias, To/CC/BCC, subject, body, reply context and real attachment list. Include any native signature/quote transformation affecting the content.
3. Follow native human confirmation requirements; a returned token or `--confirm-send` is a transport mechanism, not proof of consent. Existing user consent is reusable only for this unchanged final payload when native rules permit it. Cancellation, expiry or content changes invalidate the prior action.
4. Bind submission to immutable native payload/bytes or a verified content-binding mechanism. Mutable local paths, mutable remote drafts and one-time size/hash checks are insufficient by themselves. If the installed backend cannot guarantee this binding for the selected input, automatic sending stays unavailable. Offer an accurately described draft/user-client handoff without claiming delivery.
5. Revalidate identity, permission and final content immediately before the actual submission. Submit once. Do not claim a local operation ID provides distributed exactly-once semantics.

Keep native tokens private and do not restore them into an automatic send after restarting a session. Writes within the current task/account are serial; this Skill does not coordinate unrelated processes or external mail clients.

## Acceptance And Recovery

| Observed native result | Report and action |
| --- | --- |
| Full acceptance | `submitted`; do not claim delivered/read without separate evidence |
| Partial recipient acceptance | `partial`; preserve accepted/rejected sets, never resend accepted recipients automatically |
| Explicit rejection before acceptance | Report the actual failure; do not retry with another identity |
| Timeout or lost response with uncertain acceptance | `unknown`; only read-only reconciliation, no automatic resend or backend switch |
| Accepted send, failed Sent-copy save | Keep submission result and separate warning; no resend to repair the copy |
| No sufficient reconciliation evidence | Keep `unknown`; an absent Sent copy or similar subject is not proof of failure/success |

Keep actual observations and failed attempts distinct; never manufacture an Issue, timestamp or result to fill a report. If the user later chooses a new send despite an unknown earlier result, explain possible duplication and prepare a new bounded action with its own scope.

## Attachments

Keep files and extracted text in verified private external destinations. Identify ordinary file attachments, inline parts, link-only attachments and oversized/provider-managed downloads separately. Apply the minimum applicable per-file/total limit from backend, service and local policy. Do not claim unsupported OCR, decryption or Office parsing.

Do not execute attachments or automatically fetch URLs. A backend's temporary paths, parsing cache, logs and upload staging must also stay outside Git. Use an actual bounded file writer that rejects traversal, protected locations, links and unintended overwrite. The account helper only checks proposed paths; it is not that writer. If the selected download path lacks verified containment/overwrite handling, return metadata or perform a separately validated local write rather than claiming a safe download.

## Management And Retries

Verify the selected target set and native folder/label role before flags, move, archive or trash. Require a verified safe move/fallback; never substitute broad deletion or expunge. Return per-item outcomes/new references and leave unselected mail unchanged. No cross-mailbox rollback is promised. Reread failed targets before an explicitly requested continuation, and never repeat successful targets for a cleaner-looking batch result.

Transient read errors may retry up to two times after the first attempt, respecting rate limits and the current request's wait budget. Authentication, bad input and unsupported capability need a corrected prerequisite, not blind retries. Do not automatically apply read retries to writes. Long waits or cancellation do not leave a hidden background send or watcher.
