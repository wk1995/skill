# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [0.1.0] - 2026-09-11

- Change-Type: initial
- Summary: Added guidance for project-defined version grammars with arbitrary component counts, separators, and numeric or nonnumeric tokens.
- Initial versions: Use an explicitly supplied or project-required initial value; otherwise default to numeric 0.0.1, resolving custom-format conflicts before writing and preserving existing release history.
- Trigger boundaries: Explicitly cover project-owned version values, policy checks (including existing-policy CI), and release evidence; exclude incidental version mentions, dependency/tool upgrades, build/publish-only tasks, ordinary code changes, notes formatting, and Skill-copy management. Mixed requests use only the version-policy portion.
- Compatibility: This new Skill defines policy guidance without changing existing Skill behavior.
