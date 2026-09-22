## What

`CREATE CONNECTION` and `CREATE EXTERNAL LOCATION` had no grammar, so every
documented form was unparsable:

```sql
CREATE CONNECTION c TYPE POSTGRESQL OPTIONS (host 'h', port '5432');
CREATE EXTERNAL LOCATION s3_remote URL 's3://…' WITH (STORAGE CREDENTIAL c);
```

The references give `CREATE [SERVER] CONNECTION [IF NOT EXISTS] name TYPE type
OPTIONS ( option_key option_value [, …] ) [COMMENT …]` — where an option key may
be a dotted identifier or a string literal, and a value is a literal or a
`secret(scope, key)` reference — and `CREATE EXTERNAL LOCATION [IF NOT EXISTS]
name URL url WITH (STORAGE CREDENTIAL credential_name) [COMMENT …]`. `SERVER` is
the standards-compliance synonym for `CONNECTION`.

Both are `databricks`-only (Unity Catalog). The option list requires a value on
every entry, and the share/location clauses keep their required tokens required,
which rejects the partial forms (a missing name, `TYPE` with no value, an empty
or value-less option list, a missing `URL`/`WITH`, an empty `WITH`, and a
`COMMENT` with no text).

- [CREATE CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-connection)
- [CREATE EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-location)

## Tests

- New `databricks/create_connection.sql` and
  `databricks/create_external_location.sql` (yml regenerated), including the
  backticked location names and both `secret(…)` and dotted/string option keys.
- `databricks_test.py` pins the fourteen partial forms.
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
