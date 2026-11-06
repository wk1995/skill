# Fork Repository Maintenance implementation coverage

Prepared before implementation review; updated with executable evidence on 2026-11-05.
The implementation is based on the PRD and technical design in this directory.
Review base: `12851e8c9186755207f89e659ff5b8a21b0036d4` (`origin/main`).
The exact final committed head and clean-tree gate result are reported with the
execution result, avoiding a self-referential commit SHA in this file.
Environment: macOS/Darwin arm64, Python 3.14.6, Git 2.47.1. All destructive probes
use disposable fixtures. No production GitHub write or global Skill install occurs.

## Invariants and entry inventory

All test IDs below refer to `ForkTests.test_<suffix>` in
[the behavioral suite](../../../tests/fork_repository_maintenance_test.py).
Commands are entry points, including their direct invocation and resume forms.
Plan output/preparation, remote publication, isolated integration, and snapshots
are separate boundaries in the same Skill: they share profile and plan schemas,
and ship together so producer/consumer recovery can be tested end to end.

| Invariant / finding | Entry → validation → first mutation | Enumerated scenario / sequence and evidence | Result / failure state | Gap / residual |
| --- | --- | --- | --- | --- |
| Independent default | fork → base/name/selection/identity/path → cache only with refresh, then approved lock/journal | `default_only_creates_independent_default_and_idempotent_resume`, `selected_nondefault_removes_only_owned_bootstrap`, `all_branch_fork_has_same_names_plus_personal_default` | Copied names unchanged; extra personal default points to base; repeat recognizes owned result. | Native GitHub asynchronous object readiness is not exercised live. |
| Base priority | fork planning → entire input set → preparation | `missing_base_rejected_without_state_or_destination`, `default_priority_cannot_be_overridden` | Rejection leaves state and B absent. | No automatic inference when upstream default omitted. |
| Manual scope | plan-sync/sync → frozen source entries and profile → cache/journal | `no_background_sync_and_source_sync_preserves_personal_function`, `selected_sync_does_not_advance_other_existing_source`, `existing_only_all_skips_new_upstream_branches`, `include_new_all_creates_corresponding_sources_only` | Only selected sources move; personal code and checkout stay unchanged; include-new explicitly creates absent names. | No scheduler; all means currently visible upstream refs. |
| Same-SHA role collision | plan-sync and direct sync → profile roles → no mutation on rejection | `new_source_with_personal_name_blocks_even_when_sha_equal`, `unregistered_existing_name_is_not_adopted`, `direct_invocation_revalidates_later_personal_entry`, `direct_forged_existing_only_create_rejected` | Personal/unregistered refs cannot become source writes even with valid recomputed digest. | Explicit migration not implemented. |
| Source provenance / no delete propagation | sync and inspect → recorded baseline/ancestry → approved publication | `source_personal_commits_block_without_overwrite`, `upstream_rewrite_is_rejected`, `source_deleted_is_retained_and_reported` | Drift/rewrite rejected; deleted upstream branch remains in B. | Does not auto-repair divergent histories. |
| Frozen authorization | every apply → JSON/digest/kind/expiry/profile/expected refs → lock | `scope_authorization_and_digest_rejected`, `plan_frozen_against_upstream_advances`, `plan_frozen_against_remote_target_advances`, `apply_cannot_mix_new_parameters_with_saved_plan`, `wrong_direct_plan_kind_never_writes`, `expired_plan_and_unknown_later_profile_record_stop_before_write`, `recreated_destination_cannot_be_adopted_by_editing_plan_id` | Invalid/directly altered plans leave state and refs unchanged. | Digest binds inputs, not caller identity. Expired recovery needs explicit replanning. |
| Strict persistence input | all loaders → duplicate/unknown key and later-record validation → no lock for static rejection | `duplicate_json_is_not_accepted`, `expired_plan_and_unknown_later_profile_record_stop_before_write`, `snapshot_tamper_and_later_manifest_entry_rejected` | Later malformed records are rejected; no partial registration/output. | Schema migration is intentionally unsupported. |
| Fast-forward + compare-and-swap | sync/fork source writer → ancestor + actual expected old → explicit full-ref lease | frozen-target/rewrite tests above; `unknown_send_reconciles_without_republishing_verified_remote` | Updated refs never force-replace divergent source history; successful siblings retained. | Cross-device writes are per-ref, not a multi-ref transaction. |
| Lost send receipt | sync/resume → original/proposed profile and intents → reconcile before another push | `unknown_send_reconciles_without_republishing_verified_remote`, `completed_sync_resume_is_idempotent` | Injected timeout after server update reports uncertain; retry verifies without publishing again. | Fixture injects timeout; no real network failure required. |
| Remote succeeded / local disk failed | sync/resume → frozen original plus proposed state → profile persistence | `remote_success_with_profile_persistence_failure_can_resume` | Remote success survives profile fsync failure; retry records baseline without another send. | Power-loss durability of parent directories is not certified. |
| Identity, containment, target state | fork/save-plan and shared Store/output checks → no_links/related/owned state → refresh/cache | `state_and_output_symlinks_rejected_before_mutation`, `state_overlap_with_source_rejected`, `path_identity_containment_and_existing_checkout_states`, `invalid_plan_output_rejected_before_refresh`, `projectless_parent_directory_allows_external_state_and_checkout` | Same path, case alias substitute, both nesting directions, symlink, file, empty/populated checkout rejected before preparation; user data intact; a projectless parent directory permits sibling external state and checkout. | Native checks run on macOS; hostile concurrent ancestor-directory replacement is outside the same-user ownership model. |
| Namespace aliases | fork/sync/snapshot validation → all names → no Git ref write | `case_and_nested_name_collisions`, collision tests above | Case-only and foo/foo/bar aliases blocked conservatively, independent of current filesystem. | Conservative case folding can reject distinct names on case-sensitive filesystems. |
| Exclusive publication | fork/restore/preserve and saved plans → final identity check → no-replace rename or exclusive link | `exclusive_directory_publication_rejects_racing_destination`, `exclusive_plan_save_does_not_overwrite_racing_file` | Concurrent preexisting output is retained; staging remains available. | Linux renameat2 implementation not run on this macOS host. |
| Archive path self-validation | preserve direct apply/resume → archive ownership and containment before lock/journal | `direct_invalid_archive_root_rejected_before_journal`, `custom_archive_and_snapshot_idempotency` | Invalid root leaves state unchanged; owned external archive works and repeats without replacing snapshot. | No automatic retention/deletion. |
| Standalone snapshot | preserve → frozen refs, full history and manifest → owned staging then independent verification then publication | `snapshot_restores_offline_after_original_repositories_removed`, `annotated_tags_preserve_objects_and_restore_original_names` | New independent object database validates bundle, fsck and every ref; annotated tags remain tag objects. | Git scope only; platform data, LFS payloads and submodule repositories excluded. |
| Offline restore | restore/resume → manifest/bundle digest/entries/default/output → owned staging | offline restore test above, `snapshot_tamper_and_later_manifest_entry_rejected`, `restore_existing_destination_and_nested_snapshot_rejected` | After removing A/B, personal files and default restore; repeat verifies refs; corruption and overlapping/existing output blocked. | No restored remote default claim; no existing-directory overwrite. |
| Snapshot failure retention | preserve → validated owned root → staging | `snapshot_failure_retains_staging_and_recovery_path` | Injected publish failure leaves staging and recovery path; personal branch intact. | Incomplete staging requires explicit inspection, not automatic deletion/reuse. |
| Checkout filter boundary | fork/restore → no-checkout clone/init then disable configured filters → checkout | `global_smudge_filter_is_not_executed_during_clone_or_restore` | Configured canary filter never runs in clone or offline restore. | Approved validation programs can execute project code. |
| Personal merge and conflict continuation | integrate/resume → roles/source/target/baseline/owned candidate → journal and isolated clone | `merge_review_and_resume_keeps_sources_and_requires_validation`, `conflict_resolution_and_repeat_resume_publish_only_personal_result`, `personal_default_name_does_not_collide_with_internal_candidate` | Review/commit/validation precede publication; conflicts can be resolved; repeat safe; private branch names avoid personal names. | Meaningful application assertions remain caller-supplied. |
| Rebase and cherry-pick | integrate → explicit base/picks/roles → isolated candidate | `rebase_creates_new_personal_line_and_never_rewrites_default`, `cherry_pick_review_and_already_applied_idempotency` | Linear rebase creates a new personal line; cherry-pick commits require review; already-applied patches do not duplicate. | Rebase of merge history rejected; complex topology handling deferred. |
| Validation and abort | integrate/resume/abort → same plan/profile/candidate checks → only candidate operation | `validation_failure_never_updates_personal_target`, `conflict_abort_leaves_personal_and_source_untouched` | Failed assertions do not publish; abort preserves original personal/source refs. | Does not undo remote publication or discard completed candidate. |
| Direct integration self-validation | integrate and resume → source role/pick ancestry/protected target checked before lock → journal | `direct_invalid_integration_role_and_patch_rejected_before_journal` | Recomputed plans with personal source, missing patch, missing protected target rejected without state/ref changes. | No lint prerequisite. |
| Personal publication recovery | integrate/resume → owned candidate HEAD plus send intent/readback → record receipt | `integration_lost_receipt_reconciles_without_republish` | Timeout after personal ref update is reconciled; repeated push is forbidden by the test. | If candidate or remote changed independently, recovery stops. |
| Integration stage recovery | resume → persisted stage and candidate → Git operation only if not started | `resume_before_git_integration_starts_and_aborted_patch_cannot_complete` | Interrupted validated stage starts on resume; abandoning staged patches cannot falsely report completion. | Ambiguous partially started integrations retain evidence for explicit review. |
| Dependency failure | all CLI entries → Python/OS/Git; GitHub adapter → gh → no state | `missing_git_and_gh_stop_explicitly`, `missing_gh_blocks_github_request_without_mutation` | Controlled PATH missing Git or gh produces explicit failure without state creation. | Minimum supported Python/Git versions not separately installed/tested. |
| GitHub API contract | Provider create/default methods → current actor → fixture API | `github_adapter_checks_actor_scope_and_default_api_without_network`; official references below | default_branch_only true, chosen destination name, returned ID and default PATCH checked. | This mocks API responses; permissions, protection, redirects and asynchronous readiness remain unverified live. |
| Distributed runtime | existing builders → adapter validation → external artifact | Four adapters; copied test harness outside checkout; direct executable --help plus fork/idempotent resume, protected sync, preserve/offline restore, missing Git/gh and integration recovery cases | All four generated packages are exercised independently with standard-library imports; executable bit verified. | No global installation; other Agent clients themselves not launched. |
| Documentation/catalog/version | bilingual guides/metadata → catalog and adapter validators | `python3 scripts/skill_catalog.py --write`, `--check`; `python3 scripts/agent_build.py --check`; creator quick_validate via uv/PyYAML | English/Chinese catalogs each add exactly one row with language-specific links; frontmatter valid. | Release is experimental, not platform certification. |

## Findings fixed during implementation

The unpublished development tree exposed these defects through review or isolated
fixtures. They were fixed before the implementation commit, so no published
release was rewritten. Each group maps to the tests above and all sibling entries
were checked against its shared invariant.

- Rejecting macOS root-owned /var and /tmp aliases also rejected normal temporary
  directories. Only those fixed system aliases are canonicalized; user symlinks
  remain rejected across state/output/staging paths.
- Treating every working directory as a protected repository blocked normal projectless use from HOME or a project parent. Protection now resolves the actual Git worktree and installed Skill, while still rejecting source/output overlap.
- Using heads refs for snapshot tag objects lost annotated-tag compatibility.
  A/B archive refs now use a custom namespace; snapshot and restore agree.
- Check-then-rename/save could replace a racing target. Directory publication now
  uses OS exclusive rename; new plan files use an exclusive link.
- Directly edited plans could otherwise substitute a reconstructed repository ID at the same address. Shared profile validation binds immutable IDs before sync/preserve/integration writes.
- Source and personal sends needed durable intent/readback reconciliation,
  including the case where the remote succeeded and profile persistence failed.
- Some integration/archive validation originally occurred after journal creation.
  Direct apply and resume now invoke shared preflight before the first state write.
- Integration continuation could skip an unstarted operation or accept an
  abandoned patch result. Stage handling and reviewed-commit postconditions prevent
  false completion; candidate branch naming also avoids personal-name collisions.
- New checkouts must not trigger inherited smudge processes. Generated checkouts
  disable filters before materializing files; controlled caches publish explicit
  full refs rather than relying on candidate push configuration.

## Scope and remaining evidence

New component: fork-repository-maintenance; old version: absent; development
version: 0.0.1; Change-Type initial. This is provisional branch metadata, not a
published release; reassess the release version when merging to the default
branch. No prior portable/state compatibility is claimed and no migration is required. Existing adapter and artifact release versions remain
unchanged: this builds development artifacts and does not publish a new adapter.

The clean committed repository gate and version guard are mandatory final checks;
the execution report records their actual result and exact head. Prior documentation
commits on this branch are included by the origin/main comparison. Legacy tracked
.skill-sync state has no net changes; no newly ignored runtime state is added.

Recursive overlay/exclusion producer-consumer rules are unchanged (N/A for this
Skill); existing builder tests in the full gate still cover them. GitHub live
mutations, Linux native paths/renameat2, Windows, alternate hosting providers,
minimum-version installs, native Agent UI, LFS payload transfer and submodule
backups are NOT RUN and must not be inferred from local success.

Official semantics checked on 2026-11-05: [GitHub fork parameters and asynchronous
creation](https://docs.github.com/en/rest/repos/forks?apiVersion=2026-03-10#create-a-fork),
[API version selection](https://docs.github.com/en/rest/about-the-rest-api/api-versions),
and the [Git/GitHub references in the design](2026-11-05-fork-repository-maintenance-technical-design.md#14-官方依据与待验证范围).
