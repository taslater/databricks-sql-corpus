## What

`COPY INTO` has no grammar in the `databricks` or `sparksql` dialects — SQLFluff
implements it for T-SQL and Snowflake only — so every form was unparsable,
including the documented minimal case:

```sql
COPY INTO t FROM 's3://example-bucket/p' FILEFORMAT = CSV;
```

The [reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-copy-into)
gives the target as `BY POSITION` or a column list, the source as a path (with an
optional inline `CREDENTIAL` and `ENCRYPTION`) or a bracketed `SELECT`, and then
`FILEFORMAT`, `VALIDATE`, `FILES`/`PATTERN`, `FORMAT_OPTIONS` and `COPY_OPTIONS`.

`databricks` gets its own segment; Spark has no `COPY INTO`, so it does not go in
the `sparksql` base.

Every clause keeps its required tokens required, which is what rejects the partial
forms: an empty or trailing-comma column list, `VALIDATE` without a unit or a
number, an empty or value-less option list, `FILEFORMAT =` with no source, a
`CREDENTIAL` with no name, and `FILES` + `PATTERN` (which the reference makes
exclusive).

## Tests

- New `databricks/copy_into.sql`: the fifteen documented forms, from the minimal
  case through every clause together.
- `databricks_test.py` pins the fifteen partial forms a valid-parse fixture cannot
  express.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.
- The scraped corpus: `dbx-dlt-notebooks` reaches 19/19, mutation unchanged at 100%.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
