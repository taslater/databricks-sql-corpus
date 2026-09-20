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

Developed with AI assistance (opencode); every case above was run against
the branch's parser, not inferred from the documentation.
