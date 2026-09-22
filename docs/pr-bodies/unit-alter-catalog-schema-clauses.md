## What

`ALTER CATALOG` and `ALTER SCHEMA` / `ALTER DATABASE` rejected three documented
clauses: `DEFAULT COLLATION`, `SET MANAGED LOCATION` and
`[SET] RETAIN DROPPED TO …`. This binds them (plus `OPTIONS` on a catalog).

The two clauses are shared grammars: the collation value may be a bare
identifier (as on CREATE) or a quoted string (as on ALTER), and `RETAIN DROPPED`
takes `FOR` on the CREATE statements and `TO` on ALTER.

- [ALTER CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-catalog)
- [ALTER SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-schema)

## Tests

- `databricks/alter_catalog.sql` and `alter_database.sql` gain the clauses (yml
  regenerated).
- `databricks_test.py` pins the partial forms (a collation or managed location
  with no value, `RETAIN DROPPED` with no unit, empty `TAGS`/`DBPROPERTIES`).
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
