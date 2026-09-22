## What

The standalone append flow's spec is
`REPLACE USING ( column_name [, ...] ) SEQUENCE BY sequence_column`
([CREATE FLOW](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow),
Example 3). #8509 bound `REPLACE USING (…)` but left `SEQUENCE BY` unbound,
so `main` accepts the incomplete form and rejects the documented pair.

Bind the two together, as the inline FLOW clause already does for streaming
tables.

## Why here rather than #8460

The fix was carried from #8460 (`Co-authored-by: Yash Raj Pandey
<yashpn62@gmail.com>`), which is superseded by the merged PRIVATE/FLOW work
and now conflicts with `main`; the author has been quiet since 2026-09-18.

## Tests

- `create_flow_and_private_streaming_table.sql` now uses the documented pair
  (yml regenerated).
- `databricks_test.py` pins both incomplete forms as rejections — a
  valid-parse fixture cannot express the over-acceptance.
- Whole `test/dialects/` directory: 7032 passed.

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
