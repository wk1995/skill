# Choose Project Doc Location

Language: **English** | [中文](README.zh-CN.md)

`choose-project-doc-location` selects paths for project documentation and organizes document locations within a specified folder or project. It covers PRDs, technical documents, and machine-readable state-machine specifications without managing their business relationships or content schemas.

## How To Use It

Provide the document type, owning project, existing path if known, and any explicit destination. For organization, name the folder or project to process. The Skill identifies ownership and returns a path with a short reason; when asked to organize, it prepares a source-to-destination mapping and performs clear, conflict-free moves.

```text
Where should the Android pairing PRD and technical design go?
Update the existing PRD for the sync-skills Skill.
Organize document locations under skills/example-skill/.
Organize the documents in this project's notes/ folder.
Organize document locations across this Skill repository.
Only inspect the docs in notes/ and recommend paths; do not move them.
```

Explicit destinations take priority. Content updates stay at the existing location by default, with misplaced documents reported. New documents and requested organization use the rules below, while required repository file locations are preserved. Merely asking for advice never moves files.

## Default Locations

A unified application can have many code modules; these are not automatically independent projects. Independently maintained projects, such as this repository's Skills, own their local documents. The Skill uses project instructions, entry points, and build or release boundaries to distinguish them.

| Document scope | Default destination |
| --- | --- |
| Unified application's requirement documents, such as an Android feature | `<project-root>/doc/<requirement>/` |
| One independent project or Skill | `<owning-project>/doc/`, such as `skills/<skill-name>/doc/` |
| Multiple requirements in an independent project | `<owning-project>/doc/<requirement>/` |
| Requirement documents shared by independent projects | `<repository-root>/doc/<requirement>/` |
| Project introduction, quick start, and navigation | The owning project's `README.md` and its language variants |

PRDs, technical documents, and state-machine specifications use the same ownership rules. Use singular `doc` and reuse matching requirement directories. File formats and names are not prescribed. Shared repository guides can remain in an existing `docs/`; Wiki suits knowledge less tied to a code version.

## Organizing Existing Documents

A named folder is the recursive source scope; naming a project covers that project. Files may move from the named folder into the owning project's `doc/`, but not beyond that project unless a broader repository scope was explicitly requested. Path references elsewhere in the owning project may be repaired as part of relocation.

The Skill shows original paths, destinations, and reasons before moving clear candidates. It preserves contents and required files such as Skill entry points, READMEs, and changelogs. It repairs links and asset paths affected by moves, and checks that completed files would stay in place on another pass.

Ambiguous ownership, destination collisions, and moves beyond the scope are reported and left unchanged; other clear moves can proceed. Generated files, dependencies, runtime data, and out-of-scope symlink targets are not swept into documentation folders. The result lists moved, unchanged, and unresolved files. Local organization does not publish anything to Wiki.

See [SKILL.md](SKILL.md) for the placement and relocation procedure.

## When It Triggers

Use this Skill to choose paths before creating or updating project documentation, to inspect existing document locations, or to organize documentation under a specified folder or project. PRDs, technical documents, machine-readable state-machine specifications, README, repository guides, and Wiki placement requests are included. Naming README or Wiki still allows a placement check while preserving an explicit destination.

## When It Does Not Trigger

Do not use it for application code, runtime snapshots or caches, non-documentation assets, or managing and synchronizing Agent Skill copies. Defining requirement IDs, document relationships, state-machine schemas, or business semantics without a placement task is outside its scope. JSON/YAML state-machine specifications are eligible documents, but the Skill only decides their paths. Repairing broken path references during a move does not introduce business traceability.
