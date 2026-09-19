# databricks-sql-corpus

A corpus of published Databricks SQL, and a harness that measures
[SQLFluff](https://github.com/sqlfluff/sqlfluff) against it.

Every file SQLFluff cannot parse is a candidate bug in its Databricks dialect.
This finds them, groups them by construct, and checks that fixes contributed
upstream do not make SQLFluff accept invalid SQL in exchange.

## What it has found

Nineteen bugs in SQLFluff's Databricks support, found by running the corpus
and grouping the failures by construct. Thirteen have pull requests upstream,
five of them merged; six more are recorded in `docs/gaps.md` without one
yet.

Recall over the corpus, before and after. One file is skipped as a different
dialect, so 866 of the 867 are measured:

| source | SQLFluff 4.3.0 | `main` today |
| --- | ---: | ---: |
| `dbx-learn-databricks` | 13/46 — 28.3% | **41/46 — 89.1%** |
| `dbx-dlt-notebooks` | 14/19 — 73.7% | **18/19 — 94.7%** |
| `dbx-lakeflow-connector` | 50/54 — 92.6% | 51/54 — 94.4% |
| **overall** | 730/866 — 84.3% | **758/866 — 87.5%** |

Reference conformance moved with it. The doc-derived corpus now carries 253
cases over 27 reference pages: released 4.3.0 accepts 95 of the 170 must-parse
cases and `main` accepts 104. Rejection over the scraped corpus held at 100%
throughout — the fixes widened what SQLFluff accepts without letting invalid
SQL through, which is the trade the mutation corpus exists to check.

One source moved the other way. `spark-sql-tests` went from 74.7% to 72.7%,
because upstream tightened empty-parenthesis handling and six of those files
are Spark's own labelled *negative* cases. Recall scores a parser getting
stricter-and-more-correct as a loss. That is the metric's known blind spot,
not a regression.

## Why this exists

It started as an ANTLR parser, built from Spark's `SqlBase` grammar because
SQLFluff appeared not to cover Databricks SQL. Measured head to head, SQLFluff
scored **59/59** on its own Databricks fixtures and the parser here scored
**36/59** — and the advantage this project genuinely had turned out to be
notebook preprocessing, not parsing. So the parser was deleted and the effort
went into fixing SQLFluff instead of competing with it.

`docs/design-notes.md` keeps the reasoning from the parser era.

## Quick start

```bash
make venv
make corpus-fetch     # ~22 MB from 14 pinned public repositories
make corpus           # recall + rejection + reference conformance
make gaps             # failures grouped by construct
make reference        # doc-derived cases only -- no fetched corpus needed
make reference-gaps   # just the divergences, shaped for docs/gaps.md
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

**Reference conformance** — a third number, from `corpus/reference/`: cases
transcribed from the Databricks SQL reference, each `must-parse` or
`must-reject` and citing the page and anchor it came from. The scraped corpus
samples what people publish, not what the dialect allows, so a construct no
file uses — and any partial form of it — is invisible to recall and to
mutation. This is the corpus that catches those, and the one that would have
caught the `REPLACE USING (…) SEQUENCE BY …` defect before it merged.

## The corpus

867 files across 14 sources, each pinned to an exact commit: Apache Spark's
SQL test suites and its TPC-DS / TPC-H / SSB queries, SQLFluff's own
`databricks` and `sparksql` dialect fixtures, and real published Databricks
work — Databricks' own Delta Live Tables and developer-relations notebooks, a
Lakeflow connector project, a published book's companion code, and public
teaching material.

The cache is not committed: every source is reproducible from
`src/dbsqlparse/corpus/sources.py`. `corpus/reports/baseline.json` is
committed, so a change in accuracy shows up in a diff, including case-by-case
reference conformance.

`corpus/reference/` is committed, because it is not scraped from anywhere: it
is a small set of cases written from the
[SQL reference](https://docs.databricks.com/aws/en/sql/language-manual/), one
file per page, with the anchor and production recorded so a reviewer can check
the transcription against the doc.

## Contributing upstream

`docs/gaps.md` is the queue — each entry a construct with a minimal repro
verified against SQLFluff `main`, plus the pull requests already open.

## Licence

Apache-2.0. The corpus itself is third-party work under its own licences,
fetched on demand and never redistributed; see `NOTICE`.
