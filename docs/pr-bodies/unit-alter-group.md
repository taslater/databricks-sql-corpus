## What

`ALTER GROUP parent { ADD | DROP } { GROUP g [, …] | USER u [, …] }` had no
grammar. Bind it, accepting commas between members.

[ALTER GROUP](https://docs.databricks.com/aws/en/sql/language-manual/security-alter-group)

## Tests

- New `databricks/alter_group.sql` (yml regenerated).
- `databricks_test.py` pins a missing parent principal and an `ADD` with no
  members.
- The whole `test/dialects/` directory and the Python-vs-Rust parity suite.

## AI assistance

Developed with AI assistance (opencode); every case above was run against both
parsers, not inferred from the documentation.
