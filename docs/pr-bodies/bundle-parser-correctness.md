## Summary

Fixes a set of parser false positives and gaps in the SparkSQL and Databricks
dialects, all found by an independent doc-derived conformance corpus:

- **`IDENTIFIER(...)` as a column, `IDENTIFIER()` rejected.** A Databricks
  column reference now inherits the object reference, so the identifier clause
  can appear as a column (`SELECT IDENTIFIER('col')`), and `IDENTIFIER` is
  excluded from function names, so the argument-less `IDENTIFIER()` is
  rejected.
- **`LEFT` and `RIGHT` are unreserved again.** The SparkSQL `LEFT`/`RIGHT`
  join keywords had made them illegal as identifiers. `KEYS`, `PIVOT` and
  `WINDOW` are legal *explicit* aliases (`AS PIVOT`) while still excluded from
  implicit aliases.
- **`DESCRIBE history.tbl`.** The general `DESCRIBE` no longer excludes the
  `HISTORY`/`DETAIL` keywords, and the Delta `DESCRIBE HISTORY`/`DESCRIBE
  DETAIL` statements are tried first, so an unqualified `DESCRIBE HISTORY tbl`
  still binds to them.
- **A table named `stream`** can be referenced in `FROM` (`SELECT * FROM
  stream`), which the streaming `STREAM` prefix previously made unparsable.
- **JSON path** `[*]` wildcard and delimited identifiers
  (`raw:store.book[*]`, ``raw:`full name` ``).
- **A parenthesised subquery is a set-operation operand**
  (`EXCEPT (SELECT ...)`); only `EXCEPT (col, ...)` is treated as a wildcard
  exclusion.

Fixes the reference cases `identifier-clause.without-argument`,
`array-sort.lambda-keyword-parameters`, `json-path.star`,
`json-path.delimited-identifier` and `set-operators.parenthesised-operands`,
and the published files `spark-tpcds/q87.sql` and
`sqlfluff-sparksql/select_lambda.sql`.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9394 passed, 2 xfailed**
- reference conformance: **504 → 508 must-parse**, **363 → 364 must-reject
  (informative)**, no regressions
- corpus: **542 → 544** valid files, rejection **100%** (1325/1325)

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
