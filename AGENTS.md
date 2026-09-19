# AGENTS

Guidance for AI coding agents working in this repo. Read this before changing
anything under `src/dbsqlparse/corpus/`.

## What this is

`databricks-sql-corpus` measures **SQLFluff** against a corpus of published
Databricks SQL, and turns the failures into upstream pull requests.

It does **not** contain a parser. It used to: this project began as an
ANTLR parser built on Spark's own grammar, because SQLFluff appeared not to
support Databricks well. A head-to-head disproved that — SQLFluff scored
59/59 on its own Databricks fixtures where the parser here scored 36/59, and
the advantage this project actually had was notebook preprocessing, not
parsing. The parser was retired; `docs/design-notes.md` records what was
learned building it, and `NOTICE` records what was removed.

What is left is the part with ongoing value: 867 files of real Databricks SQL
from 14 pinned public sources, a harness that reports which constructs
SQLFluff cannot parse, and a mutation corpus that checks a grammar change we
contribute upstream does not make SQLFluff accept garbage.

## Commands

```bash
make venv           # create .venv, install the harness
make corpus-fetch   # download the pinned corpus (once)
make corpus         # measure SQLFluff: recall + rejection
make gaps           # group failures by construct -- the PR queue
make reference      # cases transcribed from the Databricks SQL reference
make baseline       # regenerate corpus/reports/baseline.json
make test
```

To measure an **unmerged** SQLFluff branch — the main workflow — install the
fork over the release:

```bash
.venv/bin/pip install -e ../sqlfluff     # a fork checkout on any branch
make gaps
```

Each target measures whichever SQLFluff is installed in the venv it runs with,
so another branch can be measured in parallel by pointing `PY` at a venv that
has it — useful when a worktree holds the branch you want:

```bash
make reference PY=.venv-main/bin/python     # e.g. a worktree on main
make baseline  PY=.venv-release/bin/python  # released SQLFluff only
```

`make baseline` refuses an editable SQLFluff: the committed baseline must
reflect what a release does, and an editable fork install would silently
measure a branch instead.

Nothing here needs Java, and there is no code generation step.

## Layout

```
src/dbsqlparse/corpus/sources.py    the 14 pinned sources -- pinned to exact commits
src/dbsqlparse/corpus/fetch.py      downloads them into corpus/cache/
src/dbsqlparse/corpus/runners.py    the parsers under test (SQLFluff, sqruff)
src/dbsqlparse/corpus/harness.py    recall + rejection measurement
src/dbsqlparse/corpus/mutate.py     valid SQL -> guaranteed-invalid SQL
src/dbsqlparse/corpus/reference.py  the doc-derived corpus harness
src/dbsqlparse/corpus/cli.py        `python -m dbsqlparse.corpus`
corpus/reference/*.yml              cases transcribed from the reference
src/dbsqlparse/preprocess.py        notebook cells + parameter substitution
scripts/compare_baseline.py         baseline diff for CI
docs/gaps.md                        the upstream work queue
docs/design-notes.md                history, including the retired parser
```

## The non-obvious constraints

**Two numbers that mean different things.**

| metric | what a miss means |
| --- | --- |
| **recall** — valid SQL SQLFluff accepts | false positive: CI blocks a good merge request |
| **rejection** — invalid SQL SQLFluff catches | false negative: broken SQL sails through review |

Recall matters most. Rejection exists because a corpus of only-valid SQL
cannot tell a good parser from one that accepts everything.

**Only `guaranteed` mutations are scored.** `weak` ones (deleting a comma or a
`FROM`) are reported but never scored, because the default keyword mode
legitimately re-parses them as valid — `SELECT a b FROM t` aliases `a` to `b`.
Scoring those counts correct behaviour as a miss. Re-tiering a mutation
changes what the rejection number means, so plan it.

**Deciding "did it parse?" needs three checks, not one.** `parsed.violations`
alone misses a tree that parsed into `unparsable` nodes; and `parsed.tree`
*asserts* rather than returning None when the root variant failed. See
`SqlFluffRunner.check`. Getting this wrong reports a clean 100%.

**sqruff writes findings to stderr**, while its "processed N files" banner goes
to stdout. Reading only stdout reports a clean 100% no matter the input. This
cost real debugging time; see `SqruffRunner`.

**Always include a known-bad control.** Every probe batch in this repo asserts
that something deliberately broken is still rejected. Three separate times, a
harness bug made failure look like success — once via stderr, once via
SQLFluff's `All Finished!` banner printing on failure, once via an over-narrow
pytest filter. A control catches all three.

**The corpus cache is not committed**, because every source is pinned to an
exact revision and the cache is reproducible from `sources.py` alone.
`corpus/reports/baseline.json` **is** committed, so changes show up in diffs.

**The baseline tracks released SQLFluff**, not a fork checkout, so it reflects
what a user actually gets. Do not regenerate it from a fork to make a number
look better, and read the diff before committing it. `scripts/compare_baseline.py`
distinguishes a new source from a regression.

## Adding a corpus source

Add a `Source` to `sources.py` pinned to an exact commit SHA, never a branch.
Prefer repositories that are genuinely Databricks SQL: several "Databricks"
repos on GitHub are Oracle or T-SQL, dbt projects are Jinja templates rather
than SQL, and Databricks Academy material contains deliberate `<FILL_IN>`
blanks. `harness.py` already skips JSON-wearing-a-.sql-extension and, for
local sources only, T-SQL.

Adding a source that exposes a gap is **not** a regression.

## The blind spot, and the reference corpus

The 867 files sample **what people publish**, not **what the dialect allows**.
Recall cannot fail on a construct no corpus file uses, and `mutate.py` derives
its invalid inputs from corpus SQL, so it cannot invent one either. Both
measurements are blind in the same place — and a fixture written from the same
reading of a doc page agrees with whatever that reading got wrong. Four checks,
one oracle.

That blind spot shipped a defect. SQLFluff #8509 (merged 2026-09-18)
implemented `[ replace_using_spec ]` as optional-as-a-whole but never bound its
interior, so `main` accepts `REPLACE USING (c)` and rejects the documented
`REPLACE USING (c) SEQUENCE BY d`. Nothing here could have caught it: no corpus
file uses the construct. It was found by diffing a merged PR against someone
else's older open one. See the entry in `docs/gaps.md`.

**`corpus/reference/` is the fix.** A second, small corpus transcribed from
the Databricks SQL reference rather than scraped from GitHub: one YAML file
per reference page, each case carrying the statement, a `must-parse` or
`must-reject` verdict, the doc URL and anchor, plus, for a partial form, a
`from:` link to its full-form sibling and the production it `omits:`. Each
file also carries `syntax:` (the page's production, verbatim) and `checked:`
(the date the page was read); both are required. The loader is strict —
unknown keys, duplicate ids, unresolved `from:` links, a must-reject without
`omits:`, and an `omits:` that does not appear in the file's `syntax:` block
are all errors — because a mistyped case that silently loads would make the
corpus agree with the mistake.

The rule that generates the cases is unchanged: **wherever the reference
brackets an optional multi-token production, the partial forms are explicit
`must-reject` cases.** The over-accepting half of #8509 is now pinned by
`create-flow.replace-using-without-sequence-by`, which `main` accepts.

`make reference` needs no fetched corpus. It reports separately from recall and
rejection, because the oracle is different: a must-parse miss means the
reference documents syntax that CI would block, and a must-reject miss means
the parser accepts a form the reference does not define. A must-reject case
only counts as **informative** when its full-form sibling parses — otherwise
the rejection may be for an unrelated reason, and the report calls it vacuous.
The vacuous count is the corpus's health metric and is carried in
`baseline.json`, so `compare_baseline.py` reports its trend. Every run also
checks two controls built into the harness rather than the data, one valid
statement that must parse and one structurally invalid statement that must
not; the `make reference` exit code is non-zero if either misbehaves.
`make reference-gaps` prints only the divergences, with case id, doc link and
a one-line repro, in the shape a `docs/gaps.md` entry wants.

`corpus/reports/baseline.json` carries a `reference` section, and
`scripts/compare_baseline.py` diffs it case by case: a newly added case that
fails is new coverage, while a case flipping from conforming to not, or
disappearing, is a regression. `docs/reference-coverage.md` lists every page
in the language manual and the Lakeflow SQL reference with a status
(`done` / `queued` / `n/a`), so what is left is a file rather than a memory.

**State on 2026-09-19.** The Tier 1 batch took the corpus from 7 pages / 35
cases to 16 / 171: the GRANT family with the Unity Catalog securable list, the
CREATE CATALOG clause set, CREATE VIEW, EXECUTE IMMEDIATE, CONVERT TO DELTA and
CREATE VOLUME. On `main` at `33d8c8459` the reference report reads
`52/113 must-parse, 56/58 must-reject (25 informative, 31 vacuous)`, controls
ok; on released 4.3.0 it reads `43/113, 55/58 (20 informative, 35 vacuous)`.
The batch's evidence is the case ids in `docs/gaps.md`: it pinned the open
#8511/#8512/#8513/#8515/#8516/#8517 work, found three unclaimed gaps (the
CREATE CATALOG clause set beyond `MANAGED LOCATION`, the CREATE VIEW
data-source production and parenthesised `WITH` list, both #7405 regressions)
and one new over-acceptance (`GRANT ALL PRIVILEGES, SELECT` parses). Vacuous
rejections are expected while a whole statement is an open PR — on `main` the
`SHOW GRANTS` rejections prove nothing until #8516 merges.

**Adding a case.** Read the live page, transcribe a minimal skeleton of your
own construction (never an example body), and record the anchor and production
precisely enough to review the derivation. Then probe SQLFluff: if it
disagrees with the reference, either the transcription is wrong (fix it) or
the parser is (queue it in `docs/gaps.md` with the case id). The first gap the
corpus found on its own was the inline `FLOW` clause on `CREATE STREAMING
TABLE` — documented, used in the reference's own examples, and rejected by
`main` because the grammar has no FLOW clause on the table statement.

**The inline `FLOW` gap, and the bar a PR has to meet.** `CREATE [OR REFRESH]
[PRIVATE] STREAMING TABLE t FLOW …` is documented on the CREATE STREAMING
TABLE page, and the dialect had no FLOW clause there: `PRIVATE`/`STREAMING`
are patched onto `CreateTableStatementSegment` while
`CreateFlowStatementSegment` served only the standalone statement. A draft PR
exists ([#8520](https://github.com/sqlfluff/sqlfluff/pull/8520), 2026-09-19),
opened only after the bar below was met; the bar is also what to point at when
deciding whether any other draft is ready to leave draft. #8509 is the
cautionary tale, a grammar change merged without its interior bound. The bar:
read the CREATE STREAMING TABLE and AUTO CDC reference pages; confirm every
alternative binds its required tokens (`INSERT [ONCE] BY NAME query`, `AUTO
CDC auto_cdc_flow_spec`, `REPLACE WHERE predicate BY NAME query`, `REPLACE
USING ( column_name [, …] ) SEQUENCE BY sequence_column BY NAME query`); bind
`FLOW` itself to `STREAMING` so `CREATE TABLE t FLOW …` stays rejected; add
full-form fixtures *and* the partial-form rejections, which the reference
corpus carries as `create-streaming-table.flow-*`; run the whole
`test/dialects/` directory rather than a filtered subset; and measure `make
corpus` and `make reference` on the branch. Only then is it a pull request.

This does not replace the scraped corpus — it covers the complement. Published
SQL tells you what breaks in practice; the reference tells you what the grammar
is supposed to be.

## Contributing upstream

`docs/gaps.md` is the queue. Each entry is a construct with a minimal repro
verified against SQLFluff `main`. The workflow that works:

1. `make gaps` to find or confirm a construct.
2. Reproduce it in one line before touching any grammar.
3. Fix it in a SQLFluff fork checkout, with a `.sql` fixture and the generated
   `.yml`.
4. **Run the whole `test/dialects/` directory**, not a filtered subset —
   `databricks_test.py` holds hand-written rejection tests that a
   `dialects_test.py -k databricks` filter never runs. That gap let a genuinely
   wrong change look green.
5. Check the vendor documentation before removing a rule someone wrote on
   purpose. An existing test asserting a constraint usually means the
   constraint is real.
6. SQLFluff's CONTRIBUTING requires disclosing material AI assistance in the
   pull request.
