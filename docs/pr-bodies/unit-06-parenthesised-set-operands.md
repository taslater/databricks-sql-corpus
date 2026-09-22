## What

`EXCEPT` with a parenthesised operand was rejected:

    (SELECT c FROM number1) EXCEPT (SELECT c FROM number2);

The guard that keeps a wildcard exclusion (`SELECT * EXCEPT (col)`) from
being read as a set operator excluded *any* bracketed content after
`EXCEPT`, so a parenthesised subquery operand was excluded with it. Narrow
the exclude to the shape it is meant to catch: a bracketed, delimited list
of column references. `EXCEPT (col)` still parses as a wildcard exclusion.

## Tests

- `sparksql/select_set_operators.sql` gains the parenthesised-operand form,
  next to the existing `EXCEPT ALL (SELECT ...)` (yml regenerated).
- The whole `test/dialects/` directory.

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
