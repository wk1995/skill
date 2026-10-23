# Two authoritative data-source modes

Select the source before creating or updating test data. For a new project without a recorded choice, use **`github-issues` (default)**. Use **`repository-files`** when explicitly selected by the user or the existing project configuration. Preserve an existing source until an explicit switch; a connection failure never selects the other mode automatically. Record the choice and source location in the project's existing workbench configuration or test documentation. These names describe the workflow contract; they are not new fields supported by the bundled archive parser.

| Contract | `github-issues` — default | `repository-files` — explicit alternative |
| --- | --- | --- |
| Authority | Selected GitHub host/repository and mapped Issues/comments | Selected repository and Git-tracked test files |
| Case library | Case-definition Issues with stable case IDs and structured definitions | Definition files, separate from execution records |
| Execution history | Round Issues with frozen definitions, source/build, environments, and structured event/observation comments | Round/record files with the same frozen context and append-only events/observations |
| Evidence | Attach screenshots/logs to the relevant Issue/comment and store the returned URLs | Store evidence URLs with records; attachments need not be committed to Git |
| Webpage | Read/project Issues; send validated mutations through a project adapter, then verify the result | Read/project repository files; write validated changes through a project adapter or explicit export/apply/commit workflow |
| Browser database / JSON exports | Cache or backup/transfer only; not a second primary copy | Cache or backup/transfer only; export alone does not update tracked files |

Both modes must preserve the same [state-machine contract](state-machine.md): stable plan/round/case/environment IDs, frozen round definitions, actor/time/evidence on events and observations, guarded starts/retests/results, prerequisite readiness, outcome routing and annotation history. Reuse validation and projections for the webpage, AI state snapshot, current status, dependency graph and next-test guidance. Issue labels/closure and file names are not substitutes for structured outcomes. Current-library edits affect later rounds; they do not rewrite historical snapshots.

## Default: GitHub Issues

Read [github-issues.md](github-issues.md) for case/round mapping, attachment support and CLI version handling. Store structured definitions and execution records in Issues/comments rather than maintaining two manually edited primary JSON files in Git. An export may be kept for backup, migration or offline review, clearly labelled with its source and capture time; editing it does not update Issues. Verify the actual Issue/comment and evidence URLs after each requested write. A failed or uncertain save remains pending until inspected; do not report browser-cache persistence as a successful remote save.

Initial operation is single-operator and sequential. **Multi-user concurrency and strict remote history/audit protection remain deferred**, as requested. Existing state guards and frozen-history semantics still apply; editable GitHub comments are not tamper-resistant history.

## Alternative: repository-tracked files

Reuse project-owned testing paths and any existing format. Keep **case definitions and execution records in separate files**, for example:

```text
testing/
  plans.json                 # Version/plan metadata and current case definitions
  environments.json          # Stable environment/device identities
  records/
    ROUND01.json             # Round snapshot, attached environment IDs, events and observations
  annotations.json           # Pinned contexts and append-only annotation events, when used
```

This is an illustrative mapping, not a new import format. A project adapter must assemble/validate the complete archive, retain references between these files and split validated updates back into the selected files; the starter does not import this directory layout directly. Preserve per-round source/build and original snapshots even if the current library changes. Preserve recorded observations/events; retests append attempts instead of replacing the previous result.

Resolve the actual repository and paths before applying changes. Validate the assembled state and all affected file references before writing a proposed update. Distinguish browser draft/export, working-tree changes, a Git commit, and a pushed commit in the webpage/handoff; **a local save or download is not an in-repository committed record**. Commit/push only within the task's authorization and verify the resulting commit/path. Failed writes retain the original authoritative files and recoverable pending data. Do not claim multi-file atomicity from separate file writes.

Screenshots and logs may remain on GitHub attachments or the project's existing evidence service, referenced by URL in records; choosing file authority does not require adding binary evidence to Git. Keep stable case/round/environment associations and report missing or inaccessible evidence explicitly. Apply the same attachment version/type checks when using GitHub uploads from this mode.

## Web delivery and mode changes

The bundled [workbench](web-workbench.md) currently implements IndexedDB with JSON import/export only. It has **no built-in GitHub Issues or repository-file persistence adapter**. When delivering a project workbench, connect the chosen source through the project's read/write bridge or provide an explicit validated import/export/apply workflow. Show the selected mode/location and whether changes are pending or confirmed at the primary source. Never imply that the default policy alone implements a backend. Keep credentials outside static webpage assets.

For a requested source switch: retain a backup; map stable IDs, definitions, frozen rounds, environments, observations/events, annotations and evidence URLs; validate the destination projection; verify the transferred data and references; then record the new source selection. Keep the old source as a clearly marked backup/archive. Do not enable automatic bidirectional writes or treat both sources as authoritative during migration. If transfer fails, retain the old authority and pending migration data. Existing local archives remain readable without inventing source metadata or history.
