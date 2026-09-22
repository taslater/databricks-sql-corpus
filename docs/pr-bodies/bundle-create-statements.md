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

Prepared with an AI coding assistant.
