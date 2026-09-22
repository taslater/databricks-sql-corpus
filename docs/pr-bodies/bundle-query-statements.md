## Summary

Adds the Databricks query surface:

- **`OFFSET`** without the ANSI `ROW`/`ROWS` keyword
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-offset)).
  `OFFSET` remains a legal column name, so it is removed from the
  `FromClauseTerminatorGrammar` set and excluded from the alias grammar
  explicitly instead.
- **`TABLESAMPLE ( ... ) REPEATABLE (seed)`**
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-sampling)).
- **`MATCH_RECOGNIZE`**, including the trailing table alias it allows
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-match-recognize)).
- **`WITH ( ... )` options** on a table reference
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-table-reference)).
- **`MAX RECURSION LEVEL`** on a CTE definition
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-cte)).
- The **SQL pipeline `|>`** in its `FROM` / `TABLE` / `SELECT` forms, including
  a pipeline with zero operations (`FROM t`)
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-pipeline)).
- **`ORDER BY ALL`**
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-orderby)).
- **`USE [DATABASE|SCHEMA] name`**, with a bare `USE SCHEMA` rejected.

Adds a fixture for each and rejection cases for the partial forms a
valid-parse fixture cannot express (`OFFSET;`, empty `TABLESAMPLE`, a
`REPEATABLE` with no seed, `MATCH_RECOGNIZE` with no `PATTERN`, empty table
options, `MAX RECURSION LEVEL` with no level).

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9418 passed, 2 xfailed**
- reference conformance: **504 → 517 must-parse (+13)**, must-reject
  **363 → 365**, informative rejections **211 → 216**, **0 regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

Prepared with an AI coding assistant.
