## What

`ALTER CATALOG` and `ALTER SCHEMA` / `ALTER DATABASE` rejected three documented
clauses: `DEFAULT COLLATION`, `SET MANAGED LOCATION` and
`[SET] RETAIN DROPPED TO …`. This binds them (plus `OPTIONS` on a catalog).

The two clauses are shared grammars: the collation value may be a bare
identifier (as on CREATE) or a quoted string (as on ALTER), and `RETAIN DROPPED`
takes `FOR` on the CREATE statements and `TO` on ALTER.

- [ALTER CATALOG](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-catalog)
- [ALTER SCHEMA](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-schema)

## Tests

- `databricks/alter_catalog.sql` and `alter_database.sql` gain the clauses (yml
  regenerated).
- `databricks_test.py` pins the partial forms (a collation or managed location
  with no value, `RETAIN DROPPED` with no unit, empty `TAGS`/`DBPROPERTIES`).
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
