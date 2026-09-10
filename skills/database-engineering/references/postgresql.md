# PostgreSQL Engineering

Use for PostgreSQL schema, query, RLS, and operational tasks. PostgreSQL 17 is the documentation baseline; verify the actual server and extension versions before using version-dependent features. Compatible managed services can restrict extensions, privileges, or operations.

## Schema and Access Paths

- Express domain invariants with appropriate keys, foreign keys, uniqueness, NOT NULL, and CHECK constraints. A CHECK can accept NULL; combine it with NOT NULL when the domain requires a value. Decide explicitly whether multiple NULLs under uniqueness are valid (`NULLS NOT DISTINCT` needs PostgreSQL 15+).
- Choose identity integers or UUIDs from distribution, external identifier, and storage requirements. Use exact numeric types for exact decimal quantities; use `timestamptz` for instants and a separate timezone identifier when local scheduling semantics matter. Do not blindly convert business-local timestamps.
- Normalize relationships unless a measured access pattern justifies duplication. Use JSONB for genuinely flexible attributes, with constraints and indexes for the paths actually queried; do not move relational invariants into unvalidated JSON.
- Primary/unique constraints supply indexes; referencing foreign-key columns are not automatically indexed. Assess their joins and parent update/delete paths. Index selection depends on workload: B-tree for common equality/range/order paths, GIN for appropriate JSONB/array/text operators, BRIN when physical order correlates with a large dataset.
- For multicolumn indexes, consider equality, range, ordering, selectivity, and version-specific planner behavior together. Partial indexes require a predicate the planner can establish from the query; parameterized plans may not qualify. INCLUDE can support index-only access, but visibility checks may still require heap visits.
- Justify partitioning through pruning and lifecycle management, not a fixed row-count threshold. On partitioned tables, check uniqueness/primary-key restrictions involving the partition key and the application's cross-partition identity requirements.

## Query Diagnosis

Start with plain EXPLAIN. If execution and load are acceptable, capture `EXPLAIN (ANALYZE, BUFFERS)` for representative parameters. Compare actual and estimated rows, loops, rows filtered, sort spills, buffers, and elapsed time. Distinguish planner cost from milliseconds and account for cache state and concurrent load.

When available, `pg_stat_statements` helps prioritize workload impact. PostgreSQL 17 uses `total_exec_time` and `mean_exec_time`; inspect the installed extension view rather than using old `total_time` examples. Metrics are aggregate, may have reset, and can contain sensitive SQL text.

Before changing indexes or memory, test the cause: data skew, stale statistics, correlated predicates, excessive result volume, repeated application calls, or lock waits. `work_mem` can multiply across plan operations, parallel workers, and sessions; prefer a scoped experiment over a global increase.

Compare rewritten query results, including duplicates, NULLs, ties, and timezone boundaries. Keyset pagination needs a deterministic ordering and a matching cursor, often including a unique tie-breaker; it is not a transparent replacement for arbitrary page-number navigation.

## RLS and Tenant Isolation

Review grants and policies together. Test as the actual application role, with the actual session/JWT context where relevant: cross-tenant reads, inserts, updates, and deletes; missing identity; and attempted tenant-key changes. Distinguish `USING` row visibility from `WITH CHECK` restrictions on new row values.

Superusers and BYPASSRLS roles bypass row security; table owners normally bypass it unless forced. Tests using an elevated connection do not establish application isolation. Check combinations of permissive/restrictive policies, security-definer functions, views, and connection-pool session context. Supabase-specific authentication helpers are not portable PostgreSQL built-ins.

## Operations and Change Hazards

- Inspect connection state and waits before increasing limits. Bound pools across all application instances and preserve operational headroom. With transaction pooling, check assumptions about session state, temporary objects, advisory locks, and the pooler's supported prepared-statement behavior.
- For deadlocks or long transactions, identify blocking relationships and transaction ownership before cancellation or termination. Retrying a transaction requires considering external side effects and the application's idempotency contract.
- Investigate vacuum progress, old transactions, replication slots, WAL retention, and disk capacity together. Do not propose `VACUUM FULL` as routine maintenance: it rewrites the table and takes an exclusive lock.
- `CREATE INDEX CONCURRENTLY` reduces write blocking but is not lock-free, cannot run inside a transaction block, and may leave an invalid index after failure. Check index validity and runner transaction behavior before recovery or retry; partitioned indexes require a version-specific rollout strategy.
- Zero index scans alone do not justify a drop. Check constraints, statistics reset time, rare critical workloads, and replica usage, plus index dependencies.
- Treat backups as recoverable only after an isolated restore and application/data verification. PITR depends on a compatible base backup and the required continuous WAL chain; inspect retention and replay targets before changing slots or removing WAL.

For any actual change, follow [changes.md](changes.md). Official documentation links are in [sources.md](sources.md).
