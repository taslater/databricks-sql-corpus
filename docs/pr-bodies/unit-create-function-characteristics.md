## What

`CREATE FUNCTION` implemented SQL and Python only. This adds the rest of the
[reference's](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-sql-function)
characteristic and body surface:

- `LANGUAGE SCALA` and `LANGUAGE JAVA`.
- `ENVIRONMENT ( environment_key = environment_value [, …] )`.
- `HANDLER handler_name` as the body of a Scala/Java function.
- `DEFAULT COLLATION default_collation_name`.

It also tightens three alternatives the reference makes exclusive: `CONTAINS
SQL` vs `READS SQL DATA`, and an `AS` body vs a `RETURN` body vs a `HANDLER`
body. Each characteristic may now appear at most once.

`OR REPLACE` with `IF NOT EXISTS` is deliberately **not** rejected: the Spark
`CREATE OR REPLACE … FUNCTION IF NOT EXISTS f AS 'class' USING JAR` form allows
both, and a fixture depends on it. The reference's exclusivity applies to the
SQL-function form, so this remains a known over-acceptance.

## Tests

- `databricks/create_function.sql` gains the Scala, Java, Python-ENVIRONMENT and
  DEFAULT COLLATION forms (yml regenerated).
- `databricks_test.py` pins the seven rejected boundaries above.
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
