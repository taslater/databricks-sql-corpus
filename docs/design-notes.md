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

## What the Databricks corpus found, and what it cost to close

Adding 25 real Databricks files dropped `dbx-dlt-notebooks` to 20% recall and
`dbx-devrel` to 60%. Both are now 100% and 80%. The interesting part is that
only about half the work was Databricks syntax at all.

**The biggest single win was not a Databricks feature.** `split_statements`
handed any trailing `-- comment` after the last semicolon to the parser as if
it were a statement. A comment is not SQL, so the parser reported a syntax
error at EOF and marked the file broken. That one bug was suppressing **51
files of Spark's own golden-file tests**: fixing it moved `spark-sql-tests`
from 77.6% to 94.4%, on a suite that had been in the corpus from the start.
A corpus of 495 files had never caught it, because Spark's test resources
rarely end on a comment and real notebooks almost always do. Comments arrive on
the lexer's hidden channel, so the splitter now keeps a chunk only when it has
seen a default-channel token.

The exception is an unclosed `/*`, which swallows the rest of the file as a
single hidden token and so looks identical to pure commentary. Dropping that
would turn a broken file into a silently clean one, which is the worst possible
direction for a linter to fail in. Spark's lexer already records the case and
the splitter now consults it.

**Two of the five causes I first wrote up here were wrong**, and both were
wrong the same way: the diagnostic pointed at a token several positions after
the real problem.

- Double-quoted path literals were never broken. `SELECT * FROM "/path"` has
  always parsed. The actual cause was the missing `STREAM` keyword: in
  `FROM STREAM read_files("/p", …)`, `STREAM` lexed as a table name and
  `read_files` as its alias, which made the argument list a *column alias
  list*, and the first string argument was the first thing that could not be an
  identifier. The error landed on the path, so it looked like a string-literal
  bug.
- The "CTE without `AS`" was not a CTE problem either. `${test.nrows}` went
  unsubstituted — the widget pattern did not allow a dot — and the leftover `$`
  derailed the parse well before the `WITH`.

The lesson is worth keeping: on a grammar this size, the token ANTLR reports is
where recovery gave up, not where the input went wrong.

**What was genuinely missing**, all now supported: the `LIVE` spelling
(`CREATE [OR REFRESH | STREAMING] LIVE TABLE`, which every published pipeline
still uses), `MATERIALIZED VIEW` after `OR REFRESH` rather than only
`OR REPLACE`, `TEMPORARY` streaming tables, the `STREAM` relation prefix, DLT
expectations (`CONSTRAINT x EXPECT (…) ON VIOLATION DROP ROW | FAIL UPDATE`),
and constraints inside a `CREATE TABLE` column list — inline `PRIMARY KEY`,
inline `FOREIGN KEY REFERENCES`, and named table-level constraints, none of
which Spark's `colDefinitionList` allows.

Five keywords were added for this: `LIVE`, `STREAM`, `EXPECT`, `VIOLATION`,
`FAIL`. Every one is a plausible column name, which is exactly why they went
through `keywords.txt` — the generated tests check each still works as a
column, alias, table name and in DDL, in both keyword modes.

**Two files still fail, and both should.** `PipelineSetting.json.sql` is JSON
with a `.sql` extension; it is now reported as a skip, on the same footing as
the existing T-SQL check — wrong dialect, not wrong parser. The other contains
`OPTIMIZE <table>`, a documentation placeholder for the reader to fill in. It
is not valid SQL and a parser that accepted it would be worse.

## Widening the corpus again, and what it cost

A code search finds ~12,000 public `.sql` files carrying the Databricks
notebook header, so the limit is not supply — it is picking sources that are
clearly licensed and that exercise different syntax rather than repeating the
same few statements. Three were added, taking the Databricks corpus from 25
files to 125:

| source | licence | what it adds |
| --- | --- | --- |
| `dbx-learn-databricks` | Apache-2.0 | administration, Unity Catalog, time travel |
| `dbx-packt-cookbook` | MIT | widget DDL, volumes, published-book SQL |
| `dbx-descomplicando-sql` | Unlicense | everyday analytics, 100% on arrival |

They found **11 more gaps**, now recorded in `GAPS` as strict xfails: widget
DDL (`CREATE WIDGET TEXT|DROPDOWN`, `REMOVE WIDGET`), `@v0` time travel on both
names and paths, `DESCRIBE HISTORY` used as a relation, `SHOW GRANTS ON` an
arbitrary object, `MANAGED LOCATION`, `STREAMING LIVE VIEW`, and column-level
`SET`/`UNSET TAGS`.

`dbx-descomplicando-sql` passing 39/39 on arrival is worth as much as the
failures: it is the everyday-analytics case, and it says the gaps are
concentrated in Databricks-specific DDL rather than spread through ordinary
SQL.

### The mutation harness was scoring two things wrong

Widening the corpus dropped rejection from 100% to 99.9%, and investigating it
rather than regenerating the baseline found the mutator at fault, not the
parser. Two mutations were tiered GUARANTEED when they are not guaranteed at
all:

- **Truncating after `AND`/`OR`.** Both are non-reserved in Spark's default
  keyword mode, so `SELECT a OR` reads as `SELECT a AS OR` — a column aliased
  to the word OR, which is valid. It depends on position (`WHERE x AND` has no
  such reading), so it cannot be predicted at generation time. This is the same
  phenomenon already documented for `delete-comma`, and it now has its own WEAK
  kind.
- **Truncating after `=` inside `SET`.** `SET spark.sql.some.key =` with no
  value is a legitimate config assignment. Everywhere else a trailing `=` is a
  syntax error, so the mutator now skips an `EQ` whose statement opens with
  `SET` rather than dropping the mutation everywhere.

Both were scoring correct parser behaviour as a false negative. Rejection is
back to 100%, now on 1320 guaranteed mutations.
