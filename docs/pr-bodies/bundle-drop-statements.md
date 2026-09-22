## Summary

Closes the Databricks Unity Catalog `DROP` surface against the vendor
reference. All are `DROP <object>` family members:

- **`DROP TABLE ... FORCE`** (overrides the ANSI grammar to add `FORCE`).
- **`DROP CONNECTION`**.
- **`DROP [STORAGE | SERVICE] CREDENTIAL [FORCE]`**.
- **`DROP EXTERNAL LOCATION`**.
- **`DROP POLICY <name> ON { METASTORE | CATALOG ... | SCHEMA ... | TABLE ... }`**.
- **`DROP PROCEDURE [IF EXISTS]`**.
- **`DROP PROVIDER`**, **`DROP RECIPIENT`**, **`DROP SHARE`**.
- **`DROP TEMPORARY VARIABLE`**.

`DROP MATERIALIZED VIEW` is handled in a separate PR. Adds the `drop_uc`
fixture and rejection cases for the partial forms a valid-parse fixture
cannot express.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9394 passed, 2 xfailed**
- reference conformance: **504 → 516 must-parse (+12)**, must-reject
  **363/393** with informative rejections **211 → 220**, **0 regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

Prepared with an AI coding assistant.
