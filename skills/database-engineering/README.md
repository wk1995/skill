# Database Engineering

Language: **English** | [中文](README.zh-CN.md)

`database-engineering` helps design, review, optimize, migrate, and troubleshoot PostgreSQL and MySQL databases. It combines workload-based diagnosis with version-aware changes and recovery planning.

## How To Use It

Describe the engineering task and provide the engine/version, schema or migration, SQL and execution plan if available, and whether you want a review, file edits, or live execution. The Skill inspects existing project information first and can prepare an offline plan without database credentials.

Example requests:

```text
Review this PostgreSQL 17 order schema for constraints, indexes, and tenant isolation.
Diagnose this MySQL 8.4 slow query using its EXPLAIN output and existing indexes.
Rewrite this application's PostgreSQL query while preserving NULL and pagination behavior.
Prepare an expand/backfill/contract migration for this large MySQL table; edit files only.
Investigate PostgreSQL connection exhaustion using these pool metrics and wait events.
Plan a restore drill and verification steps for our PostgreSQL backups.
```

Expect concrete findings, SQL or file changes, evidence, validation steps, and applicable rollout/recovery guidance. Live execution follows the authorized target and scope; preparing a migration does not execute it. Without runtime measurements, performance improvements remain unverified.

The Skill follows your existing provider, ORM, and migration tooling. It supplies guidance and uses tools available in the working environment; it does not bundle a database client or provision a database. PostgreSQL 17 and MySQL 8.4 documentation provide reference baselines, not a compatibility guarantee for other versions.

## When It Triggers

- PostgreSQL/MySQL schema, constraint, index, application SQL, or migration work.
- Slow-query and execution-plan analysis, lock/deadlock diagnosis, connection exhaustion, and replication lag.
- Maintenance, backup verification, and recovery planning or authorized execution.
- PostgreSQL row-level security or review of ORM-generated database changes.

## When It Does Not Trigger

- Business reporting or analytical queries without a database engineering task.
- Tasks specific to SQLite, SQL Server, Oracle, MongoDB, Redis, standalone vector databases, or other engines. PostgreSQL extensions such as pgvector remain PostgreSQL work, with extension-specific documentation needed.
- Product/vendor/ORM selection alone, billing, or infrastructure provisioning without database engineering work.
- Application changes that neither modify nor investigate SQL, schemas, or database behavior.

See [SKILL.md](SKILL.md) for the operational procedure and [sources and attribution](references/sources.md) for the Supabase, PlanetScale, and Jeffallan references and upstream notices.
