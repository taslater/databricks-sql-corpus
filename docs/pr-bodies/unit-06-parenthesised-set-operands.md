## What

`EXCEPT` with a parenthesised operand was rejected:

    (SELECT c FROM number1) EXCEPT (SELECT c FROM number2);

The guard that keeps a wildcard exclusion (`SELECT * EXCEPT (col)`) from
being read as a set operator excluded *any* bracketed content after
`EXCEPT`, so a parenthesised subquery operand was excluded with it. Narrow
the exclude to the shape it is meant to catch: a bracketed, delimited list
of column references. `EXCEPT (col)` still parses as a wildcard exclusion.

## Tests

- `sparksql/select_set_operators.sql` gains the parenthesised-operand form,
  next to the existing `EXCEPT ALL (SELECT ...)` (yml regenerated).
- The whole `test/dialects/` directory.

## AI assistance

Developed with AI assistance (opencode); every case above was run against
the branch's parser, not inferred from the documentation.
