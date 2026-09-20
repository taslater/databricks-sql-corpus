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

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
