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
make baseline       # regenerate corpus/reports/baseline.json
make test
```

To measure an **unmerged** SQLFluff branch — the main workflow — install the
fork over the release:

```bash
.venv/bin/pip install -e ../sqlfluff     # a fork checkout on any branch
make gaps
```

Nothing here needs Java, and there is no code generation step.

## Layout

```
src/dbsqlparse/corpus/sources.py    the 14 pinned sources -- pinned to exact commits
src/dbsqlparse/corpus/fetch.py      downloads them into corpus/cache/
src/dbsqlparse/corpus/runners.py    the parsers under test (SQLFluff, sqruff)
src/dbsqlparse/corpus/harness.py    recall + rejection measurement
src/dbsqlparse/corpus/mutate.py     valid SQL -> guaranteed-invalid SQL
src/dbsqlparse/corpus/cli.py        `python -m dbsqlparse.corpus`
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
