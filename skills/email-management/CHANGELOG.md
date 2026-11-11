# Changelog

## [Unreleased]

- Reject overlapping private roots and shared QQ native configuration references when filesystem aliases refer to the same location.
- Reject known local email data paths during repository builds, including nested copies.
- Align the Feishu backend reference with the anonymized read-only validation record.
- Record explicitly authorized, anonymized QQ/Feishu read-only smoke outcomes and their managed execution history; raw mailbox evidence remains private. No core behavior or version change.
- Accept underscores in native instance/profile selectors while keeping local account IDs strict; this preserves native CLI profile choices without renaming them. Existing valid references remain unchanged.
- Initial development implementation; no production installation or real-mail acceptance is implied.
- Preserve the original design and 94-case acceptance definitions; record actual offline verification separately.

## [0.1.0] - 2026-11-10

- Change-Type: initial
- Summary: Introduce portable multi-provider email workflows, on-demand backend references, and a POSIX-only private account-reference helper with isolated regression tests.
- Compatibility: New experimental component with sync identity email-management; no previous Skill contract or account file migration. Existing mail clients remain responsible for authentication and protocol operations. Native account integration and Windows ACL storage are not certified by offline checks.
