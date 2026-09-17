# Contributing

## Setup

```bash
make venv          # creates .venv and installs the package with dev extras
make test          # run the suite
```

Regenerating the parser needs Java 11+; using the tool does not. The generated
parser is committed so that `pip install` is all a user needs.

## Adding a lint rule

Rules live in `src/dbsqlparse/rules/` and see the semantic model in
`src/dbsqlparse/analysis.py`, never ANTLR contexts. Subclass `Rule`, set `id`
and `description`, list every option in `defaults`, implement `check`, and
decorate with `@register`. There is a worked example in the README.

Two things a rule must not do:

- **Ship a convention.** A rule may have structural defaults (a length limit,
  say) but must not presume what things should be called. Naming rules stay
  inert until a config supplies patterns.
- **Guess a type.** `ctx.analysis` gives a type only where the SQL states one.
  Skip columns where it is `None` rather than inferring.

## Adding Databricks syntax

Databricks-only syntax goes in `grammar/extensions/`, never into generated
output or the vendored grammar:

| file | purpose |
| --- | --- |
| `keywords.txt` | new keywords, one per line |
| `statements.g4frag` | alternatives spliced into the `statement` rule |
| `rules.g4frag` | supporting rules appended to the grammar |

Syntax that modifies an *existing* rule needs a small injection function in
`scripts/patch_grammar.py`, anchored on distinctive text, plus an entry in
`tests/test_patch_grammar.py` proving it fails loudly when that anchor moves.

Then:

```bash
make grammar       # re-vendor, patch, regenerate
make test
make corpus        # check for recall regression
```

**Adding a keyword is the risky part.** Defining a lexer token stops that word
matching `IDENTIFIER`, so `SELECT pattern FROM t` can stop parsing. Listing the
keyword in `keywords.txt` handles this automatically — it generates the token
*and* the `nonReserved` entries — and the suite checks every keyword still works
as a column name, alias and table name. Do not add tokens any other way.

## Before opening a PR

```bash
make test
make verify-generated   # committed parser matches the grammar
make corpus             # recall and rejection have not regressed
```

`make corpus` needs `make corpus-fetch` first, which downloads Spark's SQL test
files. Recall is the number that matters most: a drop means the linter would
start rejecting SQL that is actually valid, which blocks good pull requests.
