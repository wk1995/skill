# PR #14 review resolution

Review input: `ddf71d324fe67fd429a794f48094be42feb69f0f`, compared with `origin/main`. The comments contain 16 distinct concerns; repeated independent reproductions are grouped with their original finding below. The fixing commit is identified by the Git history of this document and the final gate run.

## Comment inventory

All discussion links refer to [PR #14](https://github.com/wk1995/skill/pull/14).

| Comment | Resolution | Regression evidence |
| --- | --- | --- |
| [3955345041](https://github.com/wk1995/skill/pull/14#discussion_r3955345041) | Preserve staging on failed install recovery and report both staging and snapshot paths. The independent snapshot already survived; the original “only backup lost” description was too broad. | `test_install_recovery_fault_matrix`: install replace and post-install digest failure, each with successful and failed recovery |
| [3955345049](https://github.com/wk1995/skill/pull/14#discussion_r3955345049) | Validate discovered Agent, same-Agent derivation, real directory, and root ownership before persisting a local location. | `test_unknown_cross_agent_and_outside_location_rejected_before_persist` |
| [3955345054](https://github.com/wk1995/skill/pull/14#discussion_r3955345054) | Validate field types, SHA-256 values, versions, identities, and canonical adapter-relative paths before accepting build records. | `test_invalid_manifest_fields_report_without_aborting` |
| [3955345062](https://github.com/wk1995/skill/pull/14#discussion_r3955345062) | Conflicting registry and metadata identities become unlinked conflicts, not installs of either Skill. | `test_registry_metadata_identity_conflict` |
| [3955360891](https://github.com/wk1995/skill/pull/14#discussion_r3955360891) | Read approval from the PR base and require the plan to remain unchanged in the deletion PR. | `tests/pr-review-guard.sh`: self-approval rejected; previously merged approval accepted |
| [3955360895](https://github.com/wk1995/skill/pull/14#discussion_r3955360895) | Reject future confirmations and timestamp-only evidence; require attributable evidence links reviewed in the prior approval PR. The offline guard validates form; maintainers verify authorship and backup claims before merging approval. | Guard tests for future time and absent evidence; migration documentation defines the trust boundary |
| [3955360899](https://github.com/wk1995/skill/pull/14#discussion_r3955360899) | Validate the install directory before the already-current branch. | `test_identical_symlink_install_rejected_without_state` |
| [3955360901](https://github.com/wk1995/skill/pull/14#discussion_r3955360901) | Document exit 2 for successful mutation with stale report versus strict inventory findings; shell-quote the installed script retry command. | `test_stale_exit_code_and_retry_are_documented_and_executable` |
| [3955360907](https://github.com/wk1995/skill/pull/14#discussion_r3955360907) | Healthy project-only Skills pass strict mode. | `test_healthy_project_only_passes_strict` |
| [3955360913](https://github.com/wk1995/skill/pull/14#discussion_r3955360913) | Adopt the review's documentation option: portable Python validator is authoritative; JSON Schema is informative except for the shared status vocabulary. No Draft 2020-12 execution or third-party runtime dependency is claimed. | `tests/skill-relationship-report-contract.sh`: structural/semantic rejection tests, distributed schema and root compatibility reference, documented boundary |
| [3955459554](https://github.com/wk1995/skill/pull/14#discussion_r3955459554) | Ship validator and schema inside the portable Skill; retain repository CLI/reference compatibility. | `test_installed_skill_can_generate_report`: real Codex and WorkBuddy artifacts, copied away from build output, run with Python `-S` and no optional tools |
| [3955459563](https://github.com/wk1995/skill/pull/14#discussion_r3955459563) | Recognize Agent repair snapshot manifests in rollback, validate identity/path/digest before writing, snapshot the current install, restore only the recorded install. | `test_repair_snapshot_can_be_rolled_back`, `test_rollback_rejects_corrupt_snapshot_before_mutation`; role and location-only registrations, repeated repair/rollback |
| [3955459567](https://github.com/wk1995/skill/pull/14#discussion_r3955459567) | Publish records only after the entire Agent manifest passes; repair independently rejects invalid Agent builds. | `test_corrupt_manifest_cannot_supply_repair` |
| [3955459576](https://github.com/wk1995/skill/pull/14#discussion_r3955459576) | Complete-build counts require the portable source to exist. | `test_report_missing_source_with_existing_builds`: report, remove source, report again |
| [3955459584](https://github.com/wk1995/skill/pull/14#discussion_r3955459584) | Protect discovered local/related roots and registered locations before report output mutations. | `test_output_path_identity_and_containment_matrix`, `test_case_alias_output_protection` |
| [3955459590](https://github.com/wk1995/skill/pull/14#discussion_r3955459590) | Codex adapter 1.1.1 includes `.agents/skills` and retains `.codex/skills`. | `test_codex_official_root_and_legacy_root_share_attribution` |

Additional defects encountered during fixes: explicit `--state-dir` no longer evaluates an unrelated default before parsing; report replacement now retains backups when its own recovery also fails (`test_report_double_failure_preserves_backups`).

## Mutation boundary review

Every changed implementation file was read completely, including the moved validator. The full PR tree inventory was inspected for deletions, renames, modes, generated catalogs, and tracked ignored paths. Legacy `.skill-sync/` has no net change. The root validator and schema are compatibility entry points; their portable implementations are intentionally distributed under `skills/sync-skills/`.

| Entry points | Mandatory validation before first mutation | Failure evidence |
| --- | --- | --- |
| `relationships` / `generate_and_write` / `write_reports` | Build report and contract validation; output identity/containment and file/lock checks → mkdir/chmod → staged report replacement | Protected inputs and registry unchanged; second-file replacement restores the first; double failure keeps backups |
| `atomic_write_report_set` | Regular owned report targets → staging directory | Partial replacement recovery and preserved recovery files |
| `link-location` | Group/path identity, metadata and kind-specific Agent validation → registry write | Unknown Agent, wrong derivation, outside root rejected without registry/snapshot changes |
| `repair-agent-install` | Adapter/target ownership, identity and full trusted manifest → verified snapshot → staged installation | Reject / success / repeated success; install/recovery fault matrix |
| `create_agent_install_snapshot` | Real source, safe IDs, non-overlapping state → snapshot directory | Direct same-path and both nesting directions rejected |
| `atomic_install_build` | Real separate source/target and containment → staging → metadata/digest verification → first target replace | Same-path, alias, nesting, file, empty and absent target; recoverable failures retain original data |
| Agent snapshot `rollback` | Manifest identity, registered target, real paths and digest → undo snapshot → atomic installation | Corrupt snapshot rejected before writes; repair → rollback → repeated rollback preserves unselected roles |
| Ordinary `link`, `convert`, `sync`, `rollback`, `rename` | Existing identity/role validation before persistence; rollback now validates all selected snapshot roles before creating its pre-rollback snapshot | Existing path-safety/sync-ID suites; stale-report test confirms completed mutation remains saved |
| `migrate-state` / `migrate_state_tree` | Same-path/nesting and complete source/target manifest checks → staged copy | Existing malformed/legacy state, modes, missing inputs, aliases, idempotency, copy failure, absent optional tools |
| `agent_build.build` | `validate_all`, safe output and replacement ownership → staging/build → replacement | Adapter suite plus recursive exclusions, reserved override paths, force/rebuild idempotency |
| PR guard tree/ignore helpers | Resolve exact Git commits → isolated temporary checkout | Base/head merge tests, protected-state and ignored-file cases; missing Git fails closed |

## Validation scope

- The 20 new regression methods run through `tests/skill-relationship-regressions.sh`; guard and contract tests add migration-approval and contract-boundary regressions.
- A selected set of 10 regression methods was also run against the original review head in a temporary archive: it failed with 8 assertions and 5 errors across subcases, confirming that the tests distinguish the fixes from the original behavior.
- Filesystem checks ran on macOS with native case-insensitive identity; a controlled samefile substitute is included for case-sensitive runners. Nested transient exclusions are checked in generated outputs. Existing adapter tests reject nested reserved append fragments.
- The full gate must run on the clean committed tree: `bash tests/pr-review-gate.sh origin/main`. It also executes all `tests/*.sh`, including build, catalog, migration, contract, and regression suites. Gate results and exact final head are reported in the completion message.
- [Official Skills documentation](https://learn.chatgpt.com/docs/build-skills) was fetched on 2026-09-08; it lists `$HOME/.agents/skills`. The former developer documentation URL redirects there. Product scope is Codex adapter 1.1.1; legacy directory support is retained explicitly.
- Native Linux/Windows and actual Agent UI loading were not exercised locally. Tests include case-sensitive substitutes and standard-library-only subprocesses, but these do not prove client UI behavior. Live collaborator evidence verification is intentionally a maintainer step in the separate approval PR. Power loss, concurrent hostile filesystem replacement, and real cross-device failure were not simulated; staging is placed beside each target to avoid cross-device rename during normal installation.
