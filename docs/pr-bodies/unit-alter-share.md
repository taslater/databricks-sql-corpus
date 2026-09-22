## What

`ALTER SHARE` had no grammar. It now binds the documented object-membership
clauses — `ADD`/`ALTER` and `REMOVE` for `TABLE` (with `COMMENT`, `PARTITION`,
`AS` and `WITH`/`WITHOUT HISTORY`), `MATERIALIZED VIEW`, `SCHEMA`, `VIEW` and
`MODEL` — plus `RENAME TO` and `[SET] OWNER TO`.

[ALTER SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-share)

## Tests

- New `databricks/alter_share.sql` covering the object clauses and the full
  table form (yml regenerated).
- `databricks_test.py` pins `ADD TABLE` with no name, a bare `ADD`, and
  `RENAME TO` with no name.
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
