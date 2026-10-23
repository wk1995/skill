# Two authoritative data-source modes

Use the [unified case/record/summary format](data-format.md) for required fields, references, source mappings and validated examples; both sources reconstruct the same archive.

Select the source before creating or updating test data. For a new project without a recorded choice, use **`github-issues` (default)**. Use **`repository-files`** when explicitly selected by the user or the existing project configuration. Preserve an existing source until an explicit switch; a connection failure never selects the other mode automatically. Record the choice and source location in the project's existing workbench configuration or test documentation. These names describe the workflow contract; they are not new fields supported by the bundled archive parser.

| Contract | `github-issues` — default | `repository-files` — explicit alternative |
| --- | --- | --- |
| Authority | Selected GitHub host/repository and mapped Issues/comments | Selected repository and Git-tracked test files |
| Case library | Case-definition Issues with stable case IDs and structured definitions | Definition files, separate from execution records |
| Execution history | Round Issues with frozen definitions, source/build, environments, and structured event/observation comments | Round/record files with the same frozen context and append-only events/observations |
| Evidence | Attach screenshots/logs to the relevant Issue/comment and store the returned URLs | Append Issue associations to records; screenshots/logs live in the linked Issue, outside Git |
| Webpage | Read/project Issues; send validated mutations through a project adapter, then verify the result | Read/project repository files; write validated changes through a project adapter or explicit export/apply/commit workflow |
| Browser database / JSON exports | Cache or backup/transfer only; not a second primary copy | Cache or backup/transfer only; export alone does not update tracked files |

Both modes must preserve the same [state-machine contract](state-machine.md): stable plan/round/case/environment IDs, frozen round definitions, actor/time/evidence on events and observations, guarded starts/retests/results, prerequisite readiness, outcome routing and annotation history. Reuse validation and projections for the webpage, AI state snapshot, current status, dependency graph and next-test guidance. Issue labels/closure and file names are not substitutes for structured outcomes. Current-library edits affect later rounds; they do not rewrite historical snapshots.

## Default: GitHub Issues

Read [github-issues.md](github-issues.md) for case/round mapping, attachment support and CLI version handling. Store structured definitions and execution records in Issues/comments rather than maintaining two manually edited primary JSON files in Git. An export may be kept for backup, migration or offline review, clearly labelled with its source and capture time; editing it does not update Issues. Verify the actual Issue/comment and evidence URLs after each requested write. A failed or uncertain save remains pending until inspected; do not report browser-cache persistence as a successful remote save.

Initial operation is single-operator and sequential. **Multi-user concurrency and strict remote history/audit protection remain deferred**, as requested. Existing state guards and frozen-history semantics still apply; editable GitHub comments are not tamper-resistant history.

## Included webpage adapters

Requires Node.js18+; GitHub mode also requires an authenticated local `gh`, repository access and Issues enabled. File mode requires Git and an existing repository with a HEAD commit. Copy both `scripts/` and `assets/workbench/` together, preserving their relative layout. Start from the Skill directory or use the actual absolute script path:

```bash
# Default mode: GitHub Issues. Replace OWNER/REPO with the confirmed target.
node scripts/workbench-server.mjs --repo OWNER/REPO
# Explicit alternative: save to a selected repository; commits stay a separate action.
node scripts/workbench-server.mjs --mode repository-files --repo-root /absolute/project --data-dir testing/testflow
```

Open the printed loopback URL. The banner shows the selected repository/source, initialization state and Git commit status. **Initialize this source** explicitly creates its empty workspace; existing workspaces load without replacement. Import an actual plan/archive, then use the normal case/round/environment/result/annotation controls: they read and write the selected source. Refresh reloads that authority; it never silently switches to browser data. An unconfigured static web server does not substitute IndexedDB. Optional `--workspace <lowercase-name>`, `--port <number>` and GitHub `--hostname <host>` / `--issue <index-number>` select a known scope; use `--issue` when discovery finds ambiguous indices. Preserve the chosen source configuration for future runs.

The service binds127.0.0.1 only, validates Host/origin and requires a session header on mutations. It exposes no token to the browser and does not serve arbitrary repository files. It serializes its own source reads and writes and rejects stale revisions, malformed state and history rewrites before source writes. HTTP archive requests are limited to16MiB; keep screenshot/log bytes in attachments and store their URLs. These local controls are not a distributed transaction/locking guarantee. Keep the existing gh account, repository and requested write scope; changing the gh actor while connected rejects writes. Do not expose this bridge on the network.

### GitHub persistence

One index Issue per workspace points to the published source generation. Case Issues are keyed by plan/case, and round Issues by round ID. Full definitions and round snapshots/events/observations are stored as append-only structured JSON comments; annotations and derived conclusions also live in comments. Documents split into bounded chunks with ordered IDs and a digest. The index's manifest references the exact published comments; it changes only after all new documents read back successfully. Reused unchanged documents retain their references. Issue closure/labels never determine the testing outcome.

An interrupted save may leave unreferenced comments or entity Issues; the previously published workspace stays authoritative. Do not delete such data automatically or call the interrupted save successful. On an uncertain final index write, inspect/read back the index rather than blindly repeating it. The initial implementation uses whole-entity snapshots, not one human-readable comment per individual event; the structured round document retains every event and observation. Read the exact referenced chunks, not an arbitrary latest comment. No screenshot/log upload is implied by saving a record: attach through the documented media/browser route and record the returned URL.

### Repository file persistence and explicit commits

The default file layout is:

```text
testing/testflow/
  owner.json
  workspace.json                # Atomically published generation pointer
  snapshots/<generation>/
    definitions.json            # Plans/cases, environment profiles, schema/revision
    records.json                # Frozen rounds, execution events and observations
    annotations.json            # Pinned contexts and annotation events
    conclusions.json            # Revision-bound, machine-readable test conclusions
```

Definitions and execution records are separate files. Each save validates the entire proposed state and retained history, writes a fresh generation, then atomically replaces the pointer. Readers validate all referenced data and recompute conclusions for agreement. Original generations remain recoverable. Failed staging can leave pending files; preserve/inspect them, and never publish or commit an incomplete generation. Paths must stay inside the actual repository root; foreign nonempty directories, `.git` paths and symlinks reject. The service does not interpret this layout as a legacy plan import.

A successful **Save** creates working-tree changes only. **Commit test data** explicitly stages/commits the owned data files, including definitions, records and conclusions, using the repository's configured Git identity and current branch. Other staged or working-tree files stay outside that commit. Git diagnostics disable optional index writes; literal pathspecs and cleared Git-location environment variables keep operations bound to the selected repository. Missing identity, detached HEAD, ignored files, stale state or Git failure is reported with the pending data retained; no force-add or push is performed. Check the displayed commit/head separately from a working-tree save. Do not describe ignored/untracked data as committed.

Screenshots and logs live directly in the linked Issue. File mode commits structured associations and test conclusions; the webpage has no separate attachment entry. Existing evidence paths/URLs remain readable for compatibility.

## Record-to-Issue associations

Both source modes support the optional, append-only `round.issueLinks` collection; file mode persists it inside `records.json`. Each association targets one immutable observation in its owning round, so the record supplies exact case/environment/package context. One record can link several Issues, and one Issue can be shared across records. Repository/host are included in each full HTTPS Issue URL, including cross-repository or Enterprise links. URLs are normalized; PR URLs, unsafe schemes, credentials, queries and malformed Issue paths reject. Fragment links normalize to the parent Issue. These are declared references, not verified Issue identities or attachment content.

```json
{"id":"link-unique-id","observationId":"observation-id","url":"https://github.com/OWNER/REPO/issues/123","actor":"actual-operator","createdAt":"2026-10-23T09:00:00Z"}
```

For new records, the webpage saves observations and associations atomically through `recordBatch(state, roundId, observations, issueLinks)`. Failed results need actual notes plus a linked Issue or legacy nonempty `observation.evidence`. New UI records keep that legacy field empty and use associations. Other outcomes may omit Issues. Adding an association to an existing or completed record uses `linkRecordIssues(state, roundId, links)`: validate all IDs/URLs/operator/times before persistence, retain original observations/events, and treat exact event-ID retries as no-ops. Import unions associations by immutable ID; rewrites conflict, and source updates reject removal. Older archives without the optional collection remain valid and their saved conclusion representation remains unchanged.

Open the linked Issue to attach screenshots and logs directly through GitHub's supported UI/CLI route. There is no webpage attachment upload entry or media copy into Git. Record cards, copied results and current/unresolved-failure conclusion references expose the Issue URLs; conclusions retain the original test verdict. File saves and explicit commits include these associations along with records/conclusions. Linking alone does not call an Issue API, create/comment/close an Issue or change its status; in Issues-primary mode the usual workspace save still writes its structured source documents. Creation, attachment upload or remote comments require their own authorized action. Do not infer that a linked Issue exists, is accessible, contains evidence or is closed from this reference.

## Test conclusions and legacy browser data

The webpage's **Round test conclusion** and AI `projection.conclusions` use the shared `ci-package-test/conclusions` contract, tied to `archiveRevision`, round/source/version and case/environment outcomes. Known failures remain failed through incomplete/skipped retests; blocked/partial coverage is explicit. Only a completed round whose every execution is a valid pass concludes passed; skips and missing coverage remain incomplete. Legacy rounds are labelled legacy without fabricating a managed conclusion. Conclusions are persisted and checked alongside their supporting records in both sources; file mode commits `conclusions.json` as well. These conclusions describe the recorded tests, not release approval.

Existing IndexedDB databases are never silently migrated or cleared. For an explicit local preview/old-data export, serve `assets/workbench/` with a static server and open `?local=1` (the original database) or the existing `?workspace=<name>` URL (a named database). The banner states browser preview and no primary-source sync. Export first, restart with the chosen source bridge, explicitly initialize the destination if needed and import/verify the archive. Browser exports remain backups; primary writes go through the connected source. Node/gh/Git setup errors do not create an automatic file/IndexedDB fallback.

For a requested source switch: retain a backup; map stable IDs, definitions, frozen rounds, environments, observations/events, annotations and evidence URLs; validate the destination projection; verify the transferred data and references; then record the new source selection. Keep the old source as a clearly marked backup/archive. Do not enable automatic bidirectional writes or treat both sources as authoritative during migration. If transfer fails, retain the old authority and pending migration data. Existing local archives remain readable without inventing source metadata or history.
