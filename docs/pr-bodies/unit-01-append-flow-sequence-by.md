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

Developed with AI assistance (opencode); every case above was run against the
branch's parser, not inferred from the documentation.
