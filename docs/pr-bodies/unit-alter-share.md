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

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
