# Preserve and extend an existing project workbench

Use these procedures when the existing project supplies capabilities beyond the bundled starter. Reuse its adapters and authoritative data rather than replacing the application wholesale. The starter does not include ADB discovery, historical identity mapping, a live WebMCP registry, GitHub PR-diff preparation or local screenshot storage. Implement and verify a requested adapter before reporting it available; instructions alone do not add a working UI or API.

## Adoption and capability checks

Record the actual source repository/branch, running service directory, authoritative data paths, schema, environment identity, evidence destination and history policy. The visible page can run from a different worktree than the terminal. Keep these identities separate from the tested package's source commit.

For each requested integration, trace UI/AI/CLI entry point → shared validation → first write → read-back. Verify it with disposable data. Keep existing guards and observe the selected source mode; host tools and browser drafts are not additional primary sources. Mark an absent or unverified adapter pending and retain supported independent work.

Custom schemas require an explicit mapping of definitions, observations, environments, Issue associations, conclusions and unknown legacy fields. Preserve unmapped source data. The bundled unified-format validator rejects unsupported archives; neither changing `schemaVersion` nor copying only recognized fields is a migration. Update validators, writers, import/export and UI/AI consumers together when extending a schema. Do not add the configuration choices in this guide as unrecognized archive fields.

## ADB device discovery and registration

When Android testing calls for webpage device discovery, provide a loopback service adapter and an explicit scan/register UI. Reuse an existing project implementation when available.

- Discover candidates using fixed ADB commands and read only the properties needed for model, manufacturer, OS/build and relevant runtime configuration. Return offline/unauthorized/missing-tool conditions clearly; do not fabricate a registered device from incomplete properties.
- Resolve the physical identity on the service. USB and wireless endpoints for the same phone should map to one identity; an endpoint or shared model name alone is insufficient. Keep raw serial numbers and private identity material out of browser responses and tracked test data.
- Scan responses expose a bounded candidate selector. Before registering the selected candidate, read it again and confirm it is still connected and authorized. Register the resulting server-owned configuration, then explicitly attach/select it for the round.
- Reuse profiles across rounds, but retain each observation's original configuration snapshot. A system upgrade is a configuration change, not permission to relabel past results. Enforce the same registration and round membership checks on single/batch saves and direct AI calls.
- Discovery does not install a package, change developer settings or operate the phone. Those actions follow the requested testing scope and actual live device state; see [android-example.md](android-example.md).

Verify USB/wireless deduplication, two identical models remaining distinct, disconnect between scan/register, unauthorized devices, stale configuration, tool timeout and missing ADB using mocks or disposable fixtures.

## Historical environment identity associations

When importing records from another workbench, support explicit confirmation that an imported identity belongs to an already registered environment. Show both original and target configurations before accepting the association.

Store the association separately from immutable observed device/environment snapshots. Require a known source identity and a target attached to the current round; reject incompatible OS/build configurations. Never infer sameness from a model label, replace execution times or assign an unknown legacy device to a phone by guesswork.

Keep mappings local to the selected archive/round revision and preserve historical projections. Handle repeated mappings idempotently, avoid alias chains/cycles, and retain a different phone's unresolved failure. After association, calculate current grouping, conclusions and next-round selection through the same mapping logic; previously saved conclusions become stale when their supporting grouping changes.

The bundled schema has no historical identity-mapping field or editor. An existing project's mapping remains a project adapter until its format and all consumers are explicitly supported. Export/import must retain original identities and mappings; do not rewrite observation IDs to fit the new machine's registry.

## Live AI and WebMCP operations

If the host offers a compatible tool registry, expose actual project operations through it. Feature-detect availability; keep normal webpage operation and read-only AI snapshot export usable when it is absent. Do not invent a browser API, native annotation transport or automatic website-to-chat channel.

Useful operations include reading workspace identity, listing/getting cases and records, opening a case, preparing the next round, submitting change analysis, and recording an actual result. A selected local screenshot adapter may also expose upload-and-associate for a draft.

All mutation tools use the same model and service guards as UI/direct calls: source, round, archive/save revision, frozen case revision, registered environment, legal workflow transition and actual evidence. A context read is required before a write. Historical scopes stay read-only. Navigation and analysis never start a test or fabricate a result.

Keep read-only tools distinct from mutations. Upload success means bytes are stored/associated, not that a test passed or its result was saved. Preserve drafts and their environment binding after rejection; reject cross-round, stale or ambiguous requests atomically. Disposing/re-registering tools must not leave duplicate active writers.

Verify unavailable-registry fallback, registration failure cleanup, stale/wrong-round/environment rejection, single/batch consistency and upload without result creation. Never use a real product record merely to test the integration.

## PR difference preparation

Use a project GitHub adapter to read the actual PR base/head and compare the previous tested source with the proposed head; use PR base for a first round without a tested baseline. Verify repository and version scope. Preserve the source/build actually installed independently of the current PR head.

Read complete changes, including renamed/deleted files and affected callers. Empty/truncated patches, API limits or divergent history need a complete comparison or explicit review, not an empty-diff assumption. Bind the review to the PR, exact base/head, previous round/revision and current definition/classification baseline.

After meaningful analysis, save concrete cases with their change reasons and changed-file references. Revalidate the context before creating the round; head, prior results or library edits invalidate stale preparation. Do not invent change cases when the commits are identical. Always retain the failure/smoke/change/optional-unfinished ordering and current-library rules in [test-rounds.md](test-rounds.md), plus declared dependencies and branch targets.

The starter accepts declared change selections but does not fetch or analyze live GitHub PR diffs. An AI tool or button called "prepare next round" must report whether the real comparison and analysis are ready; reading filenames alone is not completed behavioral analysis.

## Local screenshot adapter

Issue attachments remain the default evidence destination for new projects. Preserve a working local screenshot workflow when explicitly chosen or already recorded by an existing project. Local evidence is an optional project integration, not another authoritative test-data mode and not an implemented starter attachment feature.

Provide manual upload, thumbnail/full-image preview and, when requested, AI upload/association. Choose and document project size/count/type limits rather than imposing one application's values on all projects. Validate actual bytes, supported format, bounds, names and content digest on the service; never accept arbitrary browser-supplied filesystem paths.

Keep bytes in the selected server-side store and metadata in the record/draft. Bind upload association to the correct round/case/revision, preserve existing feedback, deduplicate by content and verify referenced files before saving. Uploading, associating, recording a result, committing and publishing remain distinct outcomes. Missing old files show "附件未关联" or an equivalent explicit missing-evidence state, without fabricated previews.

Full local-archive export/import must preserve and validate associated bytes, or explicitly identify the archive as remote-reference-only. A migration to Issue attachments requires an authorized upload and returned usable links; putting a Git blob URL inside Issue Markdown is a repository-hosted image, not an Issue attachment upload. Private evidence retains its access restrictions.

When local cleanup is requested, verify the retained remote evidence first, replace all affected references and confirm read-back/export before deleting only the scoped files. Do not assume linking an Issue transfers bytes or authorizes deleting unrelated logs, packages or capture directories. Do not rewrite Git history merely to clean current working-tree files. Reconfirm conclusions if evidence associations change their supporting revision.

## Project storage and conclusion presentation

Honor the project's selected file layout. "One file per round" can contain definitions, current records and the supporting conclusion without creating a new file on each save; it is separate from whether individual attempts/events are retained inside that file. Do not replace it with the starter's generation layout automatically.

If the user explicitly chooses current-results-only storage without historical attempts, preserve that narrower contract. Do not invent missing events or claim managed append-only replay. Keep unresolved failures visible through incomplete retests, and do not interpret compaction as a passing result. Adopting managed workflow history needs an explicit project migration; never strip events from an existing managed archive to make it current-results-only.

A requested conditional conclusion tab appears only when that selected round/revision has a persisted conclusion. No conclusion means hide the tab or show the project's explicit empty state, not a fabricated pass. Preserve its deep link across reload; switching to a round without a conclusion falls back to a valid view. A new observation, environment mapping or supporting revision makes the earlier conclusion visibly stale. Display the saved scope, defects and skipped/incomplete conditions independently of list filters.

Keep working-tree saves, explicit data commits and pushes distinguishable. Include the conclusion with its supporting records in a requested commit. These storage/UI choices do not change the bundled archive schema or automatically implement a custom file adapter.
