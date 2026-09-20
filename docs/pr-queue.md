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

## Measured state, 2026-09-21 — the gate is met

On `personal/combined-2026-09-21` (tag of the same name, `e56f48b03`,
`upstream/main` at `b52246da5`, all eight open-PR branches, all ten units,
`EXCEPT DISTINCT`/`MINUS` from #8523):

| measurement | result |
| --- | --- |
| reference must-parse | **177/177** |
| reference must-reject | **83/83** (83 informative, **0 vacuous**) |
| corpus files | **777/866 (89.7%)**, mutation 1325/1325 |
| `test/dialects/` | **7092 passed** |

`personal/combined-2026-09-20` measured 150/177, 82/83 (14 vacuous) — the
first seven units closed exactly the 28 remaining reference gaps, and the
other three units are corpus/correctness work, with no combination
regressions.

Remaining scraped-corpus failures on the union are all accounted for:

- **7 `sqlfluff-sparksql` fixtures** — the Phase 2 list below.
- **78 `spark-sql-tests` files** — the source expectation is `mixed`; these
  are Spark's own inputs, many of them labelled negative cases.
- **3 files with a secondary blocker** newly exposed once the first one was
  fixed. The `dbx-devrel` SCD file was the magic-cell boundary bug (a
  `-- MAGIC %fs …` line with a trailing space, plus the `magic_start`
  trailing newline); that is fixed on `fix/databricks-magic-cell-boundaries`,
  and the file now fails later, on queued `COPY INTO`. The other two are
  `Generating Surrogate Keys.sql` (`count(DISTINCT sk)FROM`: a **general
  parser bug**, not databricks-specific — `(a)FROM t` is parsed as an
  implicit alias on ansi, sparksql and databricks, and on released 4.3.0)
  and `Clean Up.sql` (`USE CATALOG c` left unterminated before the next
  statement in the same cell).
- **1 documented not-gap**: Lakebase `create_raw_tags.sql`.

None of the four is a reference-corpus case; they are candidates for the
next batch, not for this one.

## Units

| # | branch | unit | ref cases | corpus | size | state |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `fix/databricks-append-flow-sequence-by` | bind `SEQUENCE BY` in the standalone append-flow `REPLACE USING` spec | 2 parse + 1 reject | 0 | XS | **pushed** `1e8fbed27`; `databricks_test.py` pins both incomplete forms as rejections; #8460 still `CONFLICTING` and silent, so this is the open-first unit; body at `docs/pr-bodies/unit-01-append-flow-sequence-by.md`; `gh pr create` refused by the burst throttle |
| 2 | `fix/databricks-create-catalog-additions` | CREATE CATALOG: `USING SHARE`, `RETAIN DROPPED`, `DEFAULT COLLATION`, `OPTIONS`, `FOREIGN CATALOG` | 8 + 8 boundaries | 0 | M | **pushed** `ee80fe4f0`; verified +8 must-parse, +7 informative, suite 7037, rejection 100% |
| 3 | extend `fix/databricks-live-view` (#8513) | CREATE VIEW: restore the data-source production and the parenthesised `with_clause` (same #7405 rewrite) | 4 + 4 boundaries | 1 | M | **pushed** `de3b6372c` into #8513; verified +4 must-parse, +4 informative; #8513 body rewritten to cover both repairs (the old body still claimed `OR REFRESH` was restored) |
| 4 | `fix/databricks-uc-privileges` | the full securable list (SHARE, CONNECTION, CLEAN ROOM, EXTERNAL LOCATION, EXTERNAL METADATA, PROCEDURE, `[STORAGE\|SERVICE] CREDENTIAL`, bare CATALOG) and bind `ALL PRIVILEGES` vs list | 9 + 2 show-grants + 1 reject | 0 | M/L | **pushed** `848ce72cf`, stacked on #8516; verified +11 must-parse (118→129), +1 caught (81→82), +4 informative; VOLUME cases stay #8512's |
| 5 | `fix/databricks-json-path` | JSON path `[ * ]` and delimited identifiers | 2 | 0 | S/M | **pushed** `46aa4f862`; verified +2 must-parse (109→111), suite 7030, rejection 100% |
| 6 | `fix/sparksql-parenthesised-set-operands` | parenthesised set-operation operands | 1 | 1 (q87) | S/M | **pushed** `ff39472cf`; verified +1 must-parse (109→110), suite 7030, rejection 1327/1327 |
| 7+9 | `fix/databricks-identifier-keyword-false-positives` | identifier and keyword false positives: LEFT/RIGHT unreserved (a #8050 regression), `KEYS`/`PIVOT`/`WINDOW` as explicit aliases, `DESCRIBE history.tbl`, `SELECT * FROM stream` | 1 | 1 (select_lambda) | M | **pushed** `7f58e29d3` (unit 7 `66aebdaa4` + unit 9 `163c2f232` cherry-picked); verified suite 7041, reference 110/177 (the `array_sort` lambda case flips), corpus `sqlfluff-sparksql` 124→125, mutation 1327/1327. `MASK` is **not** added: the reference's alias-only restriction is for table aliases, and the shared `AliasExpressionSegment` cannot tell a table alias from a column alias, so a blanket exclude would over-reject `SELECT a AS MASK` |
| 8 | `fix/templater-placeholder-databricks-params` | placeholder templater: `${dotted}`, `{{ dashboard }}`, `${}` | 0 | 1 | M | **pushed** `eb35e1c62`; verified: dbx-dlt-notebooks 18/19→19/19, failures 104→103, zero regressions, mutation 1327/1327, templater suite 239; four other template-shaped files have secondary gaps (gaps.md) |
| 9 | — | `DESCRIBE history.tbl`, `SELECT * FROM stream` | — | — | — | folded into unit 7 (`163c2f232` cherry-picked onto the theme branch); its fixes are correctness-only in the corpus, so they add no count on their own |
| 10 | `fix/databricks-magic-cell-boundaries` (was `…-percent-line`) | a `%`-prefixed `-- MAGIC` line inside an `%md` cell; plus the `magic_start` / `magic_single_line` / `magic_line` regexes so a trailing space or a final standalone directive cannot swallow the separator | 0 | 1 | S/M | **pushed** `1625e1051`; verified: `my_streaming_table.sql` parses, SCD file advances past the magic cells (now fails later on queued `COPY INTO`), suite 7032, mutation 100% (1326/1326); the lexer regexes need the Rust tables rebuilt to measure (`utils/rustify.py build` + `maturin develop`), done locally |

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
| 7+9 | `fix/databricks-identifier-keyword-false-positives` | `upstream/main` `b52246da5` | `7f58e29d3` | pushed, ready (unit 7 branch + unit 9 commit; the separate `fix/sparksql-identifier-false-positives` branch is superseded) |
| 8 | `fix/templater-placeholder-databricks-params` | `upstream/main` `b52246da5` | `eb35e1c62` | pushed, ready (core templater, not dialect) |
| 9 | — | — | — | folded into unit 7 |
| 10 | `fix/databricks-magic-cell-boundaries` | `upstream/main` `b52246da5` | `1625e1051` | pushed; lexer regexes inside, so a measurement needs the Rust tables rebuilt (see notes) |
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
- **Units 7 and 9 are one PR.** Both are the same problem class — a legal
  identifier rejected because a keyword elsewhere has the same spelling —
  found by the same probe and settled by the same reference page. Reviewed
  precedent (SQLFluff's `ATTACH`/`DETACH`/`VACUUM`/`REINDEX`/`ANALYZE`,
  `CREATE`/`ALTER SESSION POLICY`, our own `DESC`/`DESCRIBE HISTORY` and
  `DESCRIBE DETAIL`) bundles a statement family or one clause set; 7 and 9
  are two mechanisms behind one class, and the single PR is the deliberate
  exception. Everything else stays one construct per PR.
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
| 7 | units 7+9, identifier/keyword false positives | 1 case + select_lambda |
| 8 | unit 8, templating | 1 corpus file, independent reviewer path |
| 9 | — | folded into unit 7 |
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

The permissions-shaped refusal (`does not have permission` /
`does not have the correct permissions`, while the token's rate limit reads
5000/5000) is **bursty**: on 2026-09-21 the first call of the day succeeded
(`gh pr ready 8517` — now ready for review) and every mutation after it was
refused in the same session, including the other three `gh pr ready` calls and
`gh pr create` for unit 1. One mutation per burst; retrying in the same minute
does not help.

State after 2026-09-21: **#8517 is ready; #8519, #8520, #8522 still show
as drafts**. Review comments *are* being admitted — the cubic replies on
#8512 and #8513 posted first try — while `markPullRequestReadyForReview` and
`createPullRequest` are still refused. So the block is specific to those two
mutations, not to the token: post bodies/replies freely, and retry the three
`gh pr ready` calls and unit 1's creation on the next burst.

Unit 1's body is in `docs/pr-bodies/`; the remaining units' bodies are to be
drafted from the same template when opened. The branches are all pushed and
independent, so nothing is lost by waiting.

## Measuring a branch

`make audit AUDIT_REF=<ref>` checks the ref out in the
`../sqlfluff-worktrees/main` worktree (the `.venv-main` slot), runs
`make reference`, `make corpus`, `make diff` and the whole
`test/dialects/` suite with `-n auto`, then restores the worktree to
detached `main`. It measures committed state only, by construction.

Two caveats: `.venv-main` must have the branch's Rust lexer tables if the
branch touches a lexer regex (build with `utils/rustify.py build` +
`maturin develop`, then install the wheel into `.venv-main`); and the
corpus and differential are advisory here, since reference is the unit's
oracle and `test/dialects` is the regression gate.
