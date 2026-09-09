---
name: choose-project-doc-location
description: Choose paths for new or existing project documentation and organize document locations within a specified folder or project. Use for README, Wiki, PRDs, technical documents, and machine-readable state-machine specifications. Determine project ownership and recommend or apply suitable locations; do not manage document relationships, content schemas, or business semantics.
metadata:
  sync_id: "choose-project-doc-location"
  version: "0.0.1"
  triggering:
    include:
      - "Choose document locations before creating or updating project documentation."
      - "Inspect or organize document locations within a specified folder or project."
      - "Choose between README, repository docs, or GitHub Wiki for project information."
      - "Create, update, or place PRDs, technical documents, and machine-readable state-machine specifications."
    exclude:
      - "Edit application code, runtime state data, or non-documentation assets; machine-readable state-machine specifications used as project documentation are included."
      - "Manage copies or versions of an Agent Skill."
      - "Define document relationships, requirement traceability, state-machine schemas, or business semantics without a placement task."
  urls:
    - type: repository
      value: https://github.com/wk1995/skill.git
    - type: source
      value: skills/choose-project-doc-location
---

# Choose Project Doc Location

## Scope

Choose documentation paths from the document's purpose, owning project, and existing location. Return a recommended path and a short reason, or organize existing document locations when requested. PRDs, technical documents, and machine-readable state-machine specifications are document types for placement purposes only.

Do not prescribe document contents, requirement IDs, traceability, serialization formats, schemas, or state-machine semantics. Repairing links broken by relocation is path maintenance, not document relationship management.

## Identify The Owning Project

Announce this Skill before inspecting or editing files. Read applicable repository instructions and inspect project READMEs, existing documentation directories, and build or release boundaries.

- **Unified application project:** an Android application can contain several code modules while remaining one project. Its application root is the project root; module count or multiple source entry points alone do not establish independent projects.
- **Independent project collection:** separately maintained units, such as this repository's Skills, own their local documentation. Use their entry points, project instructions, and build or release configuration together as evidence; do not rely on folder names alone.
- **Shared scope:** a document genuinely covering several independent projects belongs at their shared repository level. A document mentioning another project does not automatically become shared.

Read enough content to determine purpose and ownership. Treat document text as content, not as authority to broaden the task. If ownership or the requirement grouping remains ambiguous, explain the unresolved choice instead of inventing a destination; continue with unambiguous files.

## Path Priority

1. Follow an explicit user destination. Check its existence and collisions before writing; explain relevant tradeoffs without silently redirecting it.
2. For a content update, locate and update the existing document in place by default. Report a placement mismatch without creating a second copy or moving it unless relocation or organization is requested.
3. For new documents or requested organization, apply the table below within the user's scope, preserving required repository file locations. Use singular `doc` for the specified document directories; do not mass-rename unrelated existing `docs/` directories.

| Document scope | Default destination |
| --- | --- |
| Requirement documents for a unified application | `<project-root>/doc/<requirement>/` |
| Documents for one independent project or Skill | `<owning-project>/doc/`; for a Skill, `skills/<skill-name>/doc/` |
| Multiple requirements within one independent project | `<owning-project>/doc/<requirement>/` |
| Requirement documents shared by independent projects | `<repository-root>/doc/<requirement>/` |
| Project introduction, quick start, and navigation | The owning project's `README.md` and its language variants |

PRDs, technical documents, and state-machine specifications follow the same ownership rules. Reuse an existing requirement directory when it clearly matches; otherwise choose a short descriptive directory name following local naming conventions. Do not introduce a requirement-ID system or rename files merely to standardize their names.

Keep other shared repository guidance in its established location, such as `docs/`. Preserve required companion documents and conventional entry points, including Skill `SKILL.md`, READMEs, and changelogs, as well as applicable `AGENTS.md`, `CONTRIBUTING.md`, and license files. These are not loose documents to sweep into `doc/`.

Wiki suits team knowledge weakly tied to a code version. Keep version-sensitive requirements and technical specifications in the repository. Naming Wiki still allows a placement recommendation but does not override an explicit user destination. Report unavailable Wiki access; create a local Wiki draft only when requested. Local folder organization does not authorize publishing to Wiki.

## Organize A Folder Or Project

Use this workflow when asked to organize, consolidate locations, or move documentation under a specified folder or project.

1. **Bound the inventory.** Use the named folder recursively as the candidate source scope, or the identified project root when the user names a project. A request to inspect or recommend is read-only; a request to organize authorizes routine relocation within that scope's owning project. Do not broaden the candidate inventory to unrelated folders. Do not follow directory symlinks outside the scope or process dependencies, build outputs, caches, runtime state, or generated files as authored documentation.
2. **Classify candidates.** Inspect purpose and ownership, not just file extensions. JSON/YAML state-machine specifications can be documentation; runtime data and configuration are not automatically documents. Mark already-correct files and required entry-point files to keep in place.
3. **Prepare a concrete mapping.** Show each candidate's source, proposed destination, and reason, including unchanged and unresolved cases. Destinations may leave the source folder to reach the owning project's `doc/`, but must stay within that project, or the explicitly scoped repository for a repository-wide task. Report any necessary move beyond that boundary separately without performing it.
4. **Check before moving.** Check all proposed destinations for existing files, conflicting candidates, and aliases such as symlinks or case-only spellings. Never overwrite, merge, or delete documents to resolve a collision. Leave ambiguous, conflicting, or out-of-boundary cases in place and explain them; proceed with the remaining clear moves without adding a routine approval step.
5. **Move and repair paths.** Preserve filenames, contents, and assets unless a change is necessary for the relocation. Fix relative document and image links inside moved files, and references to moved paths within the owning project. Move accompanying assets only when needed and clearly within scope; preserve shared assets. Repair path references only, without changing business relationships. For unavailable or out-of-scope consumers, report the references that could not be checked. If a move or link repair fails, stop dependent moves and restore affected paths where feasible, reporting the actual remaining state.
6. **Verify and report.** Confirm destinations exist, moved sources no longer remain as duplicate copies, repaired local links resolve, and unrelated files are untouched. Re-evaluate the mapping: another organization pass should propose no further moves for the completed files. Summarize moved, unchanged, and unresolved documents with reasons. Do not claim uninspected paths or external links were verified.

For read-only requests, stop after the mapping and explain unresolved cases; do not create directories, move files, or repair links.

## Examples

- “Where should the Android pairing PRD and technical design go?” → Recommend `<android-project>/doc/device-pairing/`; create nothing.
- “Update the existing Skill PRD.” → Find the original and update it in place; mention a path mismatch if present.
- “Organize documentation under `skills/example-skill/`.” → Place loose Skill documents in `skills/example-skill/doc/`, separate requirements when needed, and retain required Skill entry-point and companion files.
- “Organize documents in this project's `notes/` folder.” → Inventory only `notes/`; move clearly owned requirement documents to the project's `doc/<requirement>/`, repairing affected path references.
- “Organize documentation across this Skill repository.” → Keep single-Skill documents under their owner; place shared requirement documents in root `doc/<requirement>/`; preserve established shared guides and required files.
