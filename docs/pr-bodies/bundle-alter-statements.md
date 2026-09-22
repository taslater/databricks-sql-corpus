## Summary

Closes the Databricks `ALTER` statement surface against the vendor reference.
All statements are `ALTER <object>` family members, so they share one
`match_grammar` review context:

- **`ALTER CATALOG` / `ALTER SCHEMA`**: `DEFAULT COLLATION`,
  `MANAGED LOCATION`, `RETAIN DROPPED` and the rest of the clause set.
- **`ALTER TABLE`**: multi-column `ALTER`/`CHANGE COLUMN`, `DEFAULT
  COLLATION`, `SET EXTERNAL [DRY RUN]`, `SET`/`UNSET MANAGED`, and
  `REPLACE PARTITIONED BY WITH CLUSTER BY`.
- **`ALTER MATERIALIZED VIEW` / `ALTER STREAMING TABLE`**: schedule and
  trigger clauses, `ALTER COLUMN`, row filter, tags and owner.
- **`ALTER SHARE`**: add/remove a table, schema, view or model; rename; owner.
- **`ALTER GROUP`**: add/drop a group or user.
- **`ALTER CONNECTION` / `ALTER EXTERNAL LOCATION` / `ALTER CREDENTIAL`**.
- **`ALTER RECIPIENT` / `ALTER PROVIDER`**.

Adds a fixture per statement and rejection cases for the partial forms a
valid-parse fixture cannot express.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9439 passed, 2 xfailed**
- reference conformance: **504 → 552 must-parse (+48)**, **must-reject 363/393
  with informative rejections 211 → 223**, **0 regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

Prepared with an AI coding assistant.
