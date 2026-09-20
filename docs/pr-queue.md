# Upstream PR queue: closing the reference corpus

Goal: every case in `corpus/reference/` conforms — **177/177 must-parse,
83/83 must-reject caught, 0 vacuous** — before the next batch of upstream PRs
is opened. This file is the runsheet: what each unit contains, what it
unblocks, how the units combine, and the order to open them in. `docs/gaps.md`
remains the evidence trail; this file is the plan.

**Definition of done for the batch**

1. Every unit below is a pushed branch with fixtures, the whole
   `test/dialects/` suite green, and `make reference` run on the branch.
2. The union branch carries all units and measures 177/177, 83/83, 0 vacuous.
3. Each PR body is drafted; opening is held while GitHub throttles, then done
   in the order below.

## Measured state, 2026-09-20

On `personal/combined-2026-09-20` (fresh `upstream/main` at `b52246da5`, all
open PRs merged, `EXCEPT DISTINCT`/`MINUS` from #8523 merged, the `SEQUENCE BY`
binding carried):

| measurement | result |
| --- | --- |
| reference must-parse | **150/177** |
| reference must-reject | **82/83** (68 informative, 14 vacuous) |
| corpus failing constructs | **16 distinct** |

The 28 reference gaps are exactly units 1–7 below — combination introduced no
new failure. Of the 16 corpus constructs, 8 are ours (units 3, 6, 7, 8, 10),
7 are `sqlfluff-sparksql` fixtures outside the Databricks reference queue
(Phase 2 below), and 1 is the Lakebase file recorded as not-a-gap.

## Units

| # | branch | unit | ref cases | corpus | size | state |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `fix/databricks-append-flow-sequence-by` | bind `SEQUENCE BY` in the standalone append-flow `REPLACE USING` spec | 2 parse + 1 reject | 0 | XS | **pushed**; #8460 check done 2026-09-20 — still `CONFLICTING`, no reply, so ours opens in order |
| 2 | `fix/databricks-create-catalog-additions` | CREATE CATALOG: `USING SHARE`, `RETAIN DROPPED`, `DEFAULT COLLATION`, `OPTIONS`, `FOREIGN CATALOG` | 8 + 8 boundaries | 0 | M | **pushed** `ee80fe4f0`; verified +8 must-parse, +7 informative, suite 7037, rejection 100% |
| 3 | extend `fix/databricks-live-view` (#8513) | CREATE VIEW: restore the data-source production and the parenthesised `with_clause` (same #7405 rewrite) | 4 + 4 boundaries | 1 | M | **pushed** `de3b6372c` into #8513; verified +4 must-parse, +4 informative; #8513 body rewritten to cover both repairs (the old body still claimed `OR REFRESH` was restored) |
| 4 | `fix/databricks-uc-privileges` | the full securable list (SHARE, CONNECTION, CLEAN ROOM, EXTERNAL LOCATION, EXTERNAL METADATA, PROCEDURE, `[STORAGE\|SERVICE] CREDENTIAL`, bare CATALOG) and bind `ALL PRIVILEGES` vs list | 9 + 2 show-grants + 1 reject | 0 | M/L | **pushed** `848ce72cf`, stacked on #8516; verified +11 must-parse (118→129), +1 caught (81→82), +4 informative; VOLUME cases stay #8512's |
| 5 | `fix/databricks-json-path` | JSON path `[ * ]` and delimited identifiers | 2 | 0 | S/M | **pushed** `46aa4f862`; verified +2 must-parse (109→111), suite 7030, rejection 100% |
| 6 | `fix/sparksql-parenthesised-set-operands` | parenthesised set-operation operands | 1 | 1 (q87) | S/M | **pushed** `ff39472cf`; verified +1 must-parse (109→110), suite 7030, rejection 1327/1327 |
| 7 | `fix/databricks-unreserve-identifiers` | LEFT/RIGHT regression + `KEYS`/`PIVOT`/`WINDOW` as unquoted aliases | 1 | 1 (select_lambda) | M | **pushed** `66aebdaa4`; verified +1 must-parse (109→110), suite 7038, corpus `sqlfluff-sparksql` 124→125, mutation 1327/1327; databricks keeps its own `AliasExpressionSegment` for `FOR` (anonymous PIVOT) |
| 8 | `fix/templater-placeholder-databricks-params` | placeholder templater: `${dotted}`, `{{ dashboard }}`, `${}` | 0 | 1 | M | **pushed** `eb35e1c62`; verified: dbx-dlt-notebooks 18/19→19/19, failures 104→103, zero regressions, mutation 1327/1327, templater suite 239; four other template-shaped files have secondary gaps (gaps.md) |
| 9 | `fix/sparksql-identifier-false-positives` | `DESCRIBE history.tbl`, `SELECT * FROM stream` | 0 | 0 | S | **pushed** `163c2f232`; suite 7033; reference unchanged 109/177; corpus failures unchanged 103, mutation 1327/1327 — correctness fix, no counts |
| 10 | `fix/databricks-magic-cell-percent-line` | a `%`-prefixed `-- MAGIC` line inside an `%md` cell | 0 | 1 | S/M | **pushed** `c1754c458`; verified: `my_streaming_table.sql` parses, dbx-learn-databricks 43/46→44/46, failures 103→102, mutation 100% (1326/1326); adjacent quirk left alone: a cell ending in a standalone directive still hides the separator's blank line (needs a lexer regex change) |

Covered by existing open PRs, not repeated here: #8512 (3 cases),
#8515 (8), #8516 (6 + unlocks the securable cases), #8517 (6, draft),
#8519 (2, draft), #8520 (2, draft), #8522 (3, draft). #8523
(`EXCEPT DISTINCT`/`MINUS`, maksimtech) is another author's PR being
reviewed; its fix is carried on the union only, never re-submitted by us.

## Branches

All unit branches live in `taslater/sqlfluff` and are pushed to `origin`.
Base is the commit the branch was cut from; rebase onto `upstream/main` when
its base has moved and the unit is opened.

| unit | branch | base | tip | state |
| --- | --- | --- | --- | --- |
| 1 | `fix/databricks-append-flow-sequence-by` | `upstream/main` `b52246da5` | `535cf5655` | pushed, ready to open first |
| 2 | `fix/databricks-create-catalog-additions` | `upstream/main` `b52246da5` | `ee80fe4f0` | pushed, ready |
| 3 | `fix/databricks-live-view` (#8513) | `6356e4765` (opened 2026-09-18) | `de3b6372c` | PR open; body rewritten; rebase before more commits if upstream moves `CreateViewStatementSegment` |
| 4 | `fix/databricks-uc-privileges` | stacked on `c9121aaa8` (#8516) | `848ce72cf` | pushed; rebase onto `main` when #8516 merges, and after #8512 if it lands first |
| 5 | `fix/databricks-json-path` | `upstream/main` `b52246da5` | `46aa4f862` | pushed, ready |
| 6 | `fix/sparksql-parenthesised-set-operands` | `upstream/main` `b52246da5` | `ff39472cf` | pushed, ready |
| 7 | `fix/databricks-unreserve-identifiers` | `upstream/main` `b52246da5` | `66aebdaa4` | pushed, ready |
| 8 | `fix/templater-placeholder-databricks-params` | `upstream/main` `b52246da5` | `eb35e1c62` | pushed, ready (core templater, not dialect) |
| 9 | `fix/sparksql-identifier-false-positives` | `upstream/main` `b52246da5` | `163c2f232` | pushed, ready |
| 10 | `fix/databricks-magic-cell-percent-line` | `upstream/main` `b52246da5` | `c1754c458` | pushed, ready |
| — | `personal/combined-2026-09-20` (tag of the same name) | `upstream/main` `b52246da5` | `ba4a00c8b` | the measurement union; never merge, never open a PR from it |

Measuring a branch: the corpus `.venv` is pinned to the `sqlfluff/` checkout
path, so check the branch out there, run `make reference` and `make corpus`,
and switch back to `main` afterwards. Measure only committed state — an
uncommitted tree measures the same everywhere (this trap has cost two
mis-read deltas already).

## Combining decisions

- **Unit 3 folds into #8513.** It repairs the same `#7405`
  `CreateViewStatementSegment` rewrite; one PR, one `match_grammar`.
  #8513 has no approval to reset.
- **Unit 4 is one follow-up PR**, not two. The securables and the privilege
  binding share the GRANT-family review context. It is stacked on #8516
  (`fix/databricks-show-grants`) because the reference cases exercise the
  securables through `SHOW GRANTS`; it overlaps #8512's `AccessObjectSegment`
  and `AccessPermissionSegment` hunks, so whichever lands second rebases.
  Keep #8512 focused on `READ`/`WRITE VOLUME`.
- **Unit 7 is one PR**: LEFT/RIGHT is a regression of a merged sparksql fix
  (#8050) and the alias-only trio is the same class, found by the same probe.
- **Unit 9 is one tiny PR**; kept separate from unit 7 because it touches
  statement grammar, not keyword sets.
- Units 1, 2, 5, 6, 8, 10 stand alone.

## Open order (bang for buck)

| order | what | why first |
| --- | --- | --- |
| 0 | un-draft #8517, #8519, #8520, #8522 | 13 cases, no new work |
| 1 | unit 1, SEQUENCE BY | 3 cases, fixes a shipped over-acceptance, XS |
| 2 | unit 2, CREATE CATALOG | 8 cases, one statement, visible admin syntax |
| 3 | unit 4, UC privileges | 12 cases, big blast radius |
| 4 | unit 3, CREATE VIEW (as #8513) | 4 cases + 1 corpus file |
| 5 | unit 5, JSON path | 2 cases, common in real code |
| 6 | unit 6, set operands | 1 case + q87 |
| 7 | unit 7, identifiers | 1 case + select_lambda |
| 8 | unit 8, templating | 1 corpus file, independent reviewer path |
| 9 | unit 9, false positives | correctness, no counts |
| 10 | unit 10, magic `%`-line | 1 corpus file, queue entry first |

## Per-unit bar

Every unit, before it is pushed as ready:

- fixture first, `.yml` regenerated; rejection tests in `*_test.py` only for a
  boundary a fixture cannot express;
- whole `test/dialects/` with `-n auto`;
- `make reference` on the branch: the unit's cases flip, every vacuous
  rejection its construct owns becomes informative, nothing regresses;
- `make corpus` after any grammar change: rejection stays 100%, recall does
  not drop;
- check the sibling dialect first (databricks vs sparksql) before assuming a
  gap;
- PR body: construct, doc anchor, the cases it fixes, AI-assistance
  disclosure per SQLFluff's CONTRIBUTING.

## Phase 2 (after reference is 100%)

`sqlfluff-sparksql` fixtures still failing on the union, all outside the
Databricks reference queue: `ALTER DATABASE … SET LOCATION`,
`ALTER TABLE … SET SERDEPROPERTIES`, `ALTER VIEW … AS ( … )`,
hive-format `PARTITIONED BY (col TYPE COMMENT …)`, `ALTER TABLE … CHANGE`,
`ALTER COLUMN … TYPE … COMMENT`, and `SELECT f(*, col2)`. These are SQLFluff's
own fixtures and real gaps; queue them once the reference corpus is clean.

## Throttle notes

GitHub currently refuses PR creation and `markPullRequestReadyForReview` with
a permissions-shaped error. Branches are pushed to `origin` meanwhile; the
queue above is held in this file rather than in open PRs. Retry `gh pr ready`
for the four drafts first, then open in the order above.
