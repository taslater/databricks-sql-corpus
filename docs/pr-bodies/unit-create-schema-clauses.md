## What

`CREATE SCHEMA` / `CREATE DATABASE` took only a name, `COMMENT`, a location and
`WITH DBPROPERTIES`, in a fixed order. The
[reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-schema)
brackets each clause and follows the list with `[...]`, so the clauses repeat and
appear in any order:

```
[ COMMENT | DEFAULT COLLATION name | { LOCATION path | MANAGED LOCATION path } |
  RETAIN DROPPED FOR number { HOUR | DAY | WEEK } |
  WITH DBPROPERTIES ( … ) ] [...]
```

Bind them all as a repeating `AnyNumberOf`, and factor `DEFAULT COLLATION` and
`RETAIN DROPPED FOR` into shared grammars (CREATE CATALOG and CREATE VIEW already
carry their own copies of the former).

## Tests

- `databricks/create_database.sql` gains the clause set (yml regenerated).
- `databricks_test.py` pins the ten partial forms: `IF NOT` without `EXISTS`,
  `IF EXISTS`, a comment with no text, `DEFAULT COLLATION` and both locations
  with no name/path, `RETAIN DROPPED FOR` with no number or no unit, and empty
  or value-less `DBPROPERTIES`.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
