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
