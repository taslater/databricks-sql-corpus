## Summary

Closes the Databricks Delta maintenance and utility surface against the
vendor reference:

- **`FSCK REPAIR TABLE`** (dry run, metadata-only, verify files).
- **`REORG TABLE ... APPLY (PURGE)`** (including checkpoint / upgrade uniform).
- **`REPAIR TABLE`** (the MSCK / ADD / DROP / SYNC forms).
- **`CACHE SELECT`** and **`DROP BLOOMFILTER INDEX`**.
- **`OPTIMIZE` / `OPTIMIZE FULL`** and **`VACUUM` / `VACUUM FULL` / `VACUUM
  LITE`** (FULL and LITE are exclusive with each other and with DRY RUN).
- **`MERGE WITH SCHEMA EVOLUTION`**.
- **`COPY INTO`** with credentials, validation, files/pattern and
  format/copy options.
- The **`REFRESH`** family: foreign, materialized view, streaming table,
  table, function and path.
- **`UNDROP`**, **`SYNC`**, **`LIST`**, **`CALL`**, **`SET RECIPIENT`**.
- **`ANALYZE ... COMPUTE STORAGE METRICS`**.
- **`SET CATALOG`** alongside `USE CATALOG`, and the `SET`/`UNSET TAG`
  extensions (external metadata, functions/procedures, optional value).

Adds a fixture per statement and rejection cases for the partial forms a
valid-parse fixture cannot express. `SET RECIPIENT` makes `RECIPIENT` a
reserved word, so the `DESCRIBE RECIPIENT` alternative is bound explicitly
here.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9488 passed, 2 xfailed**
- reference conformance: **504 → 568 must-parse (+64)**, must-reject
  **363 → 367** caught, informative rejections **211 → 259**, **0
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
