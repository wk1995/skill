# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- Add placement rules for PRDs, technical documents, and machine-readable state-machine specifications: root `doc/<requirement>/` for unified applications, the owning project's `doc/` for independent projects, and root `doc/<requirement>/` for shared requirements.
- Limit this Skill to document paths; exclude business relationships, requirement traceability, content schemas, and state-machine semantics. Use project boundaries rather than code entry-point count to identify ownership.
- Add scoped folder and project organization, including a source-to-destination mapping, collision handling, content preservation, path-reference repair, and relocation verification. Read-only advice and content-only updates do not trigger moves.
- Respect explicit destinations and required repository file locations. Preserve established shared documentation layouts instead of imposing a competing `docs/skills/` tree. Align both user READMEs with the updated triggers and workflow.

## [0.0.1] - 2026-09-04

- Established the changelog baseline for the current documentation-placement workflow.
