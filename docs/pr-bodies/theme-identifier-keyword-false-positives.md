## What

Legal identifiers and aliases rejected because a keyword elsewhere has the
same spelling. Both mechanisms were found by substituting the dialect's
keywords into ordinary identifier positions, and both are settled by the
[reserved words reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words),
which says Databricks "does not formally disallow any specific literals from
being used as identifiers".

- **`LEFT` and `RIGHT` were globally reserved**, undoing the merged
  `sparksql` fix (#8050) that lets them be lambda parameters and column
  names. The reference puts them on the alias-only list, so they still
  cannot be an unquoted table alias, and the alias matcher enforces that.
- **`KEYS`, `PIVOT` and `WINDOW` were rejected as aliases** for the same
  reason, even with an explicit `AS`: none is on the alias-only list, but
  the alias exclude covered the explicit form too. The alias grammar is
  split so an explicit `AS` alias may use them while an implicit alias still
  cannot consume a following clause keyword.
- **`DESCRIBE history.tbl`** collided with the `DESCRIBE HISTORY` statement
  prefix, even though `history` is a legal table name and plain
  `DESCRIBE TABLE history.tbl` parsed. The Delta statements are tried before
  the general `DESCRIBE` instead of excluded from it, so the collision
  resolves by fall-through.
- **`SELECT * FROM stream`** was rejected because `STREAM` is part of the
  `FROM STREAM <function>` relation spelling. `STREAM` is now a prefix
  keyword only when a table expression follows it.

`databricks` keeps its own `AliasExpressionSegment`, because it also
excludes `FOR` for the anonymous `PIVOT (agg FOR col IN (…))` form.

## Tests

- New fixtures `databricks/select_lambda.sql`, `databricks/table_alias.sql`
  and `databricks/select_from_stream.sql`; `sparksql/table_alias.sql` and
  `sparksql/describe_table.sql` extended (yml regenerated).
- `databricks_test.py` pins the alias boundary that a valid-parse fixture
  cannot express: `SELECT * FROM t AS left` stays a rejection.
- The whole `test/dialects/` directory, not a `-k databricks` subset.
- The reference case `array-sort.lambda-keyword-parameters` flips, and
  `sqlfluff-sparksql/select_lambda.sql` parses in the scraped corpus.

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
