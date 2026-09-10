# Change and Recovery Workflow

Use for migration, backfill, index rollout, restore, or maintenance. Apply the engine-specific reference too. This workflow distinguishes preparing files from executing changes; it does not grant additional execution authority.

## Prepare a Reviewable Change

Record the target/environment, engine/version, current schema state, intended invariant, exact SQL or migration entry point, expected locks/rebuilds, available disk, and verification. Reuse the repository's migration runner and naming/order conventions; inspect its transaction wrapping and generated SQL.

For an offline request, edit and validate migration files and provide the execution plan. For authorized live work, verify target identity and effective role immediately before execution. Resolve ambiguous environments before connecting. Use existing credentials without copying secrets into scripts, history, or reports.

Set workload-appropriate stop conditions before live execution: timeouts, lock wait, error rate, write latency, replication lag, or disk headroom. Choose limits from the user's availability needs and observed baseline; do not invent universal thresholds. If missing facts prevent a safe execution decision, complete the offline work and identify the specific blocker.

## Preserve Application Compatibility

For changes requiring a staged rollout:

1. **Expand:** introduce an additive schema compatible with currently deployed readers/writers. Check whether a default or type change rewrites existing data in this engine/version.
2. **Backfill:** use bounded batches with a stable key, durable progress, and a retry-safe predicate. Account for writes arriving during the backfill through the application's migration strategy; define how omissions and races will be reconciled.
3. **Verify and switch:** check row counts plus domain invariants, NULL/duplicate violations, sampled or full comparisons as appropriate, and behavior of both application versions. Validate new read/write paths and replication effects.
4. **Contract:** remove old fields/paths only after dependent applications and rollback windows no longer require them. Treat destructive removal as its own scoped action.

Simple changes need not use every stage. Before adding a constraint, check existing violations and how concurrent writes remain valid; before a type conversion, check range, precision, encoding, timezone, and failed-conversion behavior.

## Execute and Observe

- Run the selected migration once through its normal runner. Check applied-version records and actual schema/data state rather than trusting a local filename or an `IF NOT EXISTS` clause to establish equivalence.
- Apply related changes in the smallest coherent unit. PostgreSQL transactions can help for supported operations; concurrent index creation and some maintenance need separate handling. MySQL implicit commits mean a transaction wrapper is not a rollback plan for DDL.
- Measure correctness and relevant performance after each step. A successful command exit is insufficient when an index is invalid, a constraint remains unvalidated, or application errors/lag rise.
- On timeout, lost connection, or runner failure, inspect server operation state, migration bookkeeping, and resulting schema before retrying. Do not run a second backfill or DDL job blindly.
- Cancellation or termination can itself have consequences. Identify the operation and inspect engine-specific cancellation/rollback behavior before acting within the user's authorization.

## Recovery Is an Operation, Not a Promise

Name the recovery method and its limits before a risky change: transaction rollback where supported, a tested reverse migration, a forward repair, or restore plus cutover. A reverse migration cannot reconstruct dropped values without a preserved copy; restoring a backup can lose later writes unless replay/reconciliation is available.

For a restore, verify backup identity, integrity and consistency method, engine/tool compatibility, required WAL or binary logs, and recovery target. Restore to a separate target by default; check data invariants and application access there before any authorized replacement or traffic switch. State observed recovery time and possible data loss against the requested RTO/RPO when provided.

After failure, preserve recoverable backups and the observed state. Record completed/pending steps, data verification, running operations, and the specific next recovery action. Do not automatically delete artifacts or retry destructive operations to make the runner appear clean.
