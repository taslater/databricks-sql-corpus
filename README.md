# databricks-sql-corpus

A corpus of published Databricks SQL, and a harness that measures
[SQLFluff](https://github.com/sqlfluff/sqlfluff) against it.

Every file SQLFluff cannot parse is a candidate bug in its Databricks dialect.
This finds them, groups them by construct, and checks that fixes contributed
upstream do not make SQLFluff accept invalid SQL in exchange.

## Why this exists

It started as a parser. Databricks SQL is Spark SQL plus a large surface of
its own — `OPTIMIZE`, `ZORDER`, `COPY INTO`, Unity Catalog, Lakeflow
pipelines, notebook cells and widgets — and SQLFluff appeared not to cover it.
So this project generated a parser with ANTLR from Spark's own `SqlBase`
grammar and patched the Databricks syntax in.

Then it was measured head to head. SQLFluff scored **59/59** on its own
Databricks dialect fixtures; the parser here scored **36/59**. The advantage
this project genuinely had was notebook preprocessing, not parsing — and a
single upstream bug in SQLFluff's magic-cell handling accounted for most of
the difference.

So the parser was deleted, and the effort moved to fixing SQLFluff instead of
competing with it. What remains is the part that was always the real asset:
the corpus, and the machinery for turning it into upstream pull requests.

`docs/design-notes.md` keeps the reasoning from the parser era.

## Quick start

```bash
make venv
make corpus-fetch     # ~22 MB from 14 pinned public repositories
make corpus           # recall + rejection
make gaps             # failures grouped by construct
```

To measure an **unmerged** SQLFluff branch, install a fork checkout over the
release:

```bash
.venv/bin/pip install -e ../sqlfluff
make gaps
```

Nothing needs Java, a Databricks workspace, or network access at measurement
time.

## What it reports

**Recall** — how much valid SQL SQLFluff accepts. A miss is a false positive:
CI blocks a merge request that was fine. This is the number that decides
whether the tool is deployable.

**Rejection** — how much invalid SQL it catches. A miss is a false negative:
broken SQL sails through review. Measured by mutating corpus SQL into forms
that are invalid on structural grounds — unbalanced parentheses, unterminated
literals, doubled punctuation — which no keyword rule can rescue.

Recall matters more. A linter that blocks good work gets uninstalled; one that
misses a bug gets a second look at review.

A corpus of only-valid SQL cannot distinguish a good parser from one that
accepts everything, which is why both numbers exist.

## The corpus

867 files across 14 sources, each pinned to an exact commit: Apache Spark's
SQL test suites and its TPC-DS / TPC-H / SSB queries, SQLFluff's own
`databricks` and `sparksql` dialect fixtures, and real published Databricks
work — Databricks' own Delta Live Tables and developer-relations notebooks, a
Lakeflow connector project, a published book's companion code, and public
teaching material.

The cache is not committed: every source is reproducible from
`src/dbsqlparse/corpus/sources.py`. `corpus/reports/baseline.json` is
committed, so a change in accuracy shows up in a diff.

## Contributing upstream

`docs/gaps.md` is the queue — each entry a construct with a minimal repro
verified against SQLFluff `main`, plus the pull requests already open.

## Licence

Apache-2.0. The corpus itself is third-party work under its own licences,
fetched on demand and never redistributed; see `NOTICE`.
