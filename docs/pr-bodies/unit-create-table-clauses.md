## What

The Databricks table definition had neither a credential-aware location nor a
table-level default collation:

```sql
CREATE TABLE t (a INT) LOCATION 's3://…' WITH (CREDENTIAL cred);
CREATE TABLE t (a STRING) DEFAULT COLLATION UTF8_BINARY;
```

`LocationWithCredentialGrammar` already existed for other statements; add it and
a shared `DefaultCollationClauseGrammar` to the table clause list. The Databricks
`TableDefinitionSegment` is rewritten explicitly rather than copying SparkSQL's,
so the two clauses sit alongside the clauses it already had.

Three over-acceptances on the page — a table constraint with no column,
`EXTERNAL` with `TEMP`, and `REPLACE` with `IF NOT EXISTS` — are left for a
separate rejection-hardening change, since they need the prefix alternatives
restructured.

[CREATE TABLE [USING]](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using)

## Tests

- `databricks/create_table.sql` gains both clauses (yml regenerated).
- `databricks_test.py` pins the two partial forms.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
