# Focused-round correction review (0.0.7)

Change baseline: `6fcb95ba12b8ff6605d52854add29a5ca5c30a1f`.
PR integration base: `12851e8c9186755207f89e659ff5b8a21b0036d4` (`origin/main`).
The final committed head and clean-tree gate result are reported at handoff;
this ledger travels with that head rather than asserting a self-referential SHA.
Environment: macOS, Node 23, system Google Chrome through Playwright, disposable
Git repositories, fake GitHub API and unique browser fixture databases.

Scope: the issue #40 correction and all model/UI/import/projection consumers of
round selection. Historical review claims for the rest of the original branch
are not treated as fresh full-PR coverage. There are no live Issue writes, device
tests, installation changes, publication or new external product claims.

## Invariants and coverage ledger

| Invariant / finding | Entry point → validation → first mutation | Scenarios and evidence | Result / residual boundary |
| --- | --- | --- | --- |
| Explicit scope; no implicit full plan, smoke or failures | `createRound` → whole archive + source/IDs/revision + dependency closure → cloned proposed archive; `previewRoundSelection` read-only | `focused-rounds.test.mjs`: 2 selected of 49, unrelated previous failure/smoke, original snapshots unchanged | PASS; sources describe selection, not proof of an external Issue/diff analysis |
| Outcome routes never extend scope | create → prerequisites only; `nextTest`, `projectFlow`, `exportAI` → frozen IDs → no write | 49-node branch chain, only C1 selected; one graph node/summary pair; outside route unavailable; no phantom blocked/untested pairs | PASS; explicit new selection required for an external target |
| Prerequisite closure and provenance | create/import → requested IDs + recursive prerequisites + exact final IDs → cloned archive | Recursive C1→C2→C3, deduplication/order/reasons; plan edits retain old snapshots; forged extra IDs reject | PASS; historical selection-free archives keep old smoke/branch validation |
| All callers validate before saving | direct create/preview; import/plan edits; single/batch results; annotations → shared whole-state validator → proposed copy | Existing workflow/dependency/import/annotation suites plus malformed/empty/duplicate/unknown/stale/unsupported source tests | PASS; no UI-only safety boundary |
| Creation retries do not duplicate rounds or rewrite history | `createRound` → validate input and compare immutable definition → return existing state or append | Same ID/definition repeat; conflicting name/definition rejection | PASS; stale plan revisions reject rather than silently reinterpret |
| Scope agrees with statistics/conclusion | `testConclusions` / AI export → validated frozen round → read-only pair projection | Focused pairs counted on both source reloads; historical unrelated failures stay in their original round | PASS; case/environment applicability remains the existing all-pairs model |
| UI preparation and confirmation match persisted scope | form → preview exact IDs/additions/exclusions → confirmation → shared model → source revision guard → source write | `browser-focused.mjs`, both primary modes: preview writes nothing, ID changes reset confirmation, stale source rejects, reload invalidates confirmation, 49-case full regression explicit | PASS; remote changes require refresh/repreview; no distributed concurrency claim |
| UI confirmation cannot be re-enabled by busy-state restoration | reload/save → render invalidates prepared scope → busy cleanup reapplies confirmation guard | Browser stale-save → reload sequence (found during review and fixed) | PASS; unsaved form values retained |
| Source writes preserve authority on rejection | `GitHubSource.write` / `FileSource.write` → `proposed` revision/whole-state/history → first comment or snapshot write | Focused source roundtrip, bad scope rejected, unchanged read-back, repeated write no extra publication; existing source failure/retry tests | PASS; fake API only, no live account evidence posted |
| Old archives stay intact; new reader compatibility explicit | import → old rules when selection absent; old 0.0.6 reader probe on focused archive | Old archive import/repeat; old reader rejects smoke-free focused round | PASS with limitation: all shared readers/writers must upgrade; direct callers migrate to explicit selection |
| Existing UI responsibilities remain valid | browser fixtures → same store/model; presentation only for navigation | 9 browser fixtures: persistence 5, UI 3, annotations 8, workflow 8, routing 9, dependencies 7, flow 9, separation 11, focus 5; `browser-primary.mjs` on both modes | PASS; fixtures open hidden annotation panels and inspect saved records in record view |
| Version 0.0.7 first-merge history is constrained | version guard → committed metadata + explicit Initial-Version owner chain → no mutation | `test_first_merge_history_requires_explicit_validated_owner_chain`: all 3 owners, PR/push, valid/repeat/rejected/corrected; malformed source/version/date/chain declarations | PASS; user explicitly authorized development-history rule; does not override base comparisons for existing components |
| Distribution matches source | adapter checks → actual isolated build → Node tests from built files outside checkout | Codex, dsh, workbuddy and workbuddy-ai, full Node suite; browser/CLI files included | PASS; no machine-wide Skill installation or sync changes |
| Path/dependency/recursive rules | no new filesystem write entry point; inherited source suite rerun | Existing source tests cover containment, case/symlink aliases, failing hooks, missing Git/gh, stale updates and partial publication; validator tests omit Git/gh/network | PASS inherited coverage; no new deletion/rollback operations, so new destructive recovery matrix N/A |
| Docs/catalog coherence | Skill/EN/ZH references → generated catalogs; schema contract updated with selection | `skill_catalog.py --write/--check`, `agent_build.py --check`, syntax and diff checks | PASS; original data-format integer versions retained, caller/reader migration explicitly documented |

## Regression proof and review expansion

The six new focused-round tests fail on an isolated checkout of `6fcb95b` and
pass on the corrected implementation. The initial implementation was also
independently reproduced expanding a single root into 49 branch targets. The
fix expanded across create, validation/import, flow projection/rendering, next
advice, AI export, UI confirmation, source persistence, summaries and their tests.

New tests exercise rejection, successful creation/save, idempotent retry and
unchanged-state failure. The complete Node suite includes 94 tests. The clean
committed final check must use `bash tests/pr-review-gate.sh origin/main`; any
failure is a completion blocker, not a waived check. Final verification artifacts
and exact commit identities are provided with the handoff.
