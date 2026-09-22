## What

Three Unity Catalog connectivity statements had no grammar:

- `ALTER CONNECTION c { [SET] OWNER TO … | RENAME TO … | OPTIONS (key value …) }`.
- `ALTER EXTERNAL LOCATION l { RENAME TO … | SET URL url [FORCE] | SET STORAGE
  CREDENTIAL c | [SET] OWNER TO … }`.
- `ALTER [STORAGE | SERVICE] CREDENTIAL c { RENAME TO … | [SET] OWNER TO … }`.

- [ALTER CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-connection)
- [ALTER EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-location)
- [ALTER CREDENTIAL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-credential)

## Tests

- New `databricks/alter_connection.sql`, `alter_external_location.sql` and
  `alter_credential.sql` (yml regenerated).
- `databricks_test.py` pins the four partial forms.
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
