# Contributing

This is a measurement harness, not a library. Most contributions are one of
three things.

## Adding a corpus source

`src/dbsqlparse/corpus/sources.py`. Pin to an exact commit SHA, never a
branch — a moving source silently reshapes every number the harness reports.

Check what you are adding is really Databricks SQL. Several repositories
named for Databricks contain Oracle or T-SQL; dbt projects contain Jinja
templates rather than SQL; Databricks Academy material contains deliberate
`<FILL_IN>` blanks. The harness already skips JSON wearing a `.sql`
extension, and T-SQL in local-only sources.

Adding a source that exposes a gap is **not** a regression, and
`scripts/compare_baseline.py` is written to tell the two apart.

## Changing the mutation tiers

`src/dbsqlparse/corpus/mutate.py`. A mutation is `guaranteed` only if it is
invalid on structural grounds that no keyword rule can rescue. Anything that
might legitimately re-parse is `weak` and is reported but never scored.

Getting this wrong reports correct behaviour as a failure. Two mutations have
already had to be re-tiered after a real corpus disproved an assumption about
them, so the bar for adding a `guaranteed` mutation is a demonstration that it
cannot parse, not an argument that it should not.

## Fixing a gap upstream

The point of the project. `docs/gaps.md` is the queue.

1. `make gaps` to find or confirm the construct.
2. Reduce it to a one-line repro before touching any grammar.
3. Fix it in a [SQLFluff](https://github.com/sqlfluff/sqlfluff) fork, with a
   `.sql` fixture and its generated `.yml`.
4. Run the whole `test/dialects/` directory. A filtered run skips
   `databricks_test.py`, which holds hand-written rejection tests.
5. Read the Databricks documentation before removing a constraint an existing
   test asserts — the test is usually right.
6. SQLFluff's CONTRIBUTING requires disclosing material AI assistance.

Then re-measure here: `pip install -e ../sqlfluff && make gaps`.

## Style

Python ≥ 3.10, `from __future__ import annotations`, fully annotated,
dataclasses for value types. Module docstrings carry the *why*, not a summary
of the code; comments explain reasoning and trade-offs, not mechanics. Prose
uses British spelling in places (`normalised`, `tokenise`) — match the
surrounding file.

Every probe or batch check must include a known-bad control. Three times in
this project's history a harness bug made failure look like success.
