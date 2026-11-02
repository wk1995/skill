# Changelog

## [Unreleased]

## [0.1.0] - 2026-11-02

- Change-Type: initial
- Summary: Add commit-time AI client/version/model attribution, configurable repository prefixes, check-only and disabled policies, and a self-contained Git commit-msg hook with safe installation and removal.
- Compatibility: New experimental Skill; no previous contract or state to migrate. Requires Python 3.10+ and Git 2.45+. No hook is installed by merely discovering the Skill. Existing hooks and custom core.hooksPath settings are preserved; hook-manager integration is explicit. Autosquash messages are exempt by default, and current identity is supplied per invocation rather than persisted.
