## What

The DBR 16.x maintenance modes had no grammar:

- `OPTIMIZE table FULL [WHERE …] [ZORDER BY …]` — an optional `FULL` before the
  existing clauses.
- `VACUUM table { FULL | LITE | DRY RUN }` — `FULL` and `LITE` bound as
  alternatives to `DRY RUN`, mutually exclusive with each other, so
  `VACUUM t FULL LITE` and `VACUUM t DRY RUN FULL` are rejected.

`VACUUM` gets a Databricks segment (the SparkSQL base does not have these
modes); `OPTIMIZE` is already Databricks-only.

- [OPTIMIZE](https://docs.databricks.com/aws/en/sql/language-manual/delta-optimize)
- [VACUUM](https://docs.databricks.com/aws/en/sql/language-manual/delta-vacuum)

## Tests

- New `databricks/optimize.sql` and `databricks/vacuum.sql` covering every clause
  combination (yml regenerated).
- `databricks_test.py` pins the eight boundaries, including the exclusive modes.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
