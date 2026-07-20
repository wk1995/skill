---
name: choose-project-doc-location
description: Decide whether requested project documentation belongs in README, repository docs, or GitHub Wiki before creating or updating it. MUST use before editing documentation when the user asks to create, update, rewrite, or organize README/readme, Wiki/wiki, docs/doc, project documentation, project details, workflow/workflows, 流程, 项目文档, 项目说明, 仓库说明, 使用说明, skill 列表, skill 作用, skill 使用说明, architecture notes, onboarding guides, or repository documentation. Treat the user's words "README" and "Wiki" as tentative labels, not final placement decisions.
metadata:
  version: "0.0.1"
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/choose-project-doc-location
---

# Choose Project Doc Location

## Overview

Use this skill before editing project documentation when the requested destination may be README, GitHub Wiki, or detailed docs. The goal is to choose the right documentation surface first, then create or update the matching artifact.

## Decision Workflow

0. Announce that this skill is being used before inspecting or editing files.
1. Identify the real content type, not just the user's requested label.
2. Inspect the repository for existing conventions before choosing a destination:
   - `README.md`, `README.*`
   - `docs/`, `doc/`, `documentation/`
   - `CONTRIBUTING.md`, `ARCHITECTURE.md`, `CHANGELOG.md`
   - existing wiki checkout or `.wiki` repository if present
3. Prefer the repository's existing documentation pattern unless it conflicts with the decision rules below.
4. If writing to GitHub Wiki requires remote access or a separate wiki repository that is not available locally, explain the intended Wiki placement and create a repo-local draft only when useful.

## Placement Rules

Choose `README.md` for:

- Project identity: what the project is, who it is for, and why it exists.
- Fast path setup: installation, minimal quick start, basic usage.
- Navigation to deeper docs.
- Short summaries of workflows, skills, architecture, or contribution model.
- Anything a first-time visitor must see on the repository landing page.

Choose repo-local `docs/` for:

- Workflow details that change with code.
- Skill inventories, skill purpose tables, usage instructions, inputs, outputs, examples, and troubleshooting.
- Architecture, design decisions, integration details, release procedures, and developer onboarding.
- Documentation that should be reviewed with code changes, versioned with branches/tags, or available after cloning.

Choose GitHub Wiki for:

- Team knowledge that is useful but not tightly bound to one code version.
- Operational notes, background research, meeting-derived knowledge, broad FAQs, or long-lived internal manuals.
- Content edited by non-code collaborators when PR review is not required.
- Cross-project information that would clutter the repository.

Avoid placing version-sensitive workflow or skill usage docs only in Wiki. Prefer `docs/` and link from `README.md`.

## Recommended Structure

For repositories containing workflows and skills, prefer:

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

When the user says "update README" or "create Wiki", treat that as intent to update project documentation, not as a final storage decision. Make the placement decision from the content:

- If the content is an entry-point summary, put it in README.
- If the content is detailed, version-sensitive, or tightly connected to repository behavior, put it in `docs/` and add/update README links.
- If the content is broad team knowledge or non-versioned reference, put it in Wiki or prepare a Wiki draft.

If the user explicitly insists on a destination after the tradeoff is clear, follow that destination unless it would break repository conventions or overwrite important content.

## Editing Guidance

Before editing, read the current target files and preserve the existing voice and structure. Keep README concise; move long explanations into docs. Use relative Markdown links for repo-local files. Do not create Wiki content locally unless the Wiki repository is checked out or the user asks for a draft.
