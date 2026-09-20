## What

Three Unity Catalog connectivity statements had no grammar:

- `ALTER CONNECTION c { [SET] OWNER TO … | RENAME TO … | OPTIONS (key value …) }`.
- `ALTER EXTERNAL LOCATION l { RENAME TO … | SET URL url [FORCE] | SET STORAGE
  CREDENTIAL c | [SET] OWNER TO … }`.
- `ALTER [STORAGE | SERVICE] CREDENTIAL c { RENAME TO … | [SET] OWNER TO … }`.

- [ALTER CONNECTION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-connection)
- [ALTER EXTERNAL LOCATION](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-location)
- [ALTER CREDENTIAL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-alter-credential)

## Tests

- New `databricks/alter_connection.sql`, `alter_external_location.sql` and
  `alter_credential.sql` (yml regenerated).
- `databricks_test.py` pins the four partial forms.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
