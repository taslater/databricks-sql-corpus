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
