# AGENTS

Guidance for AI coding agents working in this repo. Read this before changing
anything under `grammar/`, `scripts/`, or `src/dbsqlparse/generated/`.

## What this is

`databricks-sql-parser` (`dbsqlparse`) is a static parser and configurable
linter for Databricks SQL, built on Apache Spark's own ANTLR grammar. It runs
entirely locally — no workspace connection, no catalog metadata, no network at
run time. Apache-2.0; the vendored Spark grammar is attributed in `NOTICE`.

## Build and test commands

```bash
make venv              # create .venv, install package with dev extras
make test              # pytest -q
make grammar           # re-vendor + patch + regenerate parser (needs Java 11+)
make verify-generated  # committed parser matches the grammar it came from
make corpus-fetch      # download Spark's SQL test corpus (once)
make corpus            # measure recall + mutation rejection
make clean
```

`SPARK_VERSION` defaults to `v4.0.4` (the Spark release behind DBR 17.x).
The venv Python is `.venv/bin/python`; the Makefile uses it directly, so run
`make venv` before anything else.

Before claiming a change is done: `make test`, then `make verify-generated`
if you touched the grammar, then `make corpus` if you touched the parser.

## Layout

```
grammar/vendor/        pristine Spark SqlBase{Lexer,Parser}.g4 — NEVER hand-edit
grammar/extensions/    Databricks-only syntax (keywords.txt, *.g4frag)
grammar/databricks/    patched output — generated, NEVER hand-edit
scripts/fetch_grammar.py     downloads a Spark tag into grammar/vendor/
scripts/patch_grammar.py     Java→Python rewrites + extension injection
scripts/generate_parser.sh   runs ANTLR (fetches the jar into tools/)
src/dbsqlparse/generated/    ANTLR output, committed — NEVER hand-edit
src/dbsqlparse/parser.py     parse API, statement splitting, two-stage parsing
src/dbsqlparse/preprocess.py notebook cells + widget substitution
src/dbsqlparse/analysis.py   parse tree -> small semantic model
src/dbsqlparse/rules/        rule framework, registry, TOML config, the rules
src/dbsqlparse/linter.py     runs configured rules over SQL
src/dbsqlparse/cli.py        `dbsqlparse` entry point
src/dbsqlparse/corpus/       accuracy harness (fetch, mutate, score)
examples/                    complete configs, two deliberately contradictory
docs/design-notes.md         why the non-obvious decisions were made
```

Three directories are generated output. Editing them is always the wrong fix —
change the input and regenerate:

| generated | change this instead |
| --- | --- |
| `grammar/vendor/` | bump `SPARK_VERSION`, run `make grammar` |
| `grammar/databricks/` | `grammar/extensions/` or `scripts/patch_grammar.py` |
| `src/dbsqlparse/generated/` | the grammar, then `make grammar` |

## The non-obvious constraints

These are the things that are easy to break without noticing. Each exists for
a reason recorded in the module docstring — read it before changing the code.

**Every patch rewrite is anchored with an expected occurrence count.** Spark's
grammar carries Java `@members` blocks and inline actions that ANTLR copies
verbatim; under the Python target they produce a file that will not import.
`scripts/patch_grammar.py` strips them by exact-string substitution and asserts
how many times each matched, so re-vendoring a newer Spark *fails loudly*
rather than emitting a silently broken parser. Do not loosen an anchor to make
a patch apply. If an anchor stops matching, that is upstream drift to port,
not noise to suppress. Every injection needs a matching entry in
`tests/test_patch_grammar.py` proving it fails when the anchor moves.

**Case folding happens in `LA()` only.** Spark declares keywords as uppercase
literals and gets case-insensitivity from a Scala stream wrapper that is not in
the `.g4`. `UpperCaseInputStream` (in `parser.py`) folds case for the lexer DFA
while leaving token text alone — the naming rules read those identifiers, so
folding the buffer would break them.

**Adding a keyword is the risky part.** Defining a lexer token stops that word
matching `IDENTIFIER`: add `PATTERN` and `SELECT pattern FROM t` becomes a
syntax error — a false positive that blocks a good merge request.
`grammar/extensions/keywords.txt` is the single source of truth; one entry
generates the lexer token *and* both `nonReserved` entries. Never add a token
any other way. `tests/test_databricks_gap.py` checks every keyword still works
as a column name, alias, table name and in DDL, in both keyword modes.

**Generation runs ANTLR with `-Werror` deliberately.** ANTLR reports an
undefined token in a parser rule as a warning, and the result is an alternative
that can never match — syntax we believe we support but silently do not.

**Parsing is two-stage: SLL, then full LL only on failure.** ALL(*) prediction
on this grammar is too slow to run on save. SLL can report a spurious error, so
nothing is believed until LL confirms it.

**Statement splitting uses the lexer, not a regex** — splitting on `;` with a
regex breaks inside string literals and comments.

**Preprocessing preserves positions.** `preprocess.py` splits notebook source
on `-- COMMAND ----------`, skips `-- MAGIC` cells, and replaces `${env}`
widgets with a *same-length* identifier so every diagnostic line/column still
points at the right place in the original file. Any new substitution must
preserve length.

## Product rules that are not negotiable

**This project ships no naming conventions.** Every rule is off until turned
on, and the naming rules do nothing until a config supplies patterns. A rule
may have structural defaults (a length limit) but must not presume what things
should be called. A linter that invents opinions on first run gets uninstalled.

**Never guess a type.** `type-naming` fires only where the file itself states a
type — a `CREATE TABLE` column declaration or an explicit `CAST(x AS BOOLEAN)
AS flag`. `CAST(a AS INT) + 1` is an addition, not a cast. Where the type is
`None`, skip the column silently. Reporting on a guessed type is worse than
staying quiet.

**Unknown config is an error, not a no-op.** Every option a rule accepts must
appear in `defaults`; unknown rule names and options are rejected at load with
a message listing what is valid.

**Exit codes are a contract**: `0` clean or warnings only, `1` at least one
error, `2` the tool could not run. A broken config must not look like a SQL
problem.

**Rules see `Analysis`, never ANTLR contexts.** That boundary is why a rule
author needs no knowledge of Spark's grammar, and why an upstream rule rename
breaks one file instead of every rule. Keep tree-walking in `analysis.py`.

## Adding a lint rule

Subclass `Rule` in `src/dbsqlparse/rules/`, set `id` and `description`, list
every option in `defaults`, implement `check`, decorate with `@register`.
Worked example in the README. Add cases to `tests/test_rules.py`.

## Adding Databricks syntax

New syntax goes in `grammar/extensions/`:

| file | what it adds |
| --- | --- |
| `keywords.txt` | new keywords, one per line |
| `statements.g4frag` | alternatives spliced into the `statement` rule |
| `rules.g4frag` | supporting rules appended to the grammar |

Syntax that modifies an *existing* rule needs an injection function in
`scripts/patch_grammar.py`, anchored on distinctive text, plus a test in
`tests/test_patch_grammar.py`. Then `make grammar && make test && make corpus`.

`GAPS` in `tests/test_databricks_gap.py` is the uncovered-syntax backlog,
written as `xfail(strict=True)`: a gap stays visible while open, and the suite
goes **red** the moment someone closes one, forcing the entry into the
supported list. Do not relax that strictness — the inventory is meant to shrink
only deliberately.

Known limitation to preserve as-is unless asked: `GRANT`/`REVOKE` fall into
Spark's `unsupportedHiveNativeCommands` catch-all (`.*?`), so they are accepted
but not validated. `DENY` has a real rule because it had no catch-all.

## Accuracy: two numbers that mean different things

| metric | what a miss means |
| --- | --- |
| **recall** — valid SQL we accept | false positive: CI blocks a good merge request |
| **rejection** — invalid SQL we catch | false negative: broken SQL sails through review |

Recall matters most. The harness mutates valid statements into invalid ones,
because a corpus of only-valid SQL cannot distinguish a good parser from one
that accepts everything. Only `guaranteed` mutations are scored; `weak` ones
(deleting a comma or `FROM`) are reported but never scored, because Spark's
default keyword mode legitimately re-parses them as valid
(`SELECT a b FROM t` — `b` aliases `a`).

`corpus/reports/baseline.json` is committed so accuracy regressions show up in
diffs; `corpus/cache/` is not, since every source is pinned to an exact
revision and the cache is reproducible from `sources.py` alone.

Current baseline: 100% on the TPC-DS/TPC-H/SSB suites, on
`dbx-dlt-notebooks` and on `dbx-descomplicando-sql`; 87% on
`dbx-learn-databricks`, 80% on `dbx-devrel`, 60% on `dbx-packt-cookbook`, ~94%
on `spark-sql-tests` (a mixed valid/invalid source). 100% rejection on 1320
guaranteed mutations.

The `dbx-*` shortfalls are the 11 entries in `GAPS` (widget DDL, `@v0` time
travel, `MANAGED LOCATION`, `STREAMING LIVE VIEW`, column-level tags and the
rest), plus two files that are not SQL at all.

Do not regenerate the baseline to make a regression disappear — investigate the
diff first. Adding a source that exposes a gap is not a regression, and
`scripts/compare_baseline.py` is written to tell the two apart.

## Conventions

- Python ≥ 3.10, `from __future__ import annotations` everywhere, fully
  annotated (`py.typed` is shipped), dataclasses for value types.
- Only runtime dependency is `antlr4-python3-runtime==4.13.2` (pinned to the
  ANTLR tool version). Do not add dependencies casually — "nothing but pip" is
  a feature.
- Module docstrings carry the *why*, not a summary of the code. Match that:
  comments explain reasoning and trade-offs, not mechanics.
- Prose in docs and comments uses British spelling in places (`normalised`,
  `tokenise`) — match the surrounding file.
- Java is a maintainer-only build dependency. Nothing at run time may need it.

