# Upstream PR plan: the whole queue

This is the master runsheet for getting **all** of the SQLFluff Databricks work
upstream, not just the reference-corpus batch. `docs/pr-queue.md` remains the
detail record for the reference batch (its units, tips, bases and measured
deltas); this file is the plan over everything, and supersedes it as the thing
to read first when deciding what to open next.

## Objective and sizing rule

Every construct we built lives in `taslater/sqlfluff` as a branch or as a
commit on `personal/databricks-complete`. All of it is to be submitted, in
**hard bundles**: one PR per statement family or problem class, not one per
construct. The rule is the merged-PR precedent already recorded in
`docs/pr-queue.md`: review load tracks *scope coherence*, not diff size
(generated `.yml` dominates line counts), and recent merges bundle a whole
statement family (`ATTACH`/`DETACH`/`VACUUM`/`REINDEX`/`ANALYZE`, DuckDB
`INSTALL`/`LOAD`) while never crossing unrelated statements.

**If the maintainers push back on a bundle, split at the seam the bundle
table names.** Every bundle's constituent branches are preserved (tips below),
so splitting is mechanical and loses no work.

## Status legend

- **merged** — landed upstream; nothing to do.
- **open** — PR exists; land it (some are drafts to un-draft).
- **branch** — branch exists in `taslater/sqlfluff`, no PR yet.
- **slice** — only exists inside `personal/databricks-complete`; must be cut
  into a bundle branch.

Base for every new bundle is `upstream/main` unless noted; rebase before
opening, and stack where the table says so.

---

## Wave 0 — the eight PRs already in review

No new work; un-draft and land. Retry the throttled `gh pr ready`/`gh pr
create` calls (the block is bursty and mutation-specific).

| PR | construct | state |
| --- | --- | --- |
| [#8512](https://github.com/sqlfluff/sqlfluff/pull/8512) | `READ`/`WRITE VOLUME` privileges, `VOLUME` securable | open |
| [#8513](https://github.com/sqlfluff/sqlfluff/pull/8513) | `LIVE` / `STREAMING LIVE` views (also carries unit 3) | open |
| [#8515](https://github.com/sqlfluff/sqlfluff/pull/8515) | `EXECUTE IMMEDIATE` | open |
| [#8516](https://github.com/sqlfluff/sqlfluff/pull/8516) | `SHOW GRANTS` | open |
| [#8517](https://github.com/sqlfluff/sqlfluff/pull/8517) | `CONVERT TO DELTA <table>` | **ready** |
| [#8519](https://github.com/sqlfluff/sqlfluff/pull/8519) | `DROP MATERIALIZED VIEW` | **draft** |
| [#8520](https://github.com/sqlfluff/sqlfluff/pull/8520) | inline `FLOW` on `CREATE STREAMING TABLE` | **draft** |
| [#8522](https://github.com/sqlfluff/sqlfluff/pull/8522) | `NOT NULL` / `COLLATE` on a `STRUCT` field | **draft** |

Merged already: #8507, #8508, #8509, #8510, #8511, #8514.

---

## Wave 1 — cross-cutting fixes (independent, small)

These touch a subsystem rather than a statement, so they stand alone.

| bundle | title | scope | provenance |
| --- | --- | --- | --- |
| **CORE** | Treat a closing bracket as a code boundary for keyword terminators | the general `(a)FROM t` bug: a keyword after `)`/`]`/`}` terminates a clause instead of being eaten as an implicit alias; both engines | branch `core/keyword-terminator-after-bracket` `cea2c68d6` (Python + Rust mirror) |
| **TMPL** | Placeholder templater: a Databricks parameter style | `${name}`, `${dotted.name}`, `${}`, `$name`, `{{ name }}` | branch `fix/templater-placeholder-databricks-params` `eb35e1c62` (unit 8) |
| **LEX** | Keep notebook magic-cell boundaries out of the lexer | `%`-prefixed `-- MAGIC` line inside an `%md` cell; `magic_start` / `magic_single_line` / `magic_line` regexes | branch `fix/databricks-magic-cell-boundaries` `1625e1051` (unit 10) |

## Wave 2 — statement-family and problem-class bundles

| bundle | title | scope | provenance | reconcile with |
| --- | --- | --- | --- | --- |
| **PARSER** | SparkSQL/Databricks: identifier and keyword false positives, JSON paths, set operands | `LEFT`/`RIGHT` unreserved (#8050 regression); `KEYS`/`PIVOT`/`WINDOW` as explicit aliases; `DESCRIBE history.tbl`; `SELECT * FROM stream`; `IDENTIFIER(...)` as a column and `IDENTIFIER()` rejected; JSON path `[ * ]` and delimited identifiers; bracketed subquery as a set-operation operand | branches `fix/databricks-identifier-keyword-false-positives` `7f58e29d3` (7+9), `fix/databricks-json-path` `46aa4f86` (unit 5), `fix/sparksql-parenthesised-set-operands` `ff39472c` (unit 6) + the `IDENTIFIER`/`ColumnReferenceSegment` part of `personal/databricks-complete` `fbae1c591` | `fix/sparksql-identifier-false-positives` `163c2f23` is superseded — do not open |
| **ALTER** | Databricks: `ALTER` statements | `ALTER CATALOG`/`SCHEMA` clauses; `ALTER TABLE` clause set; `ALTER MATERIALIZED VIEW`/`STREAMING TABLE` (schedule); `ALTER SHARE`; `ALTER GROUP`; `ALTER CONNECTION`/`EXTERNAL LOCATION`/`CREDENTIAL`; `ALTER RECIPIENT`/`PROVIDER` | 7 branches: `alter-catalog-schema-clauses` `e86037b5`, `alter-connection-location-credential` `05877b64`, `alter-group` `bd1a1f09`, `alter-mv-streaming-schedule` `0885aa1e`, `alter-recipient-provider` `cc260983`, `alter-share` `9ab102fe`, `alter-table-clauses` `17155144` | bodies exist in `docs/pr-bodies/unit-alter-*.md` |
| **CREATE** | Databricks: `CREATE` statements | `CREATE CATALOG` clause set (`USING SHARE`, `RETAIN DROPPED`, `DEFAULT COLLATION`, `OPTIONS`, `FOREIGN CATALOG`); `CREATE SCHEMA` clauses; `CREATE TABLE` table-level `DEFAULT COLLATION` + credentialed `LOCATION`; `CREATE FUNCTION` characteristics + `OR REPLACE`/`IF NOT EXISTS` exclusivity; `CREATE CONNECTION`/`EXTERNAL LOCATION`; `CREATE SHARE`/`RECIPIENT` | 5 branches (`create-connection-external-location` `ad51ae13`, `create-function-characteristics` `d8feea33`, `create-schema-clauses` `c2c467c3`, `create-share-recipient` `d215f078`, `create-table-clauses` `ca7d5245`) + `create-catalog-additions` `ee80fe4f` (unit 2) + the `CREATE FUNCTION` exclusivity part of `fbae1c591` | #8511 merged; bodies in `docs/pr-bodies/unit-create-*.md` |
| **DROP** | Databricks: `DROP` statements | `DROP CONNECTION`/`CREDENTIAL`/`EXTERNAL LOCATION`/`POLICY`/`PROCEDURE`/`PROVIDER`/`RECIPIENT`/`SHARE`/`VARIABLE`, `DROP TABLE FORCE` | slice: `personal/databricks-complete` `fd1f612e0` | #8519 is `DROP MATERIALIZED VIEW` — leave it separate, or fold it in if it has not merged |
| **MAINT** | Databricks: Delta maintenance and auxiliary statements | `OPTIMIZE FULL`, `VACUUM FULL`/`LITE`; `MERGE WITH SCHEMA EVOLUTION`; `COPY INTO`; `FSCK REPAIR TABLE`; `REORG TABLE [APPLY (PURGE)]`; `REPAIR TABLE`; `DROP BLOOMFILTER INDEX`; `CACHE SELECT`; `REFRESH` family incl. `FOREIGN`; `ANALYZE … COMPUTE STORAGE METRICS`; `UNDROP`; `SYNC`; `LIST`; `CALL`; `SET RECIPIENT` | branches `maintenance-full-modes` `820f5283`, `merge-schema-evolution` `c1db8e72`, `copy-into` `55aa6532` + slice `ed00703a3` | bodies in `docs/pr-bodies/unit-maintenance-full-modes.md`, `unit-merge-schema-evolution.md`, `unit-copy-into.md` |
| **SECURITY** | Databricks: Unity Catalog governance — privileges, `SHOW`/`DESCRIBE`, groups, policies | full securable list + `ALL PRIVILEGES` binding; `CREATE`/`DROP GROUP`; `DENY`; `GRANT`/`REVOKE ON SHARE`; `MSCK REPAIR … PRIVILEGES`; `SHOW` UC surface; `DESCRIBE` UC surface; row-filter / column-mask `CREATE`/`DROP`/`SHOW`/`DESCRIBE POLICY` | slice `a0bac66e1` (SHOW/DESCRIBE + security) + `fix/databricks-uc-privileges` `848ce72c` (unit 4) + policy parts of slices `5a6b4b5b1` / `fd1f612e0` | #8512 and #8516 are `VOLUME` privileges and `SHOW GRANTS`; stack unit 4 on #8516, and rebase the bundle after whichever lands |
| **SCRIPTING** | Databricks: SQL scripting and stored procedures | `BEGIN … END` blocks + labels; `DECLARE` (variable, condition, cursor, handler); `IF`/`CASE`; `WHILE`/`LOOP`/`REPEAT`/`FOR` with `LEAVE`/`ITERATE`; `SIGNAL`/`RESIGNAL`; `GET DIAGNOSTICS`; `CREATE PROCEDURE` | slice `f3a38d9c3` + the `CREATE PROCEDURE` part of slice `5a6b4b5b1` | none |
| **QUERY** | Databricks: query and `SELECT` clauses | `OFFSET` without `ROW`/`ROWS`; `TABLESAMPLE … REPEATABLE`; `MATCH_RECOGNIZE`; table-reference `WITH ( … )` options; CTE `MAX RECURSION LEVEL`; SQL pipeline `|>` (`FROM`/`TABLE`/`SELECT … |>`) incl. the zero-operation `FROM t`; `USE CATALOG`/`USE SCHEMA`; `ORDER BY ALL`/`DISTINCT` exclusivity | slice `38c97627e` + the `USE`/`ORDER BY` parts of slice `dafb3cc97` + the `FROM t` part of `fbae1c591` | none |
| **INGEST** | Databricks: `INSERT`, `RESTORE` and flow statements | `INSERT WITH SCHEMA EVOLUTION`; `INSERT … REPLACE ON` (incl. the parenthesised-query source); `RESTORE [TABLE] … TO …`, arithmetic `TIMESTAMP AS OF`; pipeline `CREATE TABLE … FLOW`; append-flow `REPLACE USING ( … ) SEQUENCE BY …` | slice `055ebbacc` + the `FLOW` part of slice `5a6b4b5b1` + branch `fix/databricks-append-flow-sequence-by` `1e8fbed2` (unit 1) + the `REPLACE ON` part of `fbae1c591` | #8520 is inline `FLOW` on streaming tables — fold it in as a follow-up if it has not merged |

**Fold-in rule for hardening.** The Phase 1 rejection-hardening work
(`dafb3cc97`) has no standalone PR: `USE` and `ORDER BY` ride with **QUERY**,
`CREATE TABLE` prefix/constraint hardening and the `CREATE FUNCTION`
exclusivity ride with **CREATE**. Rejection cases a fixture cannot express
stay in `databricks_test.py`.

**Reference-batch units are all accounted for:** unit 1 → INGEST, unit 2 →
CREATE, unit 3 → #8513, unit 4 → SECURITY, unit 5 and 6 → PARSER, units 7+9 →
PARSER, unit 8 → TMPL, unit 10 → LEX, core → CORE.

---

## Open order

1. **Wave 0** — un-draft #8519, #8520, #8522 (and #8517 is already ready);
   land all eight.
2. **Wave 1** — CORE, TMPL, LEX. Independent, small, quick wins.
3. **Wave 2, in this order** (dependencies and rebase cost):
   PARSER → ALTER → CREATE → DROP → MAINT → SCRIPTING → QUERY → INGEST →
   SECURITY. SECURITY last because it must stack on #8516 and rebase after
   #8512. SCRIPTING before INGEST only because `CREATE PROCEDURE` shares the
   scripting body; they do not otherwise interact.
4. Hold the concurrent-open count at **~4–6** (the working cap). Open the next
   bundle only when an earlier one has a reviewer or is merging.

## Per-PR bar

Unchanged from `docs/pr-queue.md`; every bundle before it is pushed as ready:

- fixture first, `.yml` regenerated; rejection tests in `*_test.py` only for a
  boundary a fixture cannot express;
- whole `test/dialects/` with `-n auto` (never a filtered subset);
- `make reference`: the bundle's cases flip, vacuous rejections it owns go
  informative, nothing regresses;
- `make corpus`: rejection stays 100%, recall does not drop;
- check the sibling dialect (databricks vs sparksql) before claiming a gap;
- PR body: construct, doc anchor, cases fixed, and the AI-assistance
  disclosure SQLFluff's CONTRIBUTING requires.

## Build recipe

**A bundle of existing branches** (ALTER, CREATE, most of MAINT, and the
Wave 1 singletons):

```bash
git switch -c bundle/<name> upstream/main
git cherry-pick <each branch tip in the table>      # or git merge --no-commit
# Resolve the shared StatementSegment OneOf list and the two keyword files
# by hand -- adjacent class/segment insertions interleave if left to git.
git checkout personal/databricks-complete -- test/fixtures/dialects/...
.venv/bin/python test/generate_parse_fixture_yml.py -d databricks   # regenerate affected .yml
.venv/bin/python -m pytest test/dialects/ -q -n auto
make -C ../databricks-sql-corpus reference PY=.venv/bin/python
make -C ../databricks-sql-corpus corpus
```

**A slice-only bundle** (DROP, and the parts of SECURITY/SCRIPTING/QUERY/
INGEST that only exist in `personal/databricks-complete`): cut the package
commit's hunks for its segments, keyword additions and fixtures onto a branch
off `upstream/main`, then run the same bar. The package commit SHAs are in the
table; `fbae1c591` and `dafb3cc97` are split across bundles by construct.

**Never open a PR from `personal/databricks-complete`, and never merge it.**
It is the measurement oracle. Work in the bundle branches and keep the corpus
`.venv` pointed at whichever branch is being measured.

## Engine caveat

A dialect branch's numbers reflect its grammar only after the Rust tables are
rebuilt (`utils/rustify.py build` + `maturin build --release`, wheel installed
into every measuring venv); the Python engine is what upstream CI judges, and
`test/core/parser/parity/` enforces parity. `make audit AUDIT_REF=<ref>`
measures committed state only. A lexer change (LEX) needs the rebuild before
any measurement is meaningful.

## Fallback: splitting a bundle

The seam is the row. If a bundle is rejected as too broad:

- **PARSER** → (identifier/keyword + `IDENTIFIER`), (JSON path), (set operands);
- **ALTER** → one PR per object family if asked, but the family bundle is the
  precedent (`ATTACH`/`DETACH`/…);
- **CREATE** → (CATALOG/SCHEMA), (TABLE/FUNCTION), (CONNECTION/EXTERNAL
  LOCATION/SHARE/RECIPIENT);
- **MAINT** → (OPTIMIZE/VACUUM/MERGE/COPY INTO), (FSCK/REORG/REPAIR/CACHE/DROP
  BLOOMFILTER/REFRESH/ANALYZE), (UNDROP/SYNC/LIST/CALL/SET RECIPIENT);
- **SECURITY** → (privileges/securables), (SHOW/DESCRIBE UC),
  (groups/DENY/share/masks);
- **SCRIPTING** → (block/`DECLARE`), (control flow/loops), (`SIGNAL`/
  `RESIGNAL`/`GET DIAGNOSTICS`), (`CREATE PROCEDURE`);
- **QUERY** → one PR per clause;
- **INGEST** → (`INSERT`/`REPLACE ON`), (`RESTORE`), (flows).

Each split is the original constituent branch, pushed as its own PR.

## Progress log

- **PARSER** — branch `bundle/parser-correctness` `38667886e` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-parser-correctness.md`.
  One commit off `upstream/main` `b52246da5`; `test/dialects/` + parity **9394
  passed, 2 xfailed**; reference **504 → 508 must-parse, 363 → 364
  must-reject (informative)**, zero regressions; corpus **542 → 544**, rejection
  100%. `gh pr create` refused by the throttle (permissions-shaped); retry on
  the next burst.
- **ALTER** — branch `bundle/alter-statements` `a4fc8bf5c` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-alter-statements.md`.
  One commit off `upstream/main` `b52246da5`, squashed from the seven
  `fix/databricks-alter-*` branches; `test/dialects/` + parity **9439 passed,
  2 xfailed**; reference **504 → 552 must-parse (+48)**, must-reject 363/393
  with informative rejections **211 → 223**, zero regressions; corpus holds at
  542/562, rejection 100%. `gh pr create` refused by the throttle; retry.
- **CREATE** — branch `bundle/create-statements` `ffc38f331` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-create-statements.md`.
  One commit off `upstream/main`, squashed from the five
  `fix/databricks-create-*` branches plus `create-catalog-additions` and the
  `CREATE FUNCTION` `OR REPLACE`/`IF NOT EXISTS` exclusivity from the slice;
  `test/dialects/` + parity **9444 passed, 2 xfailed**; reference
  **504 → 547 must-parse (+43)**, must-reject **363 → 366**, informative
  **211 → 251**, zero regressions; corpus holds at 542/562, rejection 100%.
  `gh pr create` refused by the throttle; retry.
- **DROP** — branch `bundle/drop-statements` `7adb61f8c` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-drop-statements.md`.
  One commit off `upstream/main` `6f0dffd96`, from slice `fd1f612e0`; adds the
  `SERVICE`/`CREDENTIAL`/`METASTORE` keywords the slice relied on;
  `test/dialects/` + parity **9394 passed, 2 xfailed**; reference
  **504 → 516 must-parse (+12)**, informative rejections **211 → 220**, zero
  regressions; corpus holds at 542/562, rejection 100%. `gh pr create` refused
  by the throttle; retry.
- **MAINT** — branch `bundle/maintenance-statements` `ee2e4334f` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-maintenance-statements.md`.
  One commit off `upstream/main` `6f0dffd96`, from the three branches
  (`maintenance-full-modes`, `merge-schema-evolution`, `copy-into`) plus slice
  `ed00703a3`; `test/dialects/` + parity **9488 passed, 2 xfailed**; reference
  **504 → 568 must-parse (+64)**, must-reject **363 → 367**, informative
  **211 → 259**, zero regressions; corpus holds at 542/562, rejection 100%.
  `gh pr create` refused by the throttle; retry.
- **Formatting: all bundle branches needed `ruff format`, not just `ruff
  check`.** The `pre-commit` workflow (ruff v0.15.5) failed on
  `create-statements` and `alter-statements`; `parser-correctness` had no run
  at all. Fixed and re-pushed (`b5748d197`, `dde673227`, `ea2c4d156`), all
  green. Run `ruff format` on the changed files before every push.
- **SCRIPTING** — branch `bundle/scripting-statements` `445c7c500` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-scripting-statements.md`.
  One commit off `upstream/main`, from slice `f3a38d9c3` plus the
  `CREATE PROCEDURE` part of `5a6b4b5b1`; `test/dialects/` + parity **9414
  passed, 2 xfailed**; reference **504 → 523 must-parse (+19)**, must-reject
  363/393 with informative **211 → 222**, zero regressions; corpus holds at
  542/562, rejection 100%. `gh pr create` refused by the throttle; retry.
- **QUERY** — branch `bundle/query-statements` `c37654348` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-query-statements.md`.
  One commit off `upstream/main`, from slice `38c97627e` plus the `USE` /
  `ORDER BY` hunks of `dafb3cc97` and the zero-operation `FROM t` hunk of
  `fbae1c591`; `test/dialects/` + parity **9418 passed, 2 xfailed**;
  reference **504 → 517 must-parse (+13)**, must-reject **363 → 365**,
  informative **211 → 216**, zero regressions; corpus holds at 542/562,
  rejection 100%. `OFFSET` had to stay **unreserved** (a column named `offset`
  is common); it is kept off the FROM-terminator list and excluded from the
  alias grammar instead.
- **INGEST** — branch `bundle/ingest-statements` `f90bd72db` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-ingest-statements.md`.
  One commit off `upstream/main`, from slice `055ebbacc` plus the `FLOW` hunk
  of `5a6b4b5b1`, the `fix/databricks-append-flow-sequence-by` append-flow fix
  and the `REPLACE ON` hunk of `fbae1c591`; `test/dialects/` + parity **9417
  passed, 2 xfailed**; reference **504 → 518 must-parse (+14)** and the #8509
  over-acceptance now caught (`create-flow.replace-using-without-sequence-by`),
  zero regressions; corpus holds at 542/562, rejection 100%. Carries the
  inline-`FLOW` machinery that overlaps draft #8520.
- **SECURITY** — branch `bundle/security-statements` `ce3edc649` pushed to
  `taslater/sqlfluff`; body at `docs/pr-bodies/bundle-security-statements.md`.
  One squashed commit off **current `upstream/main`**, from slice `a0bac66e1`
  plus `fix/databricks-uc-privileges` (unit 4) and the `SHOW GRANTS` commits of
  #8516. It was first built on #8516's branch tip `c9121aaa8` (pre-#8510/#8511/
  #8514), which regressed `DESCRIBE HISTORY`/`DETAIL` and `MANAGED LOCATION`;
  **rebasing onto `upstream/main` cleared all three**. `test/dialects/` +
  parity **9435 passed, 2 xfailed**; reference **504 → 576 must-parse (+72)**,
  must-reject **363 → 377 (+14)**, zero regressions; corpus **542 → 543**, no
  new failures, rejection 100%. `RECIPIENT` is reserved here as well as in
  MAINT, which closes `grant-share.without-recipient`.
- **Wave 1 bodies** — `bundle-templater-databricks-params.md` and
  `bundle-notebook-magic-cell-boundaries.md` written; CORE's body already
  existed. All three branches (`core/keyword-terminator-after-bracket`,
  `fix/templater-placeholder-databricks-params`,
  `fix/databricks-magic-cell-boundaries`) are already `ruff format`-clean.

### All twelve PRs are queue-ready

CORE, TMPL, LEX, PARSER, ALTER, CREATE, DROP, MAINT, SCRIPTING, QUERY, INGEST
and SECURITY are each a pushed branch off `upstream/main` (SECURITY carries the
#8516 commits), all `ruff format`-clean and pre-commit green. The bodies are in
`docs/pr-bodies/`. Opening is draft-first: the burst throttle refuses
`CreatePullRequest` account-wide, so each is attempted once as a draft and left
pushed if refused.

**All twelve drafts were opened on 2026-09-21** — the throttle lifted for the
burst and every call was admitted:

| bundle | draft PR |
| --- | --- |
| CORE | [#8543](https://github.com/sqlfluff/sqlfluff/pull/8543) |
| TMPL | [#8544](https://github.com/sqlfluff/sqlfluff/pull/8544) |
| LEX | [#8545](https://github.com/sqlfluff/sqlfluff/pull/8545) |
| PARSER | [#8546](https://github.com/sqlfluff/sqlfluff/pull/8546) |
| ALTER | [#8547](https://github.com/sqlfluff/sqlfluff/pull/8547) |
| CREATE | [#8548](https://github.com/sqlfluff/sqlfluff/pull/8548) |
| DROP | [#8549](https://github.com/sqlfluff/sqlfluff/pull/8549) |
| MAINT | [#8550](https://github.com/sqlfluff/sqlfluff/pull/8550) |
| SCRIPTING | [#8551](https://github.com/sqlfluff/sqlfluff/pull/8551) |
| QUERY | [#8552](https://github.com/sqlfluff/sqlfluff/pull/8552) |
| INGEST | [#8553](https://github.com/sqlfluff/sqlfluff/pull/8553) |
| SECURITY | [#8554](https://github.com/sqlfluff/sqlfluff/pull/8554) |

They are drafts on purpose (the user's call): no `gh pr ready` is attempted.
The Wave 0 drafts (#8519, #8520, #8522) are likewise left as they are.
