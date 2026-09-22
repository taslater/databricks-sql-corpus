## What

`CREATE SHARE` and `CREATE RECIPIENT` had no grammar, so every documented form
was unparsable:

```sql
CREATE SHARE customer_share;
CREATE RECIPIENT r USING ID 'azure:westus:abc';
```

The references give `CREATE SHARE [IF NOT EXISTS] name [COMMENT …]` and
`CREATE RECIPIENT [IF NOT EXISTS] name [USING ID id] [COMMENT …]
[PROPERTIES ( property_key [ = ] property_value [, …] )]`, where a property key
may be dotted and the equals sign is optional.

Both are `databricks`-only (Delta Sharing), so they do not go in the `sparksql`
base. Each clause keeps its required tokens required, which rejects the partial
forms: a missing name, a missing sharing identifier, an empty or value-less
property list, and a comment with no text.

- [CREATE SHARE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-share)
- [CREATE RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-recipient)

## Tests

- New `databricks/create_share.sql` and `databricks/create_recipient.sql`
  covering the documented clause combinations (yml regenerated).
- `databricks_test.py` pins the eight partial forms a valid-parse fixture cannot
  express.
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
