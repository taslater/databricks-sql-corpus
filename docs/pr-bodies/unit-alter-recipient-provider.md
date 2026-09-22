## What

`ALTER RECIPIENT` and `ALTER PROVIDER` had no grammar. This binds
`ALTER RECIPIENT r RENAME TO … | [SET] OWNER TO … | SET PROPERTIES (key [=]
value …) | UNSET PROPERTIES (key …)`, with the equals sign optional and property
keys possibly dotted, and `ALTER PROVIDER p RENAME TO … | [SET] OWNER TO …`.

- [ALTER RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-recipient)
- [ALTER PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-provider)

## Tests

- New `databricks/alter_recipient.sql` and `alter_provider.sql` (yml regenerated).
- `databricks_test.py` pins empty `PROPERTIES`/`UNSET PROPERTIES` and a `RENAME
  TO` with no value.
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
