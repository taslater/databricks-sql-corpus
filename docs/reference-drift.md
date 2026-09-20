# Reference drift ledger

The reference corpus is a snapshot of the Databricks SQL reference. This file
is what keeps it from going quietly stale: it records what the drift checks
found, and what was decided about each finding.

It is not the same as `docs/gaps.md`. A **gap** is documented syntax the parser
rejects; a **drift finding** is the *reference itself* moving under a
transcription, or a documented page with no transcription at all. A drift
finding can turn into a gap (the page added a clause, and the parser rejects
it), into new coverage (the page added a clause, and it parses), or into
nothing (an alias page, or prose).

The checks are `make drift`, `make index-check` and `make stale` — see
`docs/maintenance.md` for the cadence and `.github/workflows/drift.yml` for the
scheduled run that opens the monthly issue. **A finding is dispositioned by
editing a file and bumping its `checked:` date; the tool never edits the corpus
itself.** That is what keeps the corpus an oracle rather than a mirror.

## Snapshot — 2026-09-20

| check | result |
| --- | --- |
| `make drift` | 204/205 `same`, 1 `uncertain`, 0 `changed`, controls ok |
| `make index-check` | 40 documented pages with no file, 0 files whose page is gone |
| `make stale --days 90` | 0 (every file re-read within the window) |

The `uncertain` is `magic_cells.yml`, whose `syntax:` is a prose sentence
("a notebook cell can only have one cell magic command …") rather than a
production, so it cannot be diffed mechanically and is re-read by hand.

## Open — documented pages with no file (40)

`make index-check` compares the docs sitemap against the pages the corpus
covers, for the statement/clause families only. These pages are documented but
no file transcribes them, and they are not in `docs/reference-coverage.md`
either — most were never linked from the language-manual index page the
coverage ledger was generated from, so the "0 queued" that ended the
transcription batches was measured against an undercount.

Each needs one decision: a file (`done`), a note that it is an alias or a
landing page (`n/a`), or nothing yet (leave it here and it reappears next
month).

| page | note |
| --- | --- |
| `sql-ref-syntax-txn-begin` | `BEGIN` transaction control |
| `sql-ref-syntax-txn-begin-atomic` | `BEGIN ATOMIC` |
| `sql-ref-syntax-txn-commit` | `COMMIT` |
| `sql-ref-syntax-txn-rollback` | `ROLLBACK` |
| `sql-ref-syntax-window-functions-frame` | window frame clause |
| `sql-ref-syntax-qry-select-watermark` | `WATERMARK` clause |
| `sql-ref-syntax-qry-select-nearest-by` | `NEAREST BY` |
| `sql-ref-syntax-qry-select-pipeop` | `\|>` pipe operator |
| `sql-ref-syntax-qry-select-match-recognize-define` | `MATCH_RECOGNIZE` `DEFINE` |
| `sql-ref-syntax-qry-select-match-recognize-measures` | `MATCH_RECOGNIZE` `MEASURES` |
| `sql-ref-syntax-qry-select-match-recognize-pattern` | `MATCH_RECOGNIZE` `PATTERN` |
| `sql-ref-syntax-qry-explain-materialized-view` | `EXPLAIN` of a materialized view |
| `sql-ref-syntax-aux-analyze-drop-statistics` | `ANALYZE … DROP STATISTICS` |
| `sql-ref-syntax-aux-show-statistics` | `SHOW STATISTICS` |
| `sql-ref-syntax-aux-conf-mgmt-set-collation` | `SET COLLATION` |
| `sql-ref-syntax-aux-conf-mgmt-set-query-tags` | `SET QUERY TAGS` |
| `sql-ref-syntax-aux-describe-governed-tag` | `DESCRIBE GOVERNED TAG` |
| `sql-ref-syntax-aux-show-governed-tags` | `SHOW GOVERNED TAGS` |
| `sql-ref-syntax-ddl-create-governed-tag` | `CREATE GOVERNED TAG` |
| `sql-ref-syntax-ddl-alter-governed-tag` | `ALTER GOVERNED TAG` |
| `sql-ref-syntax-ddl-drop-governed-tag` | `DROP GOVERNED TAG` |
| `sql-ref-syntax-ddl-column-mask` | column mask clause |
| `sql-ref-syntax-ddl-row-filter` | row filter clause |
| `sql-ref-syntax-ddl-cluster-by` | `CLUSTER BY` |
| `sql-ref-syntax-ddl-tblproperties` | `TBLPROPERTIES` |
| `sql-ref-syntax-ddl-create-table` | likely a landing page over the `-using`/`-like`/`-hiveformat`/`-constraint` pages |
| `sql-ref-syntax-ddl-create-table-constraint` | table constraint clause |
| `sql-ref-syntax-ddl-alter-table-add-constraint` | `ALTER TABLE … ADD CONSTRAINT` |
| `sql-ref-syntax-ddl-alter-table-drop-constraint` | `ALTER TABLE … DROP CONSTRAINT` |
| `sql-ref-syntax-ddl-alter-table-manage-column` | `ALTER TABLE … COLUMN` |
| `sql-ref-syntax-ddl-alter-table-manage-partition` | `ALTER TABLE … PARTITION` |
| `sql-ref-syntax-ddl-alter-view-set-managed` | `ALTER VIEW … SET MANAGED` |
| `sql-ref-syntax-ddl-alter-schema-set-managed-location` | `ALTER SCHEMA … SET MANAGED LOCATION` |
| `sql-ref-syntax-ddl-alter-catalog-drop-connection` | `ALTER CATALOG … DROP CONNECTION` |
| `sql-ref-syntax-ddl-create-materialized-view-refresh-policy` | `REFRESH POLICY` |
| `ldp/developer/ldp-sql-ref-create-materialized-view-refresh-policy` | the Lakeflow copy of the same page |
| `sql-ref-syntax-ddl-create-streaming-table-auto-cdc` | `AUTO CDC` |
| `control-flow/open-stmt` | `OPEN` cursor |
| `control-flow/fetch-stmt` | `FETCH` cursor |
| `control-flow/close-stmt` | `CLOSE` cursor |

## Resolved

| date | finding | disposition |
| --- | --- | --- |
| 2026-09-20 | `alter_share.yml` transcription condensed the `alter_add_materialized_view` production | expanded to verbatim; now `same` |
| 2026-09-20 | `create_function.yml` carried the `characteristic` list unclosed (missing `}` before `environment`) | closed to match the page; now `same` |
| 2026-09-20 | `create_materialized_view.yml` omitted `column_properties`, `schedule` and `schedule_clause` | added; now `same` |
| 2026-09-20 | `create_streaming_table.yml` omitted `table_specification`, `column_properties` and `table_clauses` | added; now `same` |

## How the checks work

- **`make drift`** fetches each file's `doc:` and extracts the page's `<pre>`
  code blocks. It compares the transcription against a block (or the ordered
  join of the page's production blocks, for a production split across several)
  ignoring whitespace and case — the reference renders a production across
  inline spans and drops the line breaks. Verdicts: `same`, `changed` (with a
  token diff against the closest block), `moved` (the page redirects or 404s),
  `uncertain` (no diffable production) and `fetch-error`.
- **`make index-check`** fetches `sitemap.xml`, keeps the statement/clause URL
  families (`DEFAULT_INDEX_FAMILIES` in `drift.py`), and reports URLs with no
  file and not already listed in `docs/reference-coverage.md`. `gone` is the
  reverse: a file whose page is no longer in the sitemap.
- **`make stale`** reads the `checked:` dates. It needs no network and is the
  scheduler: a page not re-read in `STALE_DAYS` (default 90) is a candidate for
  a drift run even before the page changes.

Both `drift` and `index-check` run controls built into the harness, not the
data; the exit code is non-zero only when a control fails.
