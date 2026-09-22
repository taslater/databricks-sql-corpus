## What

`CREATE CATALOG`'s full clause set, and the separate foreign-catalog
production. #8511 bound `MANAGED LOCATION`; this binds the rest of the
[reference's grammar](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-catalog):

- The plain catalog takes any number of: `USING SHARE <provider>.<share>`,
  `MANAGED LOCATION`, `RETAIN DROPPED FOR <n> { HOUR | DAY | WEEK }`,
  `COMMENT`, `DEFAULT COLLATION`, `OPTIONS ( k = 'v' [ , ... ] )`.
- `CREATE FOREIGN CATALOG` requires both `USING CONNECTION <name>` and
  `OPTIONS ( ... )`, with an optional `COMMENT` between them.

The reference brackets each clause and follows the list with `[...]`, so the
clauses repeat and order freely: `AnyNumberOf` over a `OneOf`, replacing the
previous `AnySetOf` of two. Required tokens stay required — `USING SHARE
provider` without the dot, `RETAIN DROPPED FOR` without its quantity and
unit, an empty or value-less `OPTIONS` list, and the foreign-catalog partial
forms are all pinned as rejections.

`DROPPED` joins the unreserved list; `COLLATION`, `CONNECTION` and `SHARE`
are already carried by the inherited ANSI keyword sets.

## Tests

- `databricks/create_catalog.sql` gains the clause set and the foreign
  production (yml regenerated).
- `databricks_test.py` pins the incomplete clause forms above — rejection
  boundaries a valid-parse fixture cannot express.
- The whole `test/dialects/` directory, not a `-k databricks` subset.

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
