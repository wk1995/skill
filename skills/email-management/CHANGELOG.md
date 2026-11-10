# Changelog

## [Unreleased]

- Accept underscores in native instance/profile selectors while keeping local account IDs strict; this preserves native CLI profile choices without renaming them. Existing valid references remain unchanged.
- Initial development implementation; no production installation or real-mail acceptance is implied.
- Preserve the original design and 94-case acceptance definitions; record actual offline verification separately.

## [0.1.0] - 2026-11-10

- Change-Type: initial
- Summary: Introduce portable multi-provider email workflows, on-demand backend references, and a POSIX-only private account-reference helper with isolated regression tests.
- Compatibility: New experimental component with sync identity email-management; no previous Skill contract or account file migration. Existing mail clients remain responsible for authentication and protocol operations. Native account integration and Windows ACL storage are not certified by offline checks.
