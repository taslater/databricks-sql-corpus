## What

`ALTER MATERIALIZED VIEW` and `ALTER STREAMING TABLE` had no schedule or column
grammar. Both now bind the same surface:

- `{ ADD | ALTER } SCHEDULE [REFRESH] { EVERY n { HOUR | DAY | WEEK } | CRON str
  [ AT TIME ZONE tz ] }`, and `ADD`/`ALTER TRIGGER ON UPDATE [AT MOST EVERY …]`.
- `DROP SCHEDULE`.
- `ALTER COLUMN col { COMMENT … | SET MASK … | DROP MASK | SET/UNSET TAGS … }`.
- `SET`/`DROP ROW FILTER`, `SET`/`UNSET TAGS` and `[SET] OWNER TO`.

- [ALTER MATERIALIZED VIEW](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-materialized-view)
- [ALTER STREAMING TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-streaming-table)

## Tests

- New `databricks/alter_materialized_view.sql` and `alter_streaming_table.sql`
  (yml regenerated).
- `databricks_test.py` pins a column comment with no value, a bare
  `ADD SCHEDULE`, and an owner with no principal.
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
