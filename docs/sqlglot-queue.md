# sqlglot gap queue

The upstream work queue for sqlglot, seeded by `make diff` on 2026-09-19:
SQLFluff `main` at `33d8c8459` parses these documented constructs, sqlglot
30.18.0 rejects them. See `docs/sqlglot-plan.md` for why the differential is
advisory and what a disagreement does and does not prove.

An entry here is a contribution candidate, not a verdict. sqlglot's own gaps
are not bugs in the same way SQLFluff's are: it is a transpiler with a
documented leniency fallback, and a construct it does not model is accepted as
an opaque `Command` rather than rejected. The reference corpus remains the
oracle; these cases were transcribed from it, each with its doc anchor.

**Evidence bar per entry**, mirroring the SQLFluff process: pinned version, a
one-line repro, what SQLFluff does, what sqlglot does, the doc link, and a
proposed test in sqlglot's style (`tests/dialects/test_databricks.py`). Run
sqlglot's own suite before opening anything, and disclose AI assistance in the
PR as SQLFluff's CONTRIBUTING requires.

## Priority 1: `DESCRIBE DETAIL` (3 cases)

Smallest useful fix: sqlglot's `DESCRIBE` parses a table target but the
`DETAIL` keyword is unexpected. The relation form of `DESCRIBE DETAIL` is
already covered in SQLFluff by #8514.

| case | repro | sqlglot says |
| --- | --- | --- |
| `describe-detail.table` | `DESCRIBE DETAIL t` | Invalid expression / Unexpected token |
| `describe-detail.schema-qualified-table` | `DESCRIBE DETAIL schema1.t` | Invalid expression / Unexpected token |
| `describe-detail.desc-abbreviation` | `DESC DETAIL t` | Invalid expression / Unexpected token |

Doc: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-describe-table#describe-detail

## Priority 2: `CREATE VOLUME` (7 cases)

A whole statement sqlglot does not model, so every form falls back to
`Command`. The reference defines a managed form and an external form, each
with `IF NOT EXISTS`, `COMMENT` and a qualified name.

| case | repro |
| --- | --- |
| `create-volume.managed` | `CREATE VOLUME v` |
| `create-volume.external` | `CREATE EXTERNAL VOLUME v LOCATION 's3://example-bucket/data'` |
| `create-volume.qualified-name` | `CREATE VOLUME c.s.v` |
| `create-volume.if-not-exists` | `CREATE VOLUME IF NOT EXISTS v` |
| `create-volume.comment` | `CREATE VOLUME v COMMENT 'a volume'` |
| `create-volume.external-all-clauses` | `CREATE EXTERNAL VOLUME IF NOT EXISTS c.s.v LOCATION 's3://example-bucket/data' COMMENT 'a volume'` |

Doc: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-volume#syntax

## Priority 3: `CREATE CATALOG` (3 cases)

Also Command fallback. Spark SQL has catalogs, but sqlglot models none of the
DDL, so this is broadly useful beyond Databricks.

| case | repro |
| --- | --- |
| `create-catalog.plain` | `CREATE CATALOG c` |
| `create-catalog.if-not-exists` | `CREATE CATALOG IF NOT EXISTS c` |
| `create-catalog.comment` | `CREATE CATALOG c COMMENT 'a catalog'` |

Doc: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-catalog#syntax

The SQLFluff reference corpus carries further clause forms (`USING SHARE`,
`MANAGED LOCATION`, `RETAIN DROPPED`, `DEFAULT COLLATION`, `OPTIONS`, the
foreign-catalog production) that neither parser accepts yet -- see
`docs/gaps.md`; add them to sqlglot's fixture only when they are modelled there
too.

## Priority 4: `CREATE FLOW` (4 cases)

Command fallback on every form. Specialised to Lakeflow, so lower priority for
a general transpiler, but the append and auto-CDC forms are the documented core
of declarative pipelines.

| case | repro |
| --- | --- |
| `create-flow.append-by-name` | `CREATE FLOW f AS INSERT INTO t BY NAME SELECT * FROM STREAM s` |
| `create-flow.append-once` | `CREATE FLOW f AS INSERT ONCE INTO t BY NAME SELECT * FROM archive` |
| `create-flow.append-with-comment` | `CREATE FLOW f COMMENT 'backfill' AS INSERT ONCE INTO t BY NAME SELECT * FROM archive` |
| `create-flow.auto-cdc` | `CREATE FLOW f AS AUTO CDC INTO t FROM STREAM s KEYS (id) SEQUENCE BY seq` |

Doc: https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow#syntax

## Priority 5: smaller, targeted gaps

| case | repro | sqlglot says |
| --- | --- | --- |
| `convert-to-delta.path` | ``CONVERT TO DELTA parquet.`s3://example-bucket/data` `` | Invalid expression / Unexpected token |
| `create-materialized-view.expectations-only` | `CREATE OR REFRESH MATERIALIZED VIEW mv (CONSTRAINT c EXPECT (x IS NOT NULL) ON VIOLATION DROP ROW) AS SELECT x FROM s` | Expecting ) |
| `create-streaming-table.private` | `CREATE PRIVATE STREAMING TABLE t (a BIGINT)` | Command fallback |
| `create-streaming-table.private-with-refresh` | `CREATE OR REFRESH PRIVATE STREAMING TABLE t AS SELECT * FROM STREAM s` | Command fallback |
| `create-view.default-collation` | `CREATE VIEW v DEFAULT COLLATION UTF8_BINARY AS SELECT a FROM t` | Command fallback |
| `create-view.metric-yaml` | `CREATE VIEW v WITH METRICS LANGUAGE YAML AS $$ version: 0.1 $$` | Command fallback |

`CONVERT TO DELTA` is the odd one: sqlglot already parses the table form, so the
path form is a widening rather than a new statement. `WITH METRICS LANGUAGE
YAML` uses a dollar-quoted body -- check whether sqlglot's tokenizer handles
`$$...$$` before scoping that one.

## Process

1. Pick a group; reproduce on the pinned version:
   `.venv-main/bin/python -c "import sqlglot; sqlglot.parse_one('<repro>', read='databricks')"`.
2. Read the doc page and sqlglot's parser for the statement before writing
   anything; prefer widening an existing expression over a new class.
3. Branch from `tobymao/sqlglot` main, add a `validate_identity` case to
   `tests/dialects/test_databricks.py`, and run their suite.
4. Open the PR with the doc link, the SQLFluff cross-reference, and AI
   disclosure.

Nothing in this queue affects this project's metrics; it exists so the
differential's second-gap list is actionable rather than read once and lost.
