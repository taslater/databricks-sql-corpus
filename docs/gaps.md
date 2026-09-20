# SQLFluff Databricks gap queue

The upstream work queue. Every entry is a construct that appears in published
Databricks SQL or in the Databricks SQL reference and that SQLFluff's
`databricks` dialect cannot parse, with a minimal reproduction verified
against SQLFluff `main`. Cases in `corpus/reference/` cite the reference page;
where one pins an entry, its id is named.

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
author's reduced rebase or as a follow-up PR. No corpus file exercises it,
so it is recorded from the reference and #8460's fixture rather than from a
failure count. The reference corpus now pins both halves:
`create-flow.append-replace-using-sequence-by` must parse (it does not) and
`create-flow.replace-using-without-sequence-by` must be rejected (it is
accepted).

**`DROP MATERIALIZED VIEW`** is unparsable in the `databricks` dialect as of
SQLFluff 4.3.0. Repro: `DROP MATERIALIZED VIEW mv;`. Found 2026-09-19 by the
semantic-model tests in `sqlfluff-plugin-conventions`, not by this corpus —
no corpus file needs it yet, so it is queued rather than claimed. Databricks
documents the construct, so `DropViewStatementSegment` should accept the
`MATERIALIZED` keyword the same way `CreateMaterializedViewStatementSegment`
already exists; belongs in an upstream PR when picked up. Pinned by the
reference corpus as `drop-view.materialized` and
`drop-view.materialized-if-exists`.

**Inline `FLOW` clauses on `CREATE STREAMING TABLE` are unparsable.** The
[CREATE STREAMING TABLE reference](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-streaming-table)
gives the statement as
`CREATE [OR REFRESH] [PRIVATE] STREAMING TABLE table_name [ … ] [ { flow_clause | AS query } ]`,
with `flow_clause` one of `FLOW { INSERT [ONCE] BY NAME query | AUTO CDC … |
REPLACE WHERE … | REPLACE USING ( column_name [, …] ) SEQUENCE BY sequence_column BY NAME query }`,
and its examples use both `FLOW INSERT BY NAME` and
`FLOW REPLACE USING (…) SEQUENCE BY … BY NAME`. The `databricks` dialect
rejects every one of them: `PRIVATE` is patched onto
`CreateTableStatementSegment` and the separate `CreateFlowStatementSegment`
handles the statement form, so there is no FLOW clause on the table statement
at all. Repro:
`CREATE OR REFRESH STREAMING TABLE t FLOW INSERT BY NAME SELECT * FROM STREAM s;`.
Found 2026-09-19 by the reference corpus
(`create-streaming-table.inline-insert-flow`) — the first gap it found on its
own, and exactly the class the scraped corpus cannot see: no published file
uses the construct, so recall had nothing to fail on.

**`CREATE CATALOG` covers only part of its clause set.** On `main` at
`33d8c8459`, `CreateCatalogStatementSegment` accepts a name and `COMMENT`
only. The
[CREATE CATALOG reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-catalog)
documents five clause alternatives and a second production, and the rest are
rejected. Each repro is pinned by the reference corpus case named beside it:

| repro | case |
| --- | --- |
| `CREATE CATALOG c USING SHARE provider.share` | `create-catalog.using-share` |
| `CREATE CATALOG c RETAIN DROPPED FOR 30 DAYS` | `create-catalog.retain-dropped-days` |
| `CREATE CATALOG c DEFAULT COLLATION UTF8_BINARY` | `create-catalog.default-collation` |
| `CREATE CATALOG c OPTIONS (k = 'v')` | `create-catalog.options` |
| `CREATE FOREIGN CATALOG fc USING CONNECTION conn OPTIONS (k = 'v')` | `create-catalog.foreign` |

`MANAGED LOCATION` is [#8511](https://github.com/sqlfluff/sqlfluff/pull/8511)'s
territory; the other clauses have no pull request. The foreign-catalog
production is a whole statement form, not a clause: it takes
`USING CONNECTION` and `OPTIONS` both unbracketed, and the reference corpus
rejects their partial forms (`create-catalog.foreign-without-connection`,
`create-catalog.foreign-without-options`).

**`CREATE VIEW` lost its data-source production.** The
[CREATE VIEW reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-view)
gives a second production, `CREATE [ OR REPLACE ] [ GLOBAL ] TEMPORARY VIEW
[ IF NOT EXISTS ] view_name [ column_list ] USING data_source [ OPTIONS
( option_key [ = ] option_value [, ...] ) ]`, and it is rejected by
`databricks` — `TemporaryViewUsingSegment` is not part of the rewritten
`CreateViewStatementSegment`, though `sparksql` still carries `USING` and
`OPTIONS`. That is the same #7405 rewrite whose LIVE/STREAMING loss #8513
repairs, and #8513 does not restore these. Repro:
`CREATE TEMPORARY VIEW v USING csv OPTIONS (path '/data');` — cases
`create-view.using-data-source`, `create-view.using-data-source-without-options`
and `create-view.using-data-source-equals`. The parenthesised clause list
`WITH ( SCHEMA BINDING )` from the `with_clause` production is rejected too
(`create-view.with-parenthesised-clause`). No pull request covers either.

**Per-field `NOT NULL` and `COLLATE` are rejected in `STRUCT` types.** The
[STRUCT type reference](https://docs.databricks.com/aws/en/sql/language-manual/data-types/struct-type)
gives the field production as
`fieldName [:] fieldType [NOT NULL] [COLLATE collationName] [COMMENT str]`,
inside `STRUCT < [ … ] >`. `COMMENT str` parses; `NOT NULL` and
`COLLATE collationName` do not. Repros:
`CREATE TABLE t (s STRUCT<a: INT NOT NULL>)` and
`CREATE TABLE t (s STRUCT<a: STRING COLLATE UTF8_BINARY>)`. Pinned by the
reference corpus as `struct.not-null`, `struct.not-null-with-comment` and
`struct.collate`; the partial forms `STRUCT<a: INT NOT>` and
`STRUCT<a: STRING COLLATE>` are pinned too, but report vacuous until the gap
closes. Found 2026-09-19 by the Tier 1.5 batch; no corpus file uses either
clause, so it is recorded from the reference.

**The JSON path `[ * ]` wildcard is rejected.** The
[JSON path expression reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-json-path-expression)
gives the accessor production as
`{ { identifier | [ field ] | [ * ] | [ index ] } [ . identifier | [ field ] | [ * ] | [ index ] ] [...] }`,
and the page navigates arrays with it in its own examples. SQLFluff `main` at
`33d8c8459` rejects every probed position, including the documented shape
`SELECT raw:store.book[*] FROM t`; `[0]` and `['field']` in the same position
parse. Pinned by `json-path.star`. The page notes `[ * ]` is not supported
for `VARIANT`, and the case navigates a STRING path. Found 2026-09-19 by the
reference corpus, the first gap of the Tier 1.5 batch — the tier was expected
to be pure regression-pinning, and its probes had not covered `[ * ]`.

**Delimited identifiers are rejected in a JSON path.** The
[same reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-json-path-expression)
shows backticked field names in its delimiter examples ("Use backticks to
escape special characters"), and its `identifier` production links to the
identifiers page, where a delimited identifier is a spelling of the same
production. SQLFluff `main` rejects a JSON path field written as a delimited
identifier, with or without characters that need escaping:
``SELECT raw:`full name` FROM t``, ``SELECT raw:`owner` FROM t`` and
``SELECT raw:`fb:testid` FROM t`` are all rejected, while the plain
identifier parses. Pinned by `json-path.delimited-identifier`. Also found
2026-09-19 by the Tier 1.5 batch.

**`DESCRIBE history.tbl` is rejected while `DESCRIBE TABLE` is accepted.**
A qualified table whose first part is `history` collides with the
`DESCRIBE HISTORY` statement prefix. The
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words)
states Databricks "does not formally disallow any specific literals from being
used as identifiers", and `history` is not in the alias-only exception list, so
the rejection is a false positive on a legal table name. Repros on `main` at
`33d8c8459`:

| form | result |
| --- | --- |
| `DESCRIBE history.tbl;` | rejected at position 1 |
| `DESCRIBE TABLE history.tbl;` | parses |
| ``DESCRIBE `history`.tbl;`` | parses |
| `DESCRIBE HISTORY tbl;` | parses (the statement, #8510) |

Found 2026-09-19 by the sqlglot differential (`make diff`), which reproduces
sqlglot's own fixture `tests/dialects/test_databricks.py:38`; verified against
`main` in the `.venv-main` worktree. Pinned by the reference corpus as
`describe-table.qualified-history` once the identifiers page is transcribed.

**`SELECT * FROM stream` is rejected for a table named `stream`.** `STREAM` is
part of the `FROM STREAM <function>` relation spelling, and the dialect
reserves it in table position, but the
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words)
does not list it among the words that need backticks. Repros on `main` at
`33d8c8459`:

| form | result |
| --- | --- |
| `SELECT * FROM stream;` | rejected at `FROM stream` |
| `SELECT * FROM \`stream\`;` | parses |
| `SELECT 1 FROM t AS stream;` | parses (alias position is fine) |

Same discovery path as the entry above (sqlglot fixture
`tests/dialects/test_databricks.py:33`). The fix belongs with the `STREAM`
keyword handling that #8509 touched, not in the lexer.

**`left` and `right` are globally reserved in `databricks`, undoing a merged
`sparksql` fix.** #8050 (merged 2026-07-07) treats LEFT/RIGHT as
non-reserved in `sparksql` so they can be lambda variables (#5004), with the
comment that `JoinTypeKeywordsGrammar` still matches them so `LEFT|RIGHT
[OUTER] JOIN` keeps working. `databricks` never got it: the dialect clears the
inherited set and installs its own, `databricks_dialect.sets(
"reserved_keywords").clear()` / `.update(RESERVED_KEYWORDS)`
(`dialect_databricks.py:54-55`), and that list contains `LEFT` and `RIGHT`
(`dialect_databricks_keywords.py:15,19`). The
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words)
puts them only in the alias-only list -- they need backticks *as a table
alias*, not everywhere. Repros on `main` at `33d8c8459`:

| form | databricks | sparksql |
| --- | --- | --- |
| `SELECT array_sort(ARRAY(3, 1), (left, right) -> CASE WHEN left < right THEN -1 ELSE 1 END);` | rejected | parses |
| `SELECT left FROM t;` | rejected | parses |
| `SELECT * FROM left;` | rejected | parses |
| `SELECT * FROM t AS left;` | rejected (correct -- alias needs backticks) | rejected |

Found 2026-09-19 by `scripts/fuzz_variants.py keywords`, with the regression
confirmed by the databricks-vs-sparksql comparison. The fix is to drop
LEFT/RIGHT from `RESERVED_KEYWORDS` and enforce the alias restriction where
aliases are parsed. Pinned by the reference corpus as
`array-sort.lambda-keyword-parameters`.

**Parenthesised set-operation operands are rejected.** The
[set operators reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-setops)
shows `(SELECT c FROM number1) INTERSECT (SELECT c FROM number2)` in its own
examples, and the scraped corpus fails it too (Spark's `q87.sql`, the
`EXCEPT DISTINCT` entries). Repro on `main` at `33d8c8459`:
`(SELECT c FROM number1) EXCEPT (SELECT c FROM number2);` is rejected, while
the same query without per-operand parentheses parses.
[#8523](https://github.com/sqlfluff/sqlfluff/pull/8523) (open, 2026-09-19)
adds the `DISTINCT` qualifier on `EXCEPT`/`MINUS` but not parenthesised
operands, so this is unclaimed. Found by the sqlglot round-trip probe; pinned
by `set-operators.parenthesised-operands`.

**`KEYS`, `PIVOT` and `WINDOW` are rejected as unquoted column aliases.** The
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words)
lists only seventeen words that cannot be an unquoted table alias, and none of
these is among them; Spark's grammar declares all three non-reserved, and
sqlglot parses all three as aliases. Repros on `main` at `33d8c8459`:
`SELECT a AS KEYS FROM t;`, `SELECT a AS PIVOT FROM t;`,
`SELECT a AS WINDOW FROM t;` are all rejected at `AS`, while `FETCH` and
`OVERLAPS` behave the same way. Found 2026-09-19 by
`scripts/fuzz_variants.py keywords`; no upstream issue found for the alias
position.

**Over-acceptance: `GRANT ALL PRIVILEGES, SELECT` parses.** The
[GRANT reference](https://docs.databricks.com/aws/en/sql/language-manual/security-grant)
gives `privilege_types` as `{ ALL PRIVILEGES | privilege_type [, ...] }` —
exclusive alternatives. SQLFluff accepts the mixed form:
`GRANT ALL PRIVILEGES, SELECT ON TABLE t TO p`. The reference corpus case is
`grant.all-privileges-in-list`, and it is the only over-acceptance the Tier 1
batch found other than the known #8509 one. This wants a grammar that binds
the choice, not a widening: it is the quiet failure direction, invisible to
recall and to every fixture that only checks positive forms.

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
  three together and needs six or so new keywords. The reference corpus now
  pins the whole list: `privileges.yml` carries one must-parse case per
  securable in the production (`privileges.catalog` … `privileges.volume`),
  plus the partial forms its brackets allow, and `show_grants.yml` pins the
  statement's own shape. On `main` the `SHOW GRANTS` statement itself is
  unimplemented (#8516), so its rejection cases report **vacuous** rather than
  informative until that merges; the GRANT half of the list stays informative.
  `READ`/`WRITE VOLUME` as privilege types are #8512's, pinned by
  `grant.read-volume-privilege` and `grant.write-volume-privilege`.
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
rejected and a test asserts it. The reference corpus pins it as
`execute-immediate.*`: eight must-parse cases across `INTO` and `USING`, and
four rejection boundaries for their partial forms. On `main` the whole
statement is rejected, so those rejections are vacuous until #8515 merges.

**`CONVERT TO DELTA` was mis-recorded.** `NO STATISTICS` had been supported all
along — `Sequence("NO", "STATISTICS", optional=True)` is already in
`ConvertToDeltaStatementSegment`. The real gap was the target: the grammar took
only a `FileReferenceSegment`, so a path parsed while `CONVERT TO DELTA
my_table` did not. The
[reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-convert-to-delta)
is explicit that table_name is "either an optionally qualified table
identifier or a path". The reference corpus pins the target as
`convert-to-delta.table` and `convert-to-delta.qualified-table`, with
`convert-to-delta.path` keeping the form the dialect already accepted.

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
