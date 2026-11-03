#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

# Explicit test IDs make a removed/renamed regression fail instead of silently
# selecting zero tests. The required PR gate also discovers this script.
run_group() {
  local label="$1"
  shift
  echo "::group::$label"
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/skill_relationship_regressions.py" "$@"
  echo "::endgroup::"
}

run_group "F1: report and repair freshness" \
  ReviewRegressions.test_report_and_repair_agree_on_input_freshness \
  ReviewRegressions.test_legacy_build_evidence_requires_rebuild_in_report_and_repair \
  ReviewRegressions.test_later_invalid_input_evidence_preserves_all_repair_state

run_group "F2: artifact and snapshot execute-bit evidence" \
  ReviewRegressions.test_artifact_execute_bit_corruption_rejected_before_repair_mutation \
  ReviewRegressions.test_snapshot_mode_corruption_rejected_before_rollback_mutation \
  ReviewRegressions.test_later_invalid_mode_record_cannot_supply_partial_builds \
  ReviewRegressions.test_added_execute_bits_and_invalid_snapshot_modes_are_rejected

run_group "F3: recursive exclusions across Agent and portable copies" \
  ReviewRegressions.test_recursive_transients_are_excluded_across_build_report_repair_and_rollback \
  ReviewRegressions.test_recursive_exclusions_in_portable_convert_sync_and_rollback

run_group "F4: publication and recovery failures" \
  ReviewRegressions.test_builder_publication_failure_retains_previous_artifact \
  ReviewRegressions.test_builder_failed_recovery_preserves_both_artifacts \
  ReviewRegressions.test_builder_backup_move_failure_and_first_publication_failure

run_group "Distributed commands: all adapters, stdlib only, missing Git" \
  ReviewRegressions.test_new_commands_run_from_every_distributed_adapter_without_git

echo "PASS: all four Skill provenance findings and distributed commands"
