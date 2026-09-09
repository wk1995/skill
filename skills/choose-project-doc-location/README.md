# Choose Project Doc Location

Language: **English** | [中文](README.zh-CN.md)

`choose-project-doc-location` selects a location for project documentation, including PRDs, technical documents, and machine-readable state-machine specifications, based on the content and the project that owns it.

## How To Use It

Describe the information that needs documenting, its owning project or requirement, and any requested destination. The Skill checks the project structure and existing documentation conventions, then guides the documentation change. Naming “README” or “Wiki” still triggers the placement check; explicit destination requirements are respected, with relevant tradeoffs explained.

For example:

```text
Document the deployment workflow for new contributors.
Should this project overview be added to the README or the Wiki?
Organize the repository documentation for the new integration.
Create a PRD, technical design, and machine-readable state-machine specification for Android device pairing.
Update the PRD and state-machine specification for the sync-skills Skill.
```

## Where Requirement Artifacts Go

Keep a requirement's PRD, technical documents, and machine-readable state-machine specifications together:

| Project structure | Location |
| --- | --- |
| Unified code entry point, such as an Android application | `<project-root>/doc/<requirement>/` |
| Independent projects, such as the Skills in this repository | `<owning-project>/doc/`, specifically `skills/<skill-name>/doc/` for a Skill |

Use singular `doc`. Independent projects can add requirement subdirectories within their own `doc/` when needed. For example, Android pairing documents could be `doc/device-pairing/prd.md`, `technical-design.md`, and `state-machine.yaml` in the same directory; a Skill's documents could be `skills/sync-skills/doc/prd.md`, `technical-design.md`, and `state-machine.json` in that Skill's `doc/`. Filenames and formats are examples, and only requested artifacts are created.

Existing shared `docs/` guidance can remain at repository level. README provides the overview and links; Wiki is for knowledge less tied to a code version. Existing artifacts are located before updates: relocation includes updating references when in scope, otherwise the artifact is updated in place and the placement mismatch is reported without creating a duplicate.

See [SKILL.md](SKILL.md) for the full placement rules and editing guidance.

## When It Triggers

Use this Skill when creating, updating, rewriting, or organizing project documentation, including PRDs, technical documents, machine-readable state-machine specifications, README content, repository docs, project details, workflow documentation, architecture notes, onboarding guides, or Wiki material. It also triggers when the user names README or Wiki directly, because the placement still needs to be checked against the content and repository conventions.

## When It Does Not Trigger

Do not use this Skill for ordinary code changes, runtime state snapshots or caches, non-documentation assets, or managing and synchronizing copies of Agent Skills. JSON/YAML state-machine specifications used as project documentation are included; implementing a state machine in application code is not.
