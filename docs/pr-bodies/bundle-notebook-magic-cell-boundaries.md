## What

Fixes two boundary errors in the Databricks notebook `-- MAGIC` lexer, both of
which end a magic cell early and leave the following statement unparsable:

- `magic_start` consumed its trailing newline, and the `[^%]` in
  `magic_single_line` / `magic_line` was allowed to match one. A `-- MAGIC`
  line with a **trailing space**, or a cell whose last line is a **standalone
  directive**, therefore swallowed the blank line that separates the cell from
  its `-- COMMAND` separator. The lexer now matches only non-newline
  characters in the body of a magic line and leaves the newline to the lexer.

A second commit fixes the related grammar boundary: a cell's language comes
from its first directive, so a later directive-shaped line — an `%md` cell
quoting `%pip`, for example — is body text. The grammar previously allowed only
plain `magic_line` body lines after the directive and ended the cell instead.

## Tests

- `test/dialects/databricks_test.py::test_magic_cell_boundaries` pins both
  whitespace boundaries as **clean-parse** checks, not rejections: trailing
  whitespace is stripped from `.sql` fixtures, and one boundary is exactly a
  trailing space, so a fixture cannot express it.
- The affected published notebook (`my_streaming_table.sql`) now parses; the
  SCD notebook advances past its magic cells — it now fails later, on the
  separately queued `COPY INTO`.
- Whole `test/dialects/` **7032 passed**; corpus mutation stays **100%**
  (1326/1326).

The lexer regexes are Rust-owned, so the tables were rebuilt
(`utils/rustify.py build` + `maturin build`) and both engines checked.

## AI assistance

Developed with AI assistance (opencode); every case was run against both
engines rather than inferred from the documentation.
