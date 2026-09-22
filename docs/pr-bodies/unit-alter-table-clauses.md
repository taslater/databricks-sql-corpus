## What

`ALTER TABLE` rejected six documented clauses. This binds them:

- `ALTER COLUMN a COMMENT 'x', b COMMENT 'y'` — the multi-column list; the
  grammar took a single column.
- `DEFAULT COLLATION name`.
- `SET EXTERNAL [DRY RUN]`.
- `SET MANAGED [TRUNCATE UNIFORM HISTORY | MOVE | COPY]`.
- `UNSET MANAGED [TRUNCATE UNIFORM HISTORY]`.
- `REPLACE PARTITIONED BY WITH CLUSTER BY (cols)`, or `… CLUSTER BY AUTO`.

`DEFAULT COLLATION` is added as a shared `DefaultCollationClauseGrammar` rather
than inline: CREATE SCHEMA, CREATE TABLE and CREATE FUNCTION all take the same
production, and CREATE CATALOG and CREATE VIEW already carry their own copy.

[ALTER TABLE reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-table)

## Tests

- `databricks/alter_table.sql` gains the clause set (yml regenerated).
- `databricks_test.py` pins `REPLACE PARTITIONED BY WITH` (a missing `CLUSTER BY`)
  and `ALTER TABLE RENAME TO` (a missing table name) as rejections.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

This pull request was co-authored with AI assistants: **Claude Opus 5**
(Anthropic) and **DeepSeek V4.1 Flash**. They drafted the grammar, the
fixtures and the rejection tests, and ran the measurements, under the
contributor's direction. Every construct was checked against the Databricks SQL
reference, and the changes were run through the whole `test/dialects/` suite,
the Python/Rust parity tests, `make reference` and `make corpus` before
submission. The human contributor remains responsible for the final pull
request, including its correctness, tests and maintainability, as
[CONTRIBUTING.md](https://github.com/sqlfluff/sqlfluff/blob/main/CONTRIBUTING.md#ai-assisted-contributions)
requires.
