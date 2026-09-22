## Summary

Closes the Databricks `CREATE` statement surface against the vendor
reference. Every case is a `CREATE <object>` family member:

- **`CREATE CATALOG`**: `USING SHARE`, `RETAIN DROPPED`, `DEFAULT COLLATION`,
  `OPTIONS`, and the `FOREIGN CATALOG` form.
- **`CREATE SCHEMA`**: the full clause set (`IF NOT EXISTS`, `COMMENT`,
  `DEFAULT COLLATION`, `LOCATION`, `MANAGED LOCATION`, `RETAIN DROPPED`,
  `DBPROPERTIES`).
- **`CREATE TABLE`**: table-level `DEFAULT COLLATION` and a credentialed
  `LOCATION`.
- **`CREATE FUNCTION`**: the characteristic set (`LANGUAGE` including `JAVA`
  and `SCALA`, `DEFAULT COLLATION`, Python `ENVIRONMENT`), and `OR REPLACE`
  is now exclusive with `IF NOT EXISTS`, as the reference requires.
- **`CREATE CONNECTION`** / **`CREATE SERVER`** and **`CREATE EXTERNAL
  LOCATION`**.
- **`CREATE SHARE`** and **`CREATE RECIPIENT`**.

Adds a fixture per statement and rejection cases for the partial forms a
valid-parse fixture cannot express.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9444 passed, 2 xfailed**
- reference conformance: **504 → 547 must-parse (+43)**, must-reject
  **363 → 366** caught, informative rejections **211 → 251**, **0
  regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

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
