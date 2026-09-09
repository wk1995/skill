---
name: choose-project-doc-location
description: Choose where to create or update project documentation, including README, Wiki, PRDs, technical documents, and machine-readable state-machine specifications. Place requirement artifacts in a requirement subdirectory under root doc/ for projects with a unified code entry point, or in the owning independent project's doc/ directory, such as an individual Skill's doc/.
metadata:
  sync_id: "choose-project-doc-location"
  version: "0.0.1"
  triggering:
    include:
      - "Create, update, rewrite, or organize project documentation."
      - "Choose between README, repository docs, or GitHub Wiki for project information."
      - "Create, update, or place PRDs, technical documents, and machine-readable state-machine specifications."
    exclude:
      - "Edit application code, runtime state data, or non-documentation assets; machine-readable state-machine specifications used as project documentation are included."
      - "Manage copies or versions of an Agent Skill."
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/choose-project-doc-location
---

# Choose Project Doc Location

## Overview

Use this skill before editing project documentation, including PRDs, technical documents, and machine-readable state-machine specifications. Choose both the documentation surface and the owning project's directory before creating or updating the artifact.

## Decision Workflow

0. Announce that this skill is being used before inspecting or editing files.
1. Identify the real content type, not just the user's requested label.
2. Identify whether the repository has a unified code entry point (for example, an Android application) or contains independently maintained projects (for example, separate Skills). Determine which project owns the requirement; multiple code modules alone do not make an application a collection of independent projects.
3. Inspect the repository for existing conventions before choosing a destination:
   - `README.md`, `README.*`
   - `docs/`, `doc/`, `documentation/`
   - `CONTRIBUTING.md`, `ARCHITECTURE.md`, `CHANGELOG.md`
   - existing wiki checkout or `.wiki` repository if present
4. Apply the requirement-artifact placement rules below before the general surface rules. For other documentation, prefer the repository's existing pattern unless it conflicts with the general rules. Respect an explicit user-selected destination; explain any relevant tradeoff without silently redirecting it.
5. If writing to GitHub Wiki requires remote access or a separate wiki repository that is not available locally, explain the intended Wiki placement. Create a local Wiki draft only if the user requests one.

## Requirement Artifact Placement

PRDs (product requirements documents), technical documents for a requirement, and machine-readable state-machine specifications belong with the project that owns the requirement:

| Project structure | Required location |
| --- | --- |
| Unified code entry point, such as an Android application | `<project-root>/doc/<requirement>/` |
| Independent projects in one repository, such as this Skill collection | `<owning-project>/doc/`; for a Skill, `skills/<skill-name>/doc/` |

Use the singular directory name `doc` for these artifacts. In an independent project's `doc/`, use a requirement subdirectory when needed to separate multiple requirements. Keep artifacts for the same requirement together. A repository-level `docs/` directory for shared guidance does not replace these locations.

For example (filenames and serialization formats are illustrative):

```text
android-project/
  doc/
    device-pairing/
      prd.md
      technical-design.md
      state-machine.yaml

skill-repository/
  skills/
    example-skill/
      doc/
        prd.md
        technical-design.md
        state-machine.json
```

Choose a machine-readable format compatible with the intended consumer and preserve its schema when updating an existing specification. Such specifications are documentation even when serialized as JSON or YAML; runtime state snapshots, caches, and application implementation files are outside this placement rule. Create only the artifacts requested, not every file shown in the example.

For an update, find the existing artifact first. If its location differs from these rules, explain the target location and migrate it when organization or relocation is within the requested scope, updating references. Otherwise update it in place and report the placement mismatch; do not create a competing copy. Keep shared repository guidance at repository level and link to the owning project's requirement artifacts rather than duplicating them.

## Placement Rules

Choose `README.md` for:

- Project identity: what the project is, who it is for, and why it exists.
- Fast path setup: installation, minimal quick start, basic usage.
- Navigation to deeper docs.
- Short summaries of workflows, skills, architecture, or contribution model.
- Anything a first-time visitor must see on the repository landing page.

Choose versioned repository documentation for the following content. Use the requirement-artifact locations above where applicable; otherwise follow existing `docs/`, `doc/`, or per-project documentation conventions:

- Workflow details that change with code.
- Skill inventories, skill purpose tables, usage instructions, inputs, outputs, examples, and troubleshooting.
- Architecture, design decisions, integration details, release procedures, and developer onboarding.
- Documentation that should be reviewed with code changes, versioned with branches/tags, or available after cloning.

Choose GitHub Wiki for:

- Team knowledge that is useful but not tightly bound to one code version.
- Operational notes, background research, meeting-derived knowledge, broad FAQs, or long-lived internal manuals.
- Content edited by non-code collaborators when PR review is not required.
- Cross-project information that would clutter the repository.

Avoid placing version-sensitive workflow or skill usage docs only in Wiki. Prefer versioned repository documentation and link from `README.md`.

## Recommended Structure

For shared repository guidance, the following is one possible layout. Preserve existing per-Skill README conventions; requirement artifacts follow the owning project's `doc/` rule above:

```text
README.md
docs/
  workflow.md
  skills.md
  skills/
    <skill-name>.md
  architecture.md
  examples.md
```

Use `README.md` as the entry point:

- Keep overview sections concise.
- Include a short workflow summary and link to `docs/workflow.md`.
- Include a short skill summary and link to `docs/skills.md`.
- Do not bury detailed per-skill usage in the README unless the project has only one or two skills.

## Handling User Wording

When the user says "update README" or "create Wiki", check the content against the placement rules and explain a different recommendation when appropriate. Preserve an explicit destination requirement. When no destination is fixed:

- If the content is an entry-point summary, put it in README.
- If the content is a PRD, requirement technical document, or machine-readable state-machine specification, use the owning project's `doc/` location above.
- For other detailed, version-sensitive content, use the repository's documentation conventions and add/update README links.
- If the content is broad team knowledge or non-versioned reference, put it in Wiki or prepare a Wiki draft.

Follow explicit user placement instructions and preserve existing content when editing or relocating documents.

## Editing Guidance

Before editing, read the current target files and preserve the existing voice and structure. Keep README concise; move long explanations into docs. Use relative Markdown links for repo-local files. Do not create Wiki content locally unless the Wiki repository is checked out or the user asks for a draft.
