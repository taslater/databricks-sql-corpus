## What

`MERGE WITH SCHEMA EVOLUTION INTO …` was rejected: the merge literal was just
`MERGE INTO`. Bind the optional clause between them, per the
[Delta MERGE reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into).

## Tests

- `databricks/merge_into.sql` gains the schema-evolution form (yml regenerated).
- `databricks_test.py` pins `MERGE WITH SCHEMA EVOLUTION t …` (the clause only
  applies before `INTO`) as a rejection.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

This pull request was co-authored with AI assistants: **Claude Opus 5**
(Anthropic) and **DeepSeek V4.1 Flash**. They drafted the grammar, the
fixtures and the rejection tests, and ran the measurements, under the
contributor's direction. Every construct was checked against the Databricks SQL
reference, and the changes were run through the whole `test/dialects/` suite,
the Python/Rust parity tests, `make reference` and `make corpus` before
submission. The human contributor remains responsible for the final pull
request, including its correctness, tests and maintainability, as
[CONTRIBUTING.md](https://github.com/sqlfluff/sqlfluff/blob/main/CONTRIBUTING.md#ai-assisted-contributions)
requires.
