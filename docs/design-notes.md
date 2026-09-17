# Design notes

Decisions that are not obvious from the code, and the reasoning behind them.
`AGENTS.md` states the resulting constraints; this file records why they exist.

## Why the Spark grammar needs a patch step

Spark writes `SqlBase{Lexer,Parser}.g4` for ANTLR's Java target. The `@members`
blocks and inline actions are Java source, and ANTLR copies them verbatim into
whatever it generates — under the Python target that produces a file which will
not import.

`scripts/patch_grammar.py` strips those blocks and points each grammar at a
Python `superClass` in `src/dbsqlparse/antlr_base.py`. Every rewrite is an
exact-string substitution that asserts an expected occurrence count, so
re-vendoring a newer Spark **fails loudly** rather than emitting a parser that
cannot import. This was verified against Spark v4.2.0, which added a lexer tag
stack the current anchors do not know about.

Loosening an anchor to make a patch apply is always the wrong fix. An anchor
that stops matching is upstream drift to port.

## Why case folding lives in `LA()` only

Spark's grammar is case-sensitive: every keyword is an uppercase literal
(`AS: 'AS';`). Case-insensitivity comes from a Scala stream wrapper applied
before lexing, which is not part of the `.g4`. Without porting it,
`select ... as x` is a syntax error while `AS x` is fine.

`UpperCaseInputStream` folds case for the lexer DFA in `LA()` only, leaving
token text untouched. That matters because the naming rules read those
identifiers — folding the buffer would make every identifier look uppercase and
break `identifier-case` entirely.

## Why parser generation rewrites the header

ANTLR stamps the grammar's absolute path into every generated file header.
Because the generated sources are committed, regenerating from a different
checkout produced a spurious one-line diff on a 37k-line file: two people
running `make grammar` would disagree for no real reason.

`scripts/generate_parser.sh` rewrites that header to a repo-relative path.
Confirmed by regenerating from a separate clone — headers differed, everything
else was byte-identical, and after the fix a fresh clone matches byte for byte.

`make verify-generated` regenerates and fails if the committed parser has
drifted from the grammar it came from. It is meant for CI.

## Why keywords are the risky part, not rules

Defining a lexer token stops that word matching `IDENTIFIER`. Add `PATTERN` as
a keyword and `SELECT pattern FROM t` becomes a syntax error — a false positive
that blocks a good merge request. Extending coverage from 23 constructs to over
100 meant 79 new keywords, so 79 chances to break ordinary SQL.

`grammar/extensions/keywords.txt` is therefore the single source of truth: one
entry generates the lexer token **and** entries in both `nonReserved` lists, so
adding a token and forgetting to keep it usable as an identifier is
structurally impossible. 395 generated tests check every keyword still works as
a column name, alias, table name and in DDL, in both keyword modes.

`DELTA` was the riskiest of them, because real-world Databricks SQL writes
`USING delta` throughout.

## Why generation runs ANTLR with `-Werror`

ANTLR reports an undefined token used in a parser rule as a *warning*, and the
result is an alternative that can never match — syntax the project believes it
supports but silently does not. Turning warnings into errors caught four such
tokens while the extensions were being written: `REMOVE`, `MODEL`, `DELTA` and
`UPDATES`.

## Why the injection tests damage the grammar on purpose

Each Databricks extension is spliced into the vendored grammar at an anchor.
When a newer Spark moves one, the dangerous outcome is not a crash — it is the
injection quietly doing nothing, generation succeeding, and the result being a
parser silently missing syntax it claims to support. Nothing looks wrong,
because the tests that would catch it cover the syntax that just stopped being
covered.

`tests/test_patch_grammar.py` damages the vendored grammar deliberately and
asserts each injection raises, plus the mirror case that a successful injection
actually changes something.

Writing those tests exposed a flaw in checking this by hand: damaging a
substring the anchor *shares* with other parts of the grammar (for example
`havingClause?`, which appears in more than one query specification) leaves the
real anchor intact, so the check passes while proving nothing. The
parametrisation damages the exact anchor text and every occurrence of it.

## Why rules never see ANTLR contexts

Rules read a semantic model (`src/dbsqlparse/analysis.py`), not parse trees.
Writing a rule then needs no knowledge of Spark's grammar, and when Spark
renames a grammar rule the breakage is confined to one file instead of
spreading across every rule.

## Why type resolution never guesses

`type-naming` fires only where the file itself states a type — a `CREATE TABLE`
column declaration, or an explicit `CAST(x AS BOOLEAN) AS flag`.
`CAST(a AS INT) + 1` is an addition, not a cast, so it has no known type and
rules skip the column silently.

A linter that guesses a type and then reports on the guess is worse than one
that stays quiet: the guess is invisible in the diagnostic, so a wrong report
looks like a real finding.

## Why the mutation corpus has two tiers

A corpus of only-valid SQL cannot distinguish a good parser from one that
accepts everything, so the harness mutates valid statements into invalid ones
and checks they are rejected.

Only `guaranteed` mutations are scored. `weak` ones — deleting a comma or a
`FROM` — are reported but never scored, because Spark's default keyword mode
legitimately re-parses them as valid:

```sql
SELECT a, b FROM t   -->   SELECT a b FROM t      -- valid: b aliases a
SELECT a FROM t      -->   SELECT FROM t          -- valid: t aliases FROM
```

Scoring those would punish the parser for being correct.

## Why the example configs contradict each other

`examples/snake-case-team.toml` uses type *suffixes* (`active_ind`,
`created_date`); `examples/hungarian-team.toml` uses type *prefixes*
(`is_active`, `dt_created`). A test asserts the two disagree. If they ever
agreed, they would stop demonstrating that the rule engine has no preference of
its own.

## Known limitation: GRANT and REVOKE

Spark does not really parse them. They fall into
`unsupportedHiveNativeCommands`, a catch-all whose body is `.*?`, so they are
*accepted* but nothing about them is validated. `DENY` has a real rule because
it had no catch-all to fall into.
