# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- Add placement rules and triggers for PRDs, requirement technical documents, and machine-readable state-machine specifications: root `doc/<requirement>/` for projects with a unified code entry point, and the owning project's `doc/` for independent projects such as Skills.
- Align both user READMEs with the new locations, distinguish specifications from runtime state, and preserve existing artifacts and references during updates. Respect explicit user destination requirements while explaining placement tradeoffs.
- Clarify in both user READMEs that explicitly naming README or Wiki still triggers the placement check. This is a documentation-only change with no version or trigger-metadata change.

## [0.0.1] - 2026-09-04

- Established the changelog baseline for the current documentation-placement workflow.
