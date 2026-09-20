## What

`ALTER RECIPIENT` and `ALTER PROVIDER` had no grammar. This binds
`ALTER RECIPIENT r RENAME TO … | [SET] OWNER TO … | SET PROPERTIES (key [=]
value …) | UNSET PROPERTIES (key …)`, with the equals sign optional and property
keys possibly dotted, and `ALTER PROVIDER p RENAME TO … | [SET] OWNER TO …`.

- [ALTER RECIPIENT](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-recipient)
- [ALTER PROVIDER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-provider)

## Tests

- New `databricks/alter_recipient.sql` and `alter_provider.sql` (yml regenerated).
- `databricks_test.py` pins empty `PROPERTIES`/`UNSET PROPERTIES` and a `RENAME
  TO` with no value.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
