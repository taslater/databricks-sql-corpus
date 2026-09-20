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

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
