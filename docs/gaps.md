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

`CREATE SCHEMA` shares two of those clauses. `CREATE SCHEMA s DEFAULT
COLLATION UTF8_BINARY` and `CREATE SCHEMA s RETAIN DROPPED FOR 14 DAYS` are
rejected on the same engine state, pinned by `create-schema.default-collation`
and the `create-schema.retain-dropped-*` cases. The rest of the CREATE SCHEMA
clause list parses, including `MANAGED LOCATION` — that clause was #8511's
gap on CREATE CATALOG, not on CREATE SCHEMA.

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

**`CREATE TABLE` rejects two documented table clauses and accepts three
non-conforming forms.** The
[CREATE TABLE [USING] reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using)
clause list includes `LOCATION path [ WITH ( CREDENTIAL credential_name ) ]`
and `DEFAULT COLLATION default_collation_name`, and its top-level statement is
three exclusive alternatives: `[CREATE OR] REPLACE { TEMP | TEMPORARY } TABLE`,
`CREATE [EXTERNAL] TABLE [ IF NOT EXISTS ]` and `CREATE { TEMP | TEMPORARY }
TABLE`. On `main` at `33d8c8459` and released 4.3.0:

| form | reference | databricks |
| --- | --- | --- |
| `CREATE TABLE t (a INT) LOCATION 's3://b/t' WITH (CREDENTIAL cred)` | must parse | rejected |
| `CREATE TABLE t (a STRING) DEFAULT COLLATION UTF8_BINARY` | must parse | rejected |
| `CREATE TEMP EXTERNAL TABLE t (a INT)` | must reject | accepted |
| `CREATE OR REPLACE TEMP TABLE IF NOT EXISTS t (a INT)` | must reject | accepted |
| `CREATE TABLE t (CONSTRAINT pk PRIMARY KEY (a))` | must reject | accepted |

The root cause is a wiring gap. Databricks defines a
`CreateTableUsingStatementSegment` (`dialect_databricks.py:1946`) whose clause
set is the Databricks `TableClausesSegment`, and that segment lists
`LocationWithCredentialGrammar` (`dialect_databricks.py:344`) -- the
credential-aware location that would close the first gap. But neither name is
inserted into `StatementSegment` (`dialect_databricks.py:1669`), so
`CREATE TABLE` is parsed by the inherited SparkSQL `TableDefinitionSegment`
(`dialect_sparksql.py:910`): its clause set is the SparkSQL `AnySetOf(...)`,
which has no `DEFAULT COLLATION` and reaches the plain `LocationGrammar`, and
its loose `OrReplace? Temporary? EXTERNAL? TABLE IfNotExists?` prefix is what
accepts the two mixed forms. The constraint-only column list comes from the
same segment's `OneOf(ColumnFieldDefinitionSegment, TableConstraintSegment)`,
which lets a table constraint take the place of the required first column.

Pinned by the reference corpus as `create-table.location-credential`,
`create-table.default-collation`, `create-table.external-temp`,
`create-table.replace-with-if-not-exists` and
`create-table.constraint-without-column`. Found 2026-09-20 by the Tier 2
batch; no corpus file uses any of the five. `CREATE CATALOG ... DEFAULT
COLLATION` is a separate, already-open gap (`create-catalog.default-collation`).

**`ALTER TABLE` rejects twelve documented clauses.** The
[ALTER TABLE reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-table)
lists 29 clause alternatives; the Databricks `AlterTableStatementSegment`
(`dialect_databricks.py:1311`) and the SparkSQL base it extends have no
grammar for twelve of them. On `main` at `33d8c8459` and released 4.3.0:

| repro | case |
| --- | --- |
| `ALTER TABLE t ALTER COLUMN a COMMENT 'x', b COMMENT 'y'` | `alter-table.alter-column-multi` |
| `ALTER TABLE t DEFAULT COLLATION UTF8_BINARY` | `alter-table.default-collation` |
| `ALTER TABLE t SET EXTERNAL` | `alter-table.set-external` |
| `ALTER TABLE t SET EXTERNAL DRY RUN` | `alter-table.set-external-dry-run` |
| `ALTER TABLE t SET MANAGED` | `alter-table.set-managed` |
| `ALTER TABLE t SET MANAGED MOVE` | `alter-table.set-managed-move` |
| `ALTER TABLE t SET MANAGED COPY` | `alter-table.set-managed-copy` |
| `ALTER TABLE t SET MANAGED TRUNCATE UNIFORM HISTORY` | `alter-table.set-managed-truncate` |
| `ALTER TABLE t UNSET MANAGED` | `alter-table.unset-managed` |
| `ALTER TABLE t UNSET MANAGED TRUNCATE UNIFORM HISTORY` | `alter-table.unset-managed-truncate` |
| `ALTER TABLE t REPLACE PARTITIONED BY WITH CLUSTER BY (a)` | `alter-table.replace-partitioned-cluster` |
| `ALTER TABLE t REPLACE PARTITIONED BY WITH CLUSTER BY AUTO` | `alter-table.replace-partitioned-cluster-auto` |

The multi-column form is the documented example shape: the page shows
`ALTER TABLE table ALTER COLUMN bool COMMENT 'boolean column', num AFTER bool,
str AFTER num, bool SET DEFAULT true`, and the single-column clauses (`AFTER`,
`COMMENT`, `SET DEFAULT`) each parse — only the comma list does not. The other
eleven are whole clauses absent from the grammar, several of them exotic
(Unity Catalog foreign-table conversion and predictive optimization); the
table `DEFAULT COLLATION` is the same missing clause as the CREATE TABLE gap
above. Found 2026-09-20 by the Tier 2 batch; no corpus file uses any of the
twelve.

**`CREATE FUNCTION` rejects the Scala/Java surface and `ENVIRONMENT`, and
accepts three non-conforming forms.** The
[CREATE FUNCTION reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-sql-function)
covers `LANGUAGE SQL`/`PYTHON`/`SCALA`/`JAVA`, the `ENVIRONMENT` and
`HANDLER` clauses, and a `DEFAULT COLLATION` characteristic.
`FunctionDefinitionGrammar` (`dialect_databricks.py:1726`) binds only
`LANGUAGE { SQL | PYTHON }` (`dialect_databricks.py:1733`), with no
`ENVIRONMENT`, `HANDLER` or default collation, so on `main` at `33d8c8459`
and released 4.3.0:

| form | reference | databricks |
| --- | --- | --- |
| `CREATE FUNCTION f(x INT) RETURNS INT LANGUAGE SCALA ENVIRONMENT (java_dependencies = '["x.jar"]') HANDLER 'com.example.X.f'` | must parse | rejected |
| the same with `LANGUAGE JAVA` | must parse | rejected |
| `CREATE FUNCTION f() RETURNS INT LANGUAGE PYTHON ENVIRONMENT (dependencies = '["a"]') AS $$ … $$` | must parse | rejected |
| `CREATE FUNCTION f(x STRING) RETURNS STRING DEFAULT COLLATION UTF8_BINARY RETURN x` | must parse | rejected |
| `CREATE OR REPLACE FUNCTION IF NOT EXISTS f() RETURNS INT RETURN 1` | must reject | accepted |
| `CREATE FUNCTION f() RETURNS INT CONTAINS SQL READS SQL DATA RETURN 1` | must reject | accepted |
| `CREATE FUNCTION f() RETURNS INT RETURN 1 AS $$ return 1 $$` | must reject | accepted |

The three accepted forms are exclusivity the grammar does not enforce: the
reference says `OR REPLACE` and `IF NOT EXISTS` cannot coexist, makes
`CONTAINS SQL` and `READS SQL DATA` alternatives of one bracket, and makes
`AS`/`RETURN`/`HANDLER` exclusive body forms. The `OR REPLACE` /
`IF NOT EXISTS` pair is the same over-acceptance the CREATE TABLE entry
records, on a second statement; `DEFAULT COLLATION` is the same missing
characteristic family as CREATE TABLE, ALTER TABLE and CREATE SCHEMA. Pinned
by `create-function.*`; found 2026-09-20 by the Tier 2 batch; no corpus file
uses any of the seven.

**`MERGE WITH SCHEMA EVOLUTION` is rejected.** The
[MERGE INTO reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into)
gives the statement start as `MERGE [ WITH SCHEMA EVOLUTION ] INTO
target_table_name …`, and documents the clause (Databricks Runtime 15.2+) as
enabling automatic schema evolution, with a worked example. On `main` at
`33d8c8459` and released 4.3.0,
`MERGE WITH SCHEMA EVOLUTION INTO t USING s ON t.k = s.k WHEN MATCHED THEN
UPDATE SET *` is rejected at position 1, while the same statement without the
clause parses. Pinned by `merge-into.with-schema-evolution`. Found 2026-09-20
by the Tier 2 batch. The rest of the MERGE grammar — all three WHEN branches,
the DELETE / UPDATE SET / INSERT actions, `EXCEPT`, aliases and a leading CTE —
parses and is pinned green.

**`COPY INTO` is unsupported by the databricks dialect.** The
[COPY INTO reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-copy-into)
defines `COPY INTO target_table [ BY POSITION | ( col_name … ) ] FROM {
source_clause | ( SELECT … FROM source_clause ) } FILEFORMAT = data_source
[ VALIDATE … ] [ FILES = ( … ) | PATTERN = … ] [ FORMAT_OPTIONS ( … ) ]
[ COPY_OPTIONS ( … ) ]`, with a `source_clause` carrying optional `CREDENTIAL`
and `ENCRYPTION`. SQLFluff implements `COPY INTO` for `tsql` and `snowflake`
only — neither `sparksql` nor `databricks` has any grammar — so on `main` at
`33d8c8459` and released 4.3.0 every form is rejected at position 1, including
`COPY INTO t FROM 's3://b/p' FILEFORMAT = CSV` and the fourteen other
documented variants. A corpus file (the `dbx-devrel` SCD notebook) already
fails here, so the gap was known; the reference corpus now pins the full
production and its fifteen partial forms as `copy-into.*`. The partial
rejections report vacuous until the statement lands. Recorded 2026-09-20 by
the Tier 2 batch.

**`OPTIMIZE … FULL` is rejected.** The
[OPTIMIZE reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-optimize)
gives `OPTIMIZE table_name [FULL] [WHERE predicate] [ZORDER BY (col_name1
[, ...])]`. The databricks dialect parses the bare statement, `WHERE` and
`ZORDER BY` — including a multi-column list and a `WHERE … ZORDER BY` pair —
but rejects `FULL`: `OPTIMIZE events FULL` fails, and therefore
`OPTIMIZE events FULL WHERE date >= '2025-01-01'` (the documented replacement
for a bare `WHERE` on a liquid-clustering table, DBR 18.1+) and the
all-clauses combination. Pinned as `optimize.full`, `optimize.full-where` and
`optimize.all-clauses`. The five `FULL`-free cases parse and are pinned green.
Recorded 2026-09-20 by the Tier 2 batch.

**`VACUUM … FULL` and `VACUUM … LITE` are rejected.** The
[VACUUM reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-vacuum)
gives `VACUUM table_name { { FULL | LITE } | DRY RUN } [...]` for Iceberg
tables (DBR 16.1+), with a plain `VACUUM table_name` form for other tables.
The dialect parses `VACUUM t` and `VACUUM t DRY RUN` but rejects the two
modes: `VACUUM t FULL` and `VACUUM t LITE`. Pinned as `vacuum.full` and
`vacuum.lite`; the two partial rejections that mix the alternatives report
vacuous until the modes land. Recorded 2026-09-20 by the Tier 2 batch.

**The Unity Catalog connectivity and sharing DDL is unsupported.** Four
statements have no grammar in the `databricks` or `sparksql` dialect, so
every documented form is rejected at position 1:

- `CREATE CONNECTION c TYPE POSTGRESQL OPTIONS (host 'h')` — pinned by
  `create-connection.*` (eight must-parse cases, including `IF NOT EXISTS`,
  `COMMENT`, dotted and string-literal option keys, a `secret(...)` value and
  the standards-compliance `SERVER` synonym).
- `CREATE EXTERNAL LOCATION l URL 'u' WITH (STORAGE CREDENTIAL c)` — pinned
  by `create-external-location.*` (five cases, including backticked names).
- `CREATE SHARE customer_share` — pinned by `create-share.*` (four cases).
- `CREATE RECIPIENT r` — pinned by `create-recipient.*` (eight cases,
  including `USING ID`, dotted `PROPERTIES` keys, and the bracketed `=`).

These are the same class as the `COPY INTO` gap above — a whole statement
missing rather than a bracketed clause — and their partial rejections report
vacuous until a grammar lands. Recorded 2026-09-20 by the Tier 2 batch.

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
Fixed on `fix/sparksql-identifier-false-positives` (pushed 2026-09-20): the
`DescribeObjectGrammar` exclusion of `HISTORY`/`DETAIL` is gone, and the
Delta statements are tried before the general DESCRIBE instead, so the
collision resolves by fall-through rather than by exclusion.

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
keyword handling that #8509 touched, not in the lexer. Fixed on
`fix/sparksql-identifier-false-positives` (pushed 2026-09-20): `STREAM` is
a prefix keyword only when a table expression follows it, in both the
keyword position and the fallthrough.

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
`array-sort.lambda-keyword-parameters`. Fixed on
`fix/databricks-unreserve-identifiers` (verified +1 must-parse, suite 7038,
corpus `sqlfluff-sparksql` 124→125, mutation 1327/1327); the branch is pushed
and held for a PR slot while the throttle holds.

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
by `set-operators.parenthesised-operands`. The cause was the `EXCEPT` guard
meant for wildcard exclusions (`SELECT * EXCEPT (col)`), which refused any
bracketed operand; narrowed on
`fix/sparksql-parenthesised-set-operands` (verified +1 must-parse, suite
7030, rejection 1327/1327) — pushed, awaiting a PR slot.

**`KEYS`, `PIVOT` and `WINDOW` are rejected as unquoted column aliases.** The
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words)
lists only seventeen words that cannot be an unquoted table alias, and none of
these is among them; Spark's grammar declares all three non-reserved, and
sqlglot parses all three as aliases. Repros on `main` at `33d8c8459`:
`SELECT a AS KEYS FROM t;`, `SELECT a AS PIVOT FROM t;`,
`SELECT a AS WINDOW FROM t;` are all rejected at `AS`, while `FETCH` and
`OVERLAPS` behave the same way. Found 2026-09-19 by
`scripts/fuzz_variants.py keywords`; no upstream issue found for the alias
position. Fixed together with LEFT/RIGHT on
`fix/databricks-unreserve-identifiers`: the alias grammar is split so an
explicit `AS` alias may use the three, while an implicit alias still cannot
consume a following clause keyword.

**A `%`-prefixed `-- MAGIC` line inside a magic cell ends the cell.**
Databricks notebook source marks every line of a magic cell with
`-- MAGIC`; the language is named by the first directive, and a later line
may also start with `%` — an `%md` cell quoting `%pip`, for example. The
grammar allowed only plain body lines after the directive, so the
`%`-prefixed line ended the cell and the rest of the file was unparsable.
Repro:

```
-- MAGIC %md
-- MAGIC Some prose quoting a magic command:
-- MAGIC %pip within a Python notebook.
```

Found 2026-09-20 by the corpus (`dbx-learn-databricks`
`my_streaming_table.sql`, a cell quoting a `%pip` warning). Fixed on
`fix/databricks-magic-cell-percent-line` (pushed): directive-shaped lines
are body text once a cell is open, and the corpus file parses
(`dbx-learn-databricks` 43/46 → 44/46, zero regressions).

Two adjacent lexer-regex quirks are **fixed** on
`fix/databricks-magic-cell-boundaries` (the branch also carries the
`%`-prefixed-line grammar change, so the whole notebook boundary surface is
one PR):

- `magic_start` consumed its trailing `(\r?\n)`, and the `[^%]` in
  `magic_single_line` / `magic_line` could match one. A `-- MAGIC` line
  with a trailing space, or a cell whose last line is a standalone
  directive, therefore swallowed the blank line the `command` separator
  needs and the next statement was unparsable. The two corpus cases are the
  `dbx-devrel` SCD file (`-- MAGIC %fs rm -r …` with a trailing space) and
  a cell ending in `-- MAGIC %fs`.
- Fixing it means matching only `[^\n%]` in the line bodies and leaving the
  newline to the lexer. Those regexes are baked into the Rust lexer at
  build time, so a local measurement needs `utils/rustify.py build` plus a
  `maturin develop` rebuild; upstream CI does that as part of installing
  the package.

With the boundary fixed, the SCD file parses past the magic cells and now
fails later, on `COPY INTO` (line 151) — a different, already-queued gap,
not a regression. The boundary cases are pinned in `databricks_test.py`
rather than in a fixture, because pre-commit strips the trailing space one
of them is made of.

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

Databricks parameter syntax is not Jinja. Notebook widget parameters
(`${name}`, `${dotted.name}`, `$name`, `${}`) and dashboard parameters
(`{{ name }}`) appear in corpus SQL, and SQLFluff's `placeholder` templater
with `param_style = dollar` covers only the first of those shapes. The
`databricks` param_style now on
`fix/templater-placeholder-databricks-params` (pushed 2026-09-20) covers all
four, with the empty `${}` falling back to the positional counter.

The corpus now measures with that syntax configured (`SqlFluffRunner` passes
the equivalent `param_regex`, so released SQLFluff can still run the
baseline). Effect on the corpus: `dbx-dlt-notebooks` goes 18/19 → 19/19 on
the dashboard file, failures 104 → 103, zero regressions, mutation 100%.

Four files still fail on parameter syntax *and* something else, so the
templater alone does not flip them — each needs its own fix:

| file | remaining blocker |
| --- | --- |
| `my_streaming_table.sql` | a `-- MAGIC %pip` mention inside an `%md` cell (unit 10) |
| `identifier-clause.sql` | Spark's `SET hivevar:name = value` |
| `Generating Surrogate Keys.sql` | `count(DISTINCT sk)FROM` without whitespace |
| `Clean Up.sql` | `USE CATALOG ${catalog}` left unterminated before the next statement |

`src/dbsqlparse/preprocess.py` remains the reference implementation for the
parameter shapes and is kept for that reason.

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
