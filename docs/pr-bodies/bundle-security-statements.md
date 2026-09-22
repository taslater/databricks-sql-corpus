## Summary

Adds the Unity Catalog governance surface:

- **`SHOW`** for the Unity Catalog objects: `CATALOGS`, `CONNECTIONS`,
  `[STORAGE | SERVICE] CREDENTIALS`, `EXTERNAL LOCATIONS`, `GROUPS`,
  `EFFECTIVE POLICIES` / `POLICIES`, `PROCEDURES`, `PROVIDERS`, `RECIPIENTS`,
  `SHARES`, `TABLES DROPPED`, `USERS`, `ALL IN SHARE`, `COLUMNS`, and
  `GRANTS ON SHARE` / `GRANTS TO RECIPIENT`.
- **`DESCRIBE`** for the same objects plus the `CATALOG` and `QUERY` forms,
  with a guarded DESCRIBE table reference so a bare object keyword is not read
  as a table name.
- The complete Unity Catalog **securable list**, with `ALL PRIVILEGES` bound
  against a privilege list (the reference makes them exclusive alternatives).
- **`CREATE GROUP` / `DROP GROUP`**, **`DENY`**, **`GRANT` / `REVOKE ON
  SHARE`**, and **`MSCK REPAIR ... PRIVILEGES`**.
- The **`READ FILES`** privilege and the **`ANY FILE`** securable.
- Reserve **`RECIPIENT`** so `TO RECIPIENT` without a name is rejected rather
  than parsed as a principal named `RECIPIENT`.

Adds fixtures for each and rejection cases for the partial forms a valid-parse
fixture cannot express.

## Note on overlap

This bundle sits at the intersection of three open PRs and will need a rebase
against whichever land first:

- [#8516](https://github.com/sqlfluff/sqlfluff/pull/8516) `SHOW GRANTS` — the
  `SHOW GRANTS` form is included here because the securable cases exercise it.
- [#8512](https://github.com/sqlfluff/sqlfluff/pull/8512) `READ`/`WRITE
  VOLUME` — the `AccessPermission` / `AccessObject` hunks overlap.
- the `RECIPIENT` reservation also appears in the Delta-maintenance bundle
  (`SET RECIPIENT`).

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9435 passed, 2 xfailed**
- reference conformance: **504 → 576 must-parse (+72)**, must-reject
  **363 → 377 (+14)**, **0 regressions** (the `grant-share.without-recipient`
  over-acceptance is closed by the `RECIPIENT` reservation)
- corpus **542 → 543**, no new failures, rejection **100%** (1326/1326)

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
