## What

The JSON path accessor accepted neither the `[ * ]` wildcard nor a
backquoted field name, both of which the
[JSON path expression reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-json-path-expression)
gives as accessors — `{ identifier | [ field ] | [ * ] | [ index ] }`, the
same set after a `.` or `:` — and whose own examples use backticked names:

- `SELECT raw:store.book[*]` failed at the star. `[*]` follows an element
  directly, with no delimiter of its own, so it is an alternative in the
  accessor loop rather than part of the after-delimiter group.
- ``SELECT raw:`full name` `` and ``raw:`fb:testid` `` failed at the colon.
  A delimited identifier is now one of the accessor alternatives.

This is the `sparksql` base, so `databricks` inherits it directly.

## Tests

- `sparksql/databricks_operator_colon_sign.sql` gains the accessor forms
  from the reference's examples, including a dotted array index and a
  backquoted name containing a colon (yml regenerated).
- The whole `test/dialects/` directory.

## AI assistance

Developed with AI assistance (opencode); every case above was run against
the branch's parser, not inferred from the documentation.
