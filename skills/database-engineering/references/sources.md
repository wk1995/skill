# Sources and Attribution

Consult this file when checking provenance or engine-specific claims. Sources were consulted on 2026-09-10. This Skill synthesizes guidance from the three projects below; it does not import their executable tooling or adopt their hosting recommendations. Upstream popularity is not technical validation.

## Skill References

| Source at a pinned commit | Material informing this Skill | Adaptation |
| --- | --- | --- |
| [Supabase Postgres Best Practices](https://github.com/supabase/agent-skills/blob/8331f910845103c08d51f6ca1d86ebb7d1f745e3/skills/supabase-postgres-best-practices/SKILL.md) | Workload priorities, schema/index guidance, connection management, RLS | Separate generic PostgreSQL behavior from provider helpers; require effective-role verification for isolation tests |
| [PlanetScale MySQL](https://github.com/planetscale/database-skills/blob/73b20b7eb64716d8c7100c054f0677c0c6e77e30/skills/mysql/SKILL.md) and [Postgres](https://github.com/planetscale/database-skills/blob/73b20b7eb64716d8c7100c054f0677c0c6e77e30/skills/postgres/SKILL.md) | Engine-specific schema, indexing, transaction and operational topics | Remove vendor preference and unconditional tuning rules; qualify online DDL and index-removal decisions |
| [Jeffallan Database Optimizer](https://github.com/Jeffallan/claude-skills/blob/882ef55e377dbf9a4dbe496bb41ac6ccd0e555cf/skills/database-optimizer/SKILL.md) | Baseline, diagnosis, incremental change, and post-change evidence | Qualify runtime plan execution and concurrent index behavior; support offline work without invented measurements |

## Authoritative Documentation

These versioned references establish a baseline, not a claim that every supported deployment behaves identically. Check matching server, extension, and managed-service documentation for the actual task.

| Topic | Reference |
| --- | --- |
| PostgreSQL plan execution and side effects | [PostgreSQL 17 EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html) |
| PostgreSQL index construction, concurrent failure, and transaction restrictions | [PostgreSQL 17 CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html) |
| PostgreSQL constraints and partition limitations | [Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html), [partitioning](https://www.postgresql.org/docs/17/ddl-partitioning.html) |
| PostgreSQL policy roles and bypass | [PostgreSQL 17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html) |
| PostgreSQL query statistics names and units | [PostgreSQL 17 pg_stat_statements](https://www.postgresql.org/docs/17/pgstatstatements.html) |
| PostgreSQL maintenance and recovery | [VACUUM](https://www.postgresql.org/docs/17/sql-vacuum.html), [continuous archiving and PITR](https://www.postgresql.org/docs/17/continuous-archiving.html) |
| MySQL runtime plans and supported forms | [MySQL 8.4 EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html) |
| MySQL DDL locking, algorithms, and limitations | [Online DDL operations](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html), [limitations](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-limitations.html) |
| MySQL DDL transaction boundaries | [Implicit commits](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html), [atomic DDL](https://dev.mysql.com/doc/refman/8.4/en/atomic-ddl.html) |
| MySQL partitioning restrictions | [Storage engines](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-storage-engines.html), [unique keys](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-partitioning-keys-unique-keys.html) |
| MySQL statement timer units | [Performance Schema statement summary tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) |
| MySQL recovery | [Point-in-time recovery](https://dev.mysql.com/doc/refman/8.4/en/point-in-time-recovery.html) |

## Upstream MIT Notices

The upstream projects use the MIT License. Their copyright notices are retained below; the permission and disclaimer text applies separately to each upstream work.

- Supabase: Copyright (c) 2026 Supabase
- PlanetScale: Copyright (c) 2026 PlanetScale
- Jeffallan/claude-skills: Copyright (c) 2025

```text
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
