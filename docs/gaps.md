# SQLFluff Databricks gap queue

The upstream work queue. Every entry is a construct that appears in published
Databricks SQL and that SQLFluff's `databricks` dialect cannot parse, with a
minimal reproduction verified against SQLFluff `main`.

This file replaces the `GAPS` inventory that lived in
`tests/test_databricks_gap.py`, which tracked gaps in this project's own
retired parser. Of the twelve gaps that inventory still held when the parser
was retired, **ten were already supported by SQLFluff** — which is the
clearest single argument for having retired it. The two that were not are
recorded below.

## Open

**`REPLACE USING (…) SEQUENCE BY …` in append flows is rejected, while the
incomplete form is accepted.** The
[CREATE FLOW reference](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow)
defines the append branch as
`INSERT [ONCE] INTO target_table BY NAME [ replace_using_spec ] query`, with
`replace_using_spec` = `REPLACE USING ( column_name [, ...] ) SEQUENCE BY
sequence_column`, and its Example 3 uses the pair. SQLFluff `main` at
`33d8c8459` (measured 2026-09-19) does the opposite: it accepts
`REPLACE USING (…)` with no `SEQUENCE BY` and rejects the documented pair.
Found while reconciling
[#8460](https://github.com/sqlfluff/sqlfluff/pull/8460) against the merged
#8509; the corrected grammar already exists on #8460's branch (a two-token
addition at `dialect_databricks.py:2465`). It lands either through the
author's reduced rebase or as a follow-up PR. No corpus file exercises it
yet, so it is recorded from the reference and #8460's fixture rather than
from a failure count.

**`DROP MATERIALIZED VIEW`** is unparsable in the `databricks` dialect as of
SQLFluff 4.3.0. Repro: `DROP MATERIALIZED VIEW mv;`. Found 2026-09-19 by the
semantic-model tests in `sqlfluff-plugin-conventions`, not by this corpus —
no corpus file needs it yet, so it is queued rather than claimed. Databricks
documents the construct, so `DropViewStatementSegment` should accept the
`MATERIALIZED` keyword the same way `CreateMaterializedViewStatementSegment`
already exists; belongs in an upstream PR when picked up.

Everything else the corpus exposed has a pull request against
`sqlfluff/sqlfluff`; see "Landed" below.

What is left is not dialect work:

- **Templating** — four corpus files, in the section below. The fix is in
  `placeholder.py`, not in a dialect.
- **The securable list.** `AccessObjectSegment` has no `SHARE`, `CONNECTION`,
  `EXTERNAL LOCATION`, `CLEAN ROOM`, `PROCEDURE` or `STORAGE`/`SERVICE
  CREDENTIAL`, so `GRANT ... ON SHARE s`, `SHOW GRANTS ON CONNECTION c` and
  their relatives are rejected. The limitation is symmetric across `GRANT`,
  `REVOKE` and `SHOW GRANTS` — see #8516, which reuses that segment
  deliberately so the three cannot drift apart. Widening it should move all
  three together and needs six or so new keywords. No corpus file needs it
  yet.
- **The type-aware naming rules** — built. They live in the public
  `sqlfluff-plugin-conventions` repo (18 rules plus arbitrary scorer
  functions), not in core.

### Notes on the three that were mis-recorded

**`EXECUTE IMMEDIATE` was missing entirely**, not only its `USING` clause.
Even `EXECUTE IMMEDIATE 'SELECT 1';` was unparsable. Apache Spark's reference
gives the same syntax as Databricks', down to the bracketed
`USING ( arg [AS] alias, ... )`, so it went in `dialect_sparksql.py` and
`databricks` inherits it. Spark's own test file settles a question the
Databricks page leaves ambiguous: `INTO (a, b)` is labelled
`-- INTO does not support braces - parser error`, so the braced spelling stays
rejected and a test asserts it.

**`CONVERT TO DELTA` was mis-recorded.** `NO STATISTICS` had been supported all
along — `Sequence("NO", "STATISTICS", optional=True)` is already in
`ConvertToDeltaStatementSegment`. The real gap was the target: the grammar took
only a `FileReferenceSegment`, so a path parsed while `CONVERT TO DELTA
my_table` did not. The
[reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-convert-to-delta)
is explicit that table_name is "either an optionally qualified table
identifier or a path".

**The `-- MAGIC` entry was mis-described, and closed itself.** It read as "body
line starting with `%`", but the two corpus files that failed —
`dbx-learn-databricks/Administration/Databricks Administration.sql` and
`dbx-learn-databricks/Delta Lake/Change Data Feed.sql` — both failed on a
single-line directive carrying content, followed by further body lines:

```
-- MAGIC %md # Databricks Administration
-- MAGIC
-- MAGIC Commands and tricks to manage Databricks clusters
```

which is the shape #8507 fixes. Measured 2026-09-18: on #8507's branch the
first file parses and the second gets past the magic cell, failing instead on
`DESC HISTORY` (#8510). With all four applied, both parse. The only
`%`-leading body line anywhere in the corpus is `-- MAGIC %py`, a documented
language alias, and it lexes fine.

## Retired from the queue

**`DOUBLE PRECISION` is not a Databricks gap.** The
[DOUBLE type reference](https://docs.databricks.com/aws/en/sql/language-manual/data-types/double-type)
gives the syntax as `DOUBLE`, with no `PRECISION` spelling. The only corpus
file containing it is `create_raw_tags.sql`, which the "Not gaps" section below
already records as Lakebase — Databricks **PostgreSQL**, not Databricks SQL.
It came from the retired parser's inventory and should not have been carried
over. (Incidentally SQLFluff *does* accept `CAST(x AS DOUBLE PRECISION)` today,
inherited from ANSI; only the column-definition path rejects it. Tightening
that is not worth a pull request.)

## Templating, not dialect

Four corpus files fail on parameter syntax rather than grammar. SQLFluff's
`placeholder` templater with `param_style = dollar` already handles `${name}`
and `$name`, declared or not. It does **not** handle:

| shape | example |
| --- | --- |
| dotted | `${test.nrows}` |
| dashboard | `{{ station_list }}` |
| empty | `${}` |

`src/dbsqlparse/preprocess.py` is the reference implementation for all three
and is kept for that reason. The fix upstream is widening the `dollar` regex
in `src/sqlfluff/core/templaters/placeholder.py`, or adding a `databricks`
param style.

## Not gaps

Recorded so they are not re-investigated:

- `PipelineSetting.json.sql` — JSON with a `.sql` extension.
- `create_raw_tags.sql` — Lakebase (Databricks **PostgreSQL**), not Databricks
  SQL. `TEXT PRIMARY KEY`, `DOUBLE PRECISION`.

## Landed

| PR | construct | state |
| --- | --- | --- |
| [#8507](https://github.com/sqlfluff/sqlfluff/pull/8507) | magic cell body after a single-line directive | **merged** |
| [#8508](https://github.com/sqlfluff/sqlfluff/pull/8508) | materialized view declaring only expectations | **merged** |
| [#8509](https://github.com/sqlfluff/sqlfluff/pull/8509) | `PRIVATE` streaming tables, `CREATE FLOW` append flows (closes #8455) | **merged** |
| [#8510](https://github.com/sqlfluff/sqlfluff/pull/8510) | `DESC HISTORY` / `DESC DETAIL` | **merged** |
| [#8511](https://github.com/sqlfluff/sqlfluff/pull/8511) | `CREATE CATALOG … MANAGED LOCATION` | open |
| [#8512](https://github.com/sqlfluff/sqlfluff/pull/8512) | `READ`/`WRITE VOLUME` privileges, `VOLUME` securable | open |
| [#8513](https://github.com/sqlfluff/sqlfluff/pull/8513) | `LIVE` / `STREAMING LIVE` views | open |
| [#8514](https://github.com/sqlfluff/sqlfluff/pull/8514) | `DESCRIBE HISTORY` / `DESCRIBE DETAIL` as relations | open |
| [#8515](https://github.com/sqlfluff/sqlfluff/pull/8515) | `EXECUTE IMMEDIATE` | open |
| [#8516](https://github.com/sqlfluff/sqlfluff/pull/8516) | `SHOW GRANTS` | open |
| [#8517](https://github.com/sqlfluff/sqlfluff/pull/8517) | `CONVERT TO DELTA <table>` | open |

All four of the first batch merged on 2026-09-18.

`CREATE TEMPORARY STREAMING LIVE VIEW` turned out not to be a missing feature
but a **regression in the `databricks` dialect**: `sparksql` parses it and has
a fixture for it, while `databricks` does not.
[#7405](https://github.com/sqlfluff/sqlfluff/pull/7405) separated `CREATE VIEW`
from `CREATE MATERIALIZED VIEW` by writing a fresh segment instead of
subclassing, and `OR REFRESH`, `STREAMING` and `LIVE` were dropped with it.
Worth remembering when reading a gap: check the sibling dialect before
assuming SQLFluff never supported something.

## Unverified divergences

Behaviour where SQLFluff differs from Apache Spark, but the Databricks and
Spark documentation does not settle which is right. Recorded rather than
filed, so they are not re-investigated from scratch.

| form | Spark / the retired parser | SQLFluff |
| --- | --- | --- |
| `SET spark.sql.foo =` (empty value) | accepted | rejected |

Spark's reference gives `SET property_key[ = property_value ]`, which reads as
either `SET key` or `SET key = value` and says nothing about an empty value.
The corpus contains no instance either way. `corpus/mutate.py` keeps its
`_in_set_statement` guard regardless, because skipping a mutation is the safe
direction.

## Where the numbers stand

Measured 2026-09-18 against the 867-file corpus, `databricks` dialect.

| source | released 4.3.0 | `main` with the four merged |
| --- | ---: | ---: |
| `dbx-learn-databricks` | 28.3% | **89.1%** |
| `dbx-dlt-notebooks` | 73.7% | **94.7%** |
| `dbx-lakeflow-connector` | 92.6% | **94.4%** |

Overall recall on `main` after the four merges: **757/866 = 87.4%**, with
rejection holding at 100% of guaranteed-invalid mutations. Thirty-three files
that could not be parsed at all now parse. Most of that is #8507: a notebook
whose magic cells do not lex fails as a whole file, so one lexer fix moves a
lot of files at once.

The six pull requests still open add one corpus file each, except
`CONVERT TO DELTA`, which adds none — no published SQL on hand converts a
registered table, so that one rests on the reference rather than on an
observed failure.

## Measurement artefacts

Things that move the corpus numbers without anything having got better or
worse. Recorded so the next person does not chase them.

**`spark-sql-tests` fell 74.7% → 72.7% between released SQLFluff 4.3.0 and
`main`** (measured 2026-09-18). Six files: `cte.sql`,
`double-quoted-identifiers.sql`, `ilike-all.sql`, `ilike-any.sql`,
`like-all.sql`, `like-any.sql`. Every one fails on empty parentheses —
`WITH t() AS (SELECT 1)`, `LIKE ALL ()` — and every one is labelled in Spark's
own source as a negative case (`-- negative case`, `-- CTE with empty column
alias list is not allowed`). Upstream got **stricter**, which recall scores as
a loss because the harness treats every file as valid SQL. Do not "fix" it.

The lesson generalises: before attributing a corpus change to your own branch,
measure clean `upstream/main` as a control. All three branches measured on
2026-09-18 showed this same −2.0 pt, and none of them caused it.
