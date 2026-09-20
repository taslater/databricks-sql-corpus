## What

Three notebook-boundary defects in the `databricks` dialect, all of them
cases where a magic cell swallowed the blank line its `-- COMMAND`
separator is made of, leaving the next statement unparsable:

- A `%`-prefixed line inside an open cell. Databricks marks every line of a
  cell with `-- MAGIC`; the language is named by the first directive, and a
  later line may itself start with `%` — an `%md` cell quoting `%pip`, for
  example. The grammar only allowed plain body lines, so the quoted command
  ended the cell.
- A `-- MAGIC` line with a trailing space. The `[^%]` in `magic_single_line`
  and `magic_line` could match the newline itself, so the line took the
  blank line after it with it.
- A cell whose *last* line is a standalone directive (`-- MAGIC %fs`).
  `magic_start` consumed its trailing `(\r?\n)`, with the same effect.

Match only `[^\n%]` in the line bodies and leave the newline to the lexer.

Both shapes appear in published notebooks: the first in
`dbx-learn-databricks`, the other two in a `dbx-devrel` notebook, whose
`-- MAGIC %fs …` line carries a trailing space.

## Tests

- `databricks/magic_single_line_with_body.sql` gains the quoted-command
  cell; the `magic_start` fixtures move the newline out of the token (yml
  regenerated).
- `databricks_test.py::test_magic_cell_boundaries` pins the trailing-space
  and last-line-directive cases. They are in the test module rather than a
  fixture because pre-commit strips trailing whitespace, and one boundary is
  exactly a trailing space.
- The whole `test/dialects/` directory, not a `-k databricks` subset, since
  that filter skips the hand-written tests in `databricks_test.py`.

## AI assistance

Developed with AI assistance (opencode); every case above was run against
the branch's parser, not inferred from the documentation.
