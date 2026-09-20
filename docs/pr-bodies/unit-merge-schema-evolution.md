## What

`MERGE WITH SCHEMA EVOLUTION INTO …` was rejected: the merge literal was just
`MERGE INTO`. Bind the optional clause between them, per the
[Delta MERGE reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into).

## Tests

- `databricks/merge_into.sql` gains the schema-evolution form (yml regenerated).
- `databricks_test.py` pins `MERGE WITH SCHEMA EVOLUTION t …` (the clause only
  applies before `INTO`) as a rejection.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
