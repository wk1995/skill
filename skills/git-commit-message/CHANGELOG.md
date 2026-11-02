# Changelog

## [Unreleased]

## [1.0.0] - 2026-11-02

- Change-Type: breaking
- Summary: Remove the global enabled option. Machine, repository and AI prefix switches independently control formatting; when all three are false, message bytes are preserved and identity is not required.
- Compatibility: Default machine opt-out, empty repository prefix list, prefix order and per-group behavior are unchanged. Configuration and file-safety validation still run with every group off. The machine configuration file is unchanged.
- Breaking-Change: Previously, a repository could use {"enabled": false} to bypass message formatting. Now any enabled key is rejected as an unknown configuration key before a message or hook is changed. Existing repositories using that option must update their policy.
- Migration: Replace enabled:false with machine_prefix:false, repo_prefix:false and ai_prefix:false. For enabled:true, delete enabled and retain the other settings. Update installed standalone hooks explicitly to use this release; no machine-config migration is required.

## [0.1.0] - 2026-11-02

- Change-Type: feature
- Summary: Add machine-level prefix configuration, placed before repository and AI prefixes, with repository switches for machine and repository groups. Machine prefixes are opt-in (`machine_prefix: false` by default); repository prefix values remain empty by default.
- Compatibility: Compatible optional inputs since 0.0.1. Existing repository policies retain their output because machine prefixes require explicit opt-in. Both configuration files are validated before writes, including disabled groups. Shared machine/repository tokens are emitted once. Machine settings are outside Skill installations and are not copied between devices. No persisted format migration is required; installed standalone hooks need explicit replacement to use this release.

## [0.0.1] - 2026-11-02

- Change-Type: initial
- Summary: Add commit-time AI client/version/model attribution, configurable repository prefixes, check-only and disabled policies, and a self-contained Git commit-msg hook with safe installation and removal. Repository policy may be committed for team sharing or kept untracked for local use, with identical loading and validation.
- Compatibility: New experimental Skill; the user explicitly selected initial version 0.0.1 before publication, replacing the unpublished 0.1.0 assignment. There is no previous published contract or state to migrate. The repository's current initial-version gate only accepts 0.1.0 or 1.0.0, so it rejects this explicitly requested version. Requires Python 3.10+ and Git 2.45+. No hook is installed by merely discovering the Skill. Existing hooks and custom core.hooksPath settings are preserved; hook-manager integration is explicit. Autosquash messages are exempt by default, and current identity is supplied per invocation rather than persisted.
