## Summary

Adds the Databricks SQL scripting surface:

- **`BEGIN ... END`** compound statements, with optional labels and `ATOMIC`.
- **`DECLARE`** for variables, conditions, cursors and exception handlers.
- **`IF` / `ELSEIF` / `ELSE`** and **`CASE`** (simple and searched).
- **`WHILE`**, **`LOOP`**, **`REPEAT ... UNTIL`** and **`FOR ... DO`**, with
  **`LEAVE`** and **`ITERATE`**.
- **`SIGNAL`** and **`RESIGNAL`**, with `SQLSTATE` and condition names.
- **`GET DIAGNOSTICS`** for row count and condition information.
- **`CREATE [OR REPLACE] PROCEDURE [IF NOT EXISTS]`**, with parameters and
  characteristics, taking a scripting body.

Adds fixtures for each statement and rejection cases for the partial forms a
valid-parse fixture cannot express.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9414 passed, 2 xfailed**
- reference conformance: **504 → 523 must-parse (+19)**, must-reject
  **363/393** with informative rejections **211 → 222**, **0 regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

Prepared with an AI coding assistant.
