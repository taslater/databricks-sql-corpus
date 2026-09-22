## What

`CREATE SCHEMA` / `CREATE DATABASE` took only a name, `COMMENT`, a location and
`WITH DBPROPERTIES`, in a fixed order. The
[reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-schema)
brackets each clause and follows the list with `[...]`, so the clauses repeat and
appear in any order:

```
[ COMMENT | DEFAULT COLLATION name | { LOCATION path | MANAGED LOCATION path } |
  RETAIN DROPPED FOR number { HOUR | DAY | WEEK } |
  WITH DBPROPERTIES ( … ) ] [...]
```

Bind them all as a repeating `AnyNumberOf`, and factor `DEFAULT COLLATION` and
`RETAIN DROPPED FOR` into shared grammars (CREATE CATALOG and CREATE VIEW already
carry their own copies of the former).

## Tests

- `databricks/create_database.sql` gains the clause set (yml regenerated).
- `databricks_test.py` pins the ten partial forms: `IF NOT` without `EXISTS`,
  `IF EXISTS`, a comment with no text, `DEFAULT COLLATION` and both locations
  with no name/path, `RETAIN DROPPED FOR` with no number or no unit, and empty
  or value-less `DBPROPERTIES`.
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
