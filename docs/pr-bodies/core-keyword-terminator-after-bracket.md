## What

A keyword terminator was only honoured when preceded by whitespace, so a
keyword glued to a closing bracket was read as an **implicit alias** instead of
ending the clause:

```sql
SELECT (a)FROM t;   -- unparsable: `FROM` taken as the alias of `(a)`
SELECT (a) FROM t;  -- parses
```

The two differ only by a whitespace token. The same shape appears in real SQL —
`count(DISTINCT sk)FROM t` in a published notebook, and `(a)WHERE`,
`(a)ORDER BY`, `(a)LIMIT` — and the keyword is swallowed as a naked identifier
alias, so the rest of the statement is unparsable. It reproduces on `ansi`,
`sparksql` and `databricks`, and on released 4.3.0, so it is core rather than
dialect-specific.

`greedy_match()` requires whitespace before an all-alphabetic terminator to
avoid a keyword being matched mid-expression. But a closing bracket is already
an unambiguous code boundary — nothing can absorb the keyword into the
preceding token — so the requirement is dropped after `)`, `]` and `}`.

The Rust parser mirrors the same rule (`is_preceded_by_whitespace`), so it is
updated too; without that the Python-vs-Rust parity corpus test fails on the
new fixture.

## Tests

- New `ansi/select_bracket_then_keyword.sql`: `(a)FROM`, `(a)WHERE`,
  `(a)ORDER BY`, `(a)LIMIT` and `count(DISTINCT sk)FROM`. Every case fails to
  parse before the change.
- `test/dialects/` and `test/core/parser/` in full, which includes the
  `python-vs-rust` parity corpus test, both engines green.
- The whole `test/` suite: no new failures.
- The published notebook whose `count(DISTINCT sk)FROM` motivated this now
  parses.

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
