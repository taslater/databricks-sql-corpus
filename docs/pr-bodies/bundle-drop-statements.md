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
