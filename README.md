# databricks-sql-parser

A static parser and linter for Databricks SQL, built on Spark's own ANTLR
grammar. It runs entirely locally: no workspace connection, no catalog
metadata, no network at run time.

Made for catching problems before review — in your editor, in a pre-commit
hook, or as a CI job that blocks a pull or merge request.

**This project ships no naming conventions.** Every rule is off until you turn
it on, and the naming rules do nothing until you supply patterns. What a column
should be called is your team's decision, not the tool's. See
[examples/](examples/) for several complete configurations, including two that
deliberately contradict each other.

## Install

```bash
pip install databricks-sql-parser
```

Nothing but the ANTLR Python runtime is required. Java is needed only to
regenerate the parser, which contributors do and users never do.

## Quick start

Check syntax — no config needed:

```bash
dbsqlparse path/to/file.sql
dbsqlparse sql/                          # recurses for *.sql
echo "SELECT a,, b FROM t" | dbsqlparse -
```

Add rules by dropping a `.dbsqlparse.toml` in your repo root:

```toml
[rules.type-naming]
severity = "error"
patterns = { BOOLEAN = "_ind$", TIMESTAMP = "_timestamp$" }

[rules.drop-requires-if-exists]
severity = "error"

[rules.no-select-star]
severity = "warning"
```

```console
$ dbsqlparse models/orders.sql
models/orders.sql:3:3: error: [type-naming] BOOLEAN column 'isShipped' does not match the required pattern (expected to match /_ind$/)
models/orders.sql:6:1: error: [drop-requires-if-exists] DROP TABLE without IF EXISTS is not re-runnable (DROP TABLE IF EXISTS ...)
```

`dbsqlparse --list-rules` prints every rule with its options.

Exit codes are chosen for CI: `0` clean or warnings only, `1` at least one
error, `2` the tool could not run (bad config, missing file). A broken config
should not look like a SQL problem.

## Configuration

Config is found by walking up from each file, so a monorepo can hold different
conventions per directory. Either of these works:

```toml
# .dbsqlparse.toml
[rules.no-select-star]
allow_qualified = true
```

```toml
# pyproject.toml
[tool.dbsqlparse.rules.no-select-star]
allow_qualified = true
```

An unknown rule name or option is an error rather than a setting that silently
does nothing, and the message lists what is valid.

### Rules

| rule | what it checks |
| --- | --- |
| `type-naming` | Column names match a pattern chosen by their type |
| `identifier-case` | snake / upper_snake / camel / pascal |
| `identifier-length` | Maximum identifier length |
| `forbidden-name` | Names matching banned patterns, with your reason |
| `require-comment` | Tables and/or columns carry a COMMENT |
| `require-table-properties` | Required TBLPROPERTIES keys and values |
| `require-table-provider` | Constrain the USING clause |
| `no-select-star` | `SELECT *` hides schema changes |
| `drop-requires-if-exists` | DROP stays re-runnable |
| `insert-requires-column-list` | INSERT names its columns instead of binding by position |

### Types are resolved locally, never guessed

`type-naming` only fires where the file itself states a type — a `CREATE TABLE`
column declaration, or an explicit `CAST(x AS BOOLEAN) AS flag`. A column whose
type cannot be resolved without a catalog is skipped silently. `CAST(a AS INT) + 1`
is an addition, not a cast, so it has no known type.

This is a deliberate limit. A linter that guesses a type and reports on the
guess is worse than one that stays quiet.

## Writing a rule

Rules see an extracted semantic model, not ANTLR contexts, so you do not need
to know Spark's grammar:

```python
from dbsqlparse.rules import Rule, register

@register
class NoSingleCharColumns(Rule):
    id = "no-single-char-columns"
    description = "Column names must be longer than one character"
    defaults = {}

    def check(self, ctx):
        for column in ctx.analysis.columns:
            if len(column.name) == 1:
                yield self.violation(
                    ctx, column.position, f"column '{column.name}' is a single character"
                )
```

Every option a rule accepts must appear in `defaults`; anything else is
rejected at config load.

## How it works

Databricks SQL is a superset of Spark SQL, and Spark ships the ANTLR grammar
that its parser is actually generated from. We start there rather than guessing
at the syntax.

```text
grammar/vendor/       pristine SqlBase{Lexer,Parser}.g4, downloaded from a Spark tag
      |               scripts/fetch_grammar.py
      |
      |  + grammar/extensions/   Databricks-only syntax (keywords, statements, rules)
      v
grammar/databricks/   Java actions rewritten for Python, extensions injected
      |               scripts/patch_grammar.py
      v
src/dbsqlparse/generated/   ANTLR output, committed to the repo
                      scripts/generate_parser.sh  (fetches ANTLR; needs Java)
```

Three problems had to be solved to make Spark's grammar usable from Python.
They are the non-obvious part of this repo:

**1. The grammar is written for the Java target.** Its `@members` blocks and
inline actions are Java source, which ANTLR copies verbatim into whatever it
generates. Under the Python target that produces a file which will not import.
`scripts/patch_grammar.py` strips those blocks and points each grammar at a
Python `superClass` in `src/dbsqlparse/antlr_base.py`. Every rewrite is an
exact-string substitution with an expected occurrence count, so re-vendoring a
newer Spark tag *fails loudly* if Spark added an action we have not ported,
rather than silently emitting a broken parser.

**2. The grammar is case-sensitive.** Spark declares every keyword as an
uppercase literal (`AS: 'AS';`) and gets case-insensitivity from Scala, by
wrapping the stream in an `UpperCaseCharStream` before lexing. That wrapper is
not in the `.g4`. Without porting it, `select ... as x` is a syntax error while
`AS x` is fine. `UpperCaseInputStream` folds case in `LA()` only, so token text
keeps its original case — which matters, because the naming rules read those
identifiers.

**3. Real files are not plain SQL.** `src/dbsqlparse/preprocess.py` splits
Databricks notebook source on `-- COMMAND ----------`, skips `-- MAGIC` cells,
and replaces `${env}` widgets with a **same-length** identifier so that every
line and column in a diagnostic still points at the right place in the original
file. `:param` and `?` need no handling — Spark's grammar has rules for both.

Parsing is two-stage: SLL first, falling back to full LL only when SLL
complains. ALL(*) prediction on a grammar this size is too slow to run on save.

## Measuring accuracy

`make corpus` reports two numbers that mean different things:

| | what a miss means |
| --- | --- |
| **recall** — valid SQL we accept | false positive: CI blocks a good merge request |
| **rejection** — invalid SQL we catch | false negative: broken SQL sails through review |

A corpus of only-valid SQL can only measure recall, and a parser that accepts
everything scores 100% on it. So the harness also **mutates** valid statements
into guaranteed-invalid ones (unbalanced parens, unterminated literals, doubled
commas, dangling operators) and checks we reject them.

Mutations come in two tiers. Only `guaranteed` ones are scored. `weak` ones —
deleting a comma or a `FROM` — are reported but never scored, because Spark's
default keyword mode legitimately re-parses them as something valid:

```sql
SELECT a, b FROM t   -->   SELECT a b FROM t      -- valid: b aliases a
SELECT a FROM t      -->   SELECT FROM t          -- valid: t aliases FROM
```

Scoring those as misses would count correct behaviour as a bug.

## Keyword strictness

By default Spark treats almost every keyword as usable as an identifier, so
this parses cleanly:

```sql
SELECT * FROM t WHERE     -- valid: WHERE is a table alias
```

That is genuinely what Databricks does, so the parser matches it by default.
`--ansi-keywords` turns on ANSI reserved-keyword enforcement, which rejects it.
Worth considering as a lint rule rather than a parser default.

## Databricks coverage

Spark's grammar covers everything Spark and Databricks share. The
Databricks-only surface is added by `grammar/extensions/`, injected during the
patch step so that re-vendoring a newer Spark does not lose it:

| file | what it adds |
| --- | --- |
| `keywords.txt` | new keywords, one per line |
| `statements.g4frag` | alternatives spliced into the `statement` rule |
| `rules.g4frag` | supporting rules appended to the grammar |

Covered:

| area | syntax |
| --- | --- |
| Delta operations | `OPTIMIZE`/`ZORDER`, `VACUUM` (incl. `LITE`/`FULL`), `RESTORE`, `SHALLOW`/`DEEP CLONE` |
| Delta utilities | `CONVERT TO DELTA`, `FSCK REPAIR`, `GENERATE`, `REORG ... APPLY`, `DROP FEATURE` |
| Ingestion | `COPY INTO`, path relations (`FROM '/vol/landing'`), `LIST` |
| Pipelines | `CREATE`/`REFRESH STREAMING TABLE`, `CREATE MATERIALIZED VIEW`, `SCHEDULE CRON`, `APPLY CHANGES INTO`, `CREATE FLOW` |
| Unity Catalog objects | `CREATE CATALOG`/`VOLUME`/`CONNECTION`/`SHARE`/`RECIPIENT`, `EXTERNAL LOCATION`, `STORAGE CREDENTIAL`, `USE CATALOG` |
| Governance | `OWNER TO`, `SET`/`UNSET TAGS`, `ROW FILTER`, column `MASK`, `COMMENT ON COLUMN`, `DENY` |
| Maintenance | `PREDICTIVE OPTIMIZATION`, `SYNC`, `CACHE SELECT`, `CLUSTER BY AUTO` |
| Constraints | `ADD`/`DROP CONSTRAINT` with `CHECK`, `PRIMARY KEY`, `FOREIGN KEY` |
| Query | `QUALIFY` |
| Semi-structured | VARIANT colon paths (`payload:user.id`, `v:['key']`), `OBJECT<a: INT>` |

### One caveat on GRANT and REVOKE

Spark's grammar does not really parse `GRANT`/`REVOKE`. They fall into
`unsupportedHiveNativeCommands`, a catch-all whose body is `.*?` — it matches
the command name and then swallows arbitrary tokens. So they are *accepted*,
but nothing about them is validated, and a malformed `GRANT` will not be
caught. `DENY` has a real rule here because it had no catch-all to fall into.
Giving `GRANT`/`REVOKE` real rules is worthwhile if you want them linted;
it would not change what parses, only what gets checked.

Generation runs ANTLR with `-Werror` on purpose. ANTLR reports an undefined
token used in a parser rule as a *warning*, and the result is an alternative
that can never match — syntax we believe we support but silently do not. That
warning caught four such tokens while this was being written.

### Adding a keyword is the risky part

Defining a lexer token stops that word matching `IDENTIFIER`. Add `PATTERN` as
a keyword and `SELECT pattern FROM t` becomes a syntax error — a false positive
that blocks a merge request that was fine.

`keywords.txt` is therefore the single source of truth: each entry generates
the lexer token **and** entries in both `nonReserved` lists, so it is
structurally impossible to add a token and forget to keep it usable as an
identifier. `tests/test_databricks_gap.py` reads that same file and checks
every keyword still works as a column name, an alias, a table name, and in DDL,
in both keyword modes.

`GAPS` in that file is the backlog for anything still uncovered, written as
`xfail(strict=True)`: a gap stays visible while open, and the suite goes **red**
the moment someone closes one, forcing the entry into the supported list. The
inventory can only shrink deliberately.

Keeping up with Databricks as it ships features is the real ongoing cost of
this approach.

## Re-vendoring a newer Spark

```bash
make grammar SPARK_VERSION=v4.2.0     # needs Java 11+
make test
make corpus
```

The default is `v4.0.4`, the Spark release behind Databricks Runtime 17.x.
Java is a build-time dependency for maintainers only — the generated parser is
committed, so installing the tool needs nothing but `pip`.

## Roadmap

- [x] Vendored + patched grammar, generated Python parser
- [x] Notebook / widget preprocessing with position fidelity
- [x] Corpus harness: recall, plus mutation-based rejection scoring
- [x] Databricks syntax coverage
- [x] Local type resolution (CREATE TABLE declarations, explicit CASTs)
- [x] Configurable rule engine with TOML config
- [ ] pre-commit hook and CI recipes (GitHub Actions, GitLab CI)
- [ ] Language server, for in-editor diagnostics
- [ ] Autofix for the cases that are provably local

## License

Apache-2.0. See [LICENSE](LICENSE).

This project incorporates the ANTLR grammar from Apache Spark, also
Apache-2.0 licensed; the generated parser is a derivative work of it. See
[NOTICE](NOTICE) for full attribution.
