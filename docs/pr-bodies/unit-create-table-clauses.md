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
