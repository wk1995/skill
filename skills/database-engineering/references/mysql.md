# MySQL/InnoDB Engineering

Use for MySQL schema, query, transaction, and operational tasks. MySQL 8.4/InnoDB is the documentation baseline. Establish the actual server, storage engine, SQL mode, and client/ORM versions; MariaDB, Vitess, and older MySQL versions require separate compatibility verification.

## Schema and Indexes

- Choose a clustered primary key with awareness that InnoDB secondary indexes store primary-key values. Narrow, insertion-friendly keys can reduce storage and page churn, but UUID or distributed-ID requirements may justify another design.
- Check signedness and types across foreign keys and joins. Use DECIMAL for exact decimal quantities. Choose DATETIME versus TIMESTAMP from timezone conversion and range semantics rather than a universal preference.
- Use an appropriate `utf8mb4` collation supported by the deployment. Assess case/accent equivalence and existing duplicates before changing collation or adding uniqueness. Do not impose MySQL 8-only collations on older compatible servers.
- Design composite indexes from predicates and ordering; distinguish range bounds, index condition pushdown, covering access, and sorting. Later index columns may still help even after a range condition. Account for the write/storage cost of each index.
- An unused-index report is a lead, not authorization to drop. Check constraints, foreign-key dependencies, observation duration, statistics resets, and rare jobs. Invisible indexes can support a measured experiment where supported, but remain maintained on writes and have restrictions.
- Check partitioning restrictions before proposing it: MySQL 8.4 user-partitioned InnoDB tables cannot participate in foreign-key relationships, and partitioning columns must be represented in each unique key as required by the engine. Do not transplant PostgreSQL DDL or generic partition advice.

## Query Diagnosis

Read plain `EXPLAIN` or `EXPLAIN FORMAT=JSON` first. On supported MySQL versions, `EXPLAIN ANALYZE` executes supported statements and returns runtime plan information; it is not interchangeable with PostgreSQL's options. Check the exact version and statement support before using it.

Use slow-query evidence or `performance_schema.events_statements_summary_by_digest` when available to rank queries by workload impact. Performance Schema timer values use picoseconds; convert units explicitly when reporting latency. Consider count, total time, rows examined, and lock evidence, not just one slow execution.

Investigate full scans, `Using filesort`, or temporary-table use in workload context; those labels alone are not defects. Match bound parameter types to indexed columns, inspect implicit conversions and collation, and check repeated application calls before rewriting SQL or changing configuration.

Test result equivalence and concurrency effects as well as timing. Preserve duplicate handling, outer-join semantics, NULLs, transaction behavior, and deterministic pagination. Do not replace `UNION` with `UNION ALL` unless duplicates are acceptable.

## Transactions, Locks, and Connections

- Check the configured isolation level. InnoDB commonly defaults to REPEATABLE READ; range operations may involve next-key/gap locks. READ COMMITTED changes semantics and some locking behavior, so it is a task-specific decision, not a general deadlock fix.
- Inspect deadlock or wait evidence and transaction boundaries. Short transactions and consistent access order can help. For deadlocks, retry the whole transaction only with bounded backoff and safe application side effects; lock wait timeouts can have different rollback scope depending on server settings.
- Bound aggregate application pools and inspect connection churn, active work, and lock waits before increasing server limits. Configuration changes require memory/capacity evidence and a recovery route.
- Replication delay affects read-after-write behavior and rollout validation. Determine the replication topology and the measurement's meaning; use the configured topology's monitoring tools instead of assuming a single lag number proves health.

## DDL and Recovery

- Ordinary MySQL DDL can implicitly commit and generally cannot be undone with transaction ROLLBACK. Atomic DDL for supported statements provides crash consistency, not user-controlled transactional rollback.
- Choose supported ALGORITHM/LOCK clauses for the exact ALTER operation, table, and version. `INSTANT`, `INPLACE`, and `COPY` have distinct constraints; INPLACE may still rebuild data. Specify a supported requirement to fail rather than silently accept a more disruptive algorithm when the availability contract requires it.
- Online DDL can wait for or acquire exclusive metadata locks. Inspect long transactions, free disk, load, replication, and timeout controls before execution. Do not describe `LOCK=NONE` as eliminating all locking.
- Plan logical reversal, a forward repair, or a tested restore before destructive changes. Verify backup consistency and, for point-in-time recovery, the required binary logs, retention, and replay coordinates. Restore into an isolated target and verify it before a cutover.

For rollout and partial failures, follow [changes.md](changes.md). Official documentation links are in [sources.md](sources.md).
