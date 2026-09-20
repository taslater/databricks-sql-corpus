# sqlglot: the advisory second parser

Added 2026-09-19. sqlglot is pinned to an exact version in the `dev` extra
(`pyproject.toml`), because reports record the version and it moves fast.

## Why, and the one rule that governs everything

`make gaps` says what SQLFluff cannot parse. `make diff` adds sqlglot -- an
independent implementation of a Databricks dialect, and the parser Databricks
Labs UCX itself uses -- and reports where the two disagree. A disagreement is
useful precisely because the implementations are independent: sqruff is a port
of SQLFluff, so its disagreements measure port lag, while sqlglot is a second
opinion.

**The rule: advisory only.** Nothing from `make diff` feeds `recall`,
`rejection`, `baseline.json` or `compare_baseline.py`. The docs-derived
reference corpus is the oracle; a second parser is a witness. Two behaviours
make this non-negotiable:

  * **Leniency.** sqlglot documents itself as "a transpiler, not a validator"
    and is deliberately lenient: it accepts `SELECT a,, b FROM t`, one of
    `mutate.py`'s GUARANTEED-invalid shapes. Its *rejections* are the signal;
    its *acceptances* are not.
  * **Command fallback.** For syntax it does not model, sqlglot logs a warning
    and returns the whole statement as an opaque `Command` node -- `CREATE
    CATALOG c`, `CREATE FLOW ...`, `OPTIMIZE t` and `VACUUM t` all land there.
    That is acceptance without understanding, so `SqlglotRunner` counts a
    top-level `Command` as failure and quietens the logger. Without this,
    SQLFluff's over-acceptances would be masked by sqlglot agreeing with them
    for the wrong reason.

The known-bad control (`SELECT a FROM ((t;`) runs in every batch, for every
parser. `make diff` exits non-zero only when a control misbehaves, because that
is the one failure that makes the whole report untrustworthy.

## What exists

| piece | where | what |
| --- | --- | --- |
| `SqlglotRunner` | `src/dbsqlparse/corpus/runners.py` | `read="databricks"`, strict error level, expression-`.errors` check, `Command` fallback as failure |
| `make diff` | `cli.py` `diff`, `differential.py` | joins both parsers over the corpus and the reference |
| `--runner sqlglot` | `cli.py` | standalone measurement; `all` runs sqlfluff+sqruff+sqlglot |
| fixture probe | `scripts/probe_sqlglot_fixtures.py` | AST-extracts SQL from sqlglot's dialect tests for discovery |
| pins | `pyproject.toml` | `sqlglot==30.18.0` in `dev`; `.venv-main` also carries it |

`make diff PY=.venv-main/bin/python` is the form to use for main-based numbers.
The default `.venv` measures whichever branch the fork checkout is on, which on
2026-09-19 was `fix/sparksql-struct-field-not-null` -- a run there correctly
showed three struct gaps missing from the "rank first" list. Check the branch
first, as the workspace AGENTS.md already says for other measurements.

## Reading the output

Corpus files, where at least one parser fails:

| category | meaning | action |
| --- | --- | --- |
| `sqlfluff-only` | only SQLFluff rejects; sqlglot parses | candidate SQLFluff gap, rank first |
| `sqlglot-only` | only sqlglot rejects | candidate gap in sqlglot (or non-SQL) |
| `both-fail` | neither parses | de-prioritised; likely unsupported by both |

Reference cases, joined by case id:

| category | meaning |
| --- | --- |
| `primary-gap` | documented syntax SQLFluff rejects that sqlglot parses -- rank first |
| `over-acceptance` | SQLFluff accepts a non-conforming form that sqlglot rejects; flagged `vacuous` when sqlglot cannot parse the full-form sibling either |
| `second-gap` | documented syntax sqlglot rejects that SQLFluff parses -- the sqlglot queue seed |
| `both-gap` | neither parses; expected while a whole statement is an open PR |
| `both-accept` | the reference disallows what both accept -- a transcription question |
| `second-lenient` | sqlglot accepts what SQLFluff rejects -- expected, no action |

## First run: 2026-09-19

SQLFluff `main` at `33d8c8459` (`.venv-main`) vs sqlglot 30.18.0, controls ok.

```
corpus:    866 files compared -- 52 sqlfluff-only, 198 sqlglot-only,
           56 both-fail, 560 agreed
reference: 8 primary-gap, 22 second-gap, 58 both-gap,
           1 over-acceptance (vacuous), 1 both-accept
```

The 8 primary gaps are exactly the live queue, which is the cross-validation
this was added for: `create-view.using-data-source-without-options`;
`drop-view.materialized` and `drop-view.materialized-if-exists` (#8519);
`json-path.star` and `json-path.delimited-identifier`; `struct.not-null`,
`struct.not-null-with-comment` and `struct.collate` (the branch above).

The 22 second gaps are the first sqlglot queue candidates: `CREATE CATALOG`
and its clauses, `CREATE FLOW`, `PRIVATE` streaming tables, `CREATE VOLUME`,
`DESCRIBE DETAIL`, and the JSON-path family SQLFluff also lacks. The one
over-acceptance, `create-flow.replace-using-without-sequence-by`, is flagged
vacuous because sqlglot Command-falls-back on the full form -- a second parser
can only certify a rejection when it can parse the thing being specialised.

## The fixture probe

`scripts/probe_sqlglot_fixtures.py` AST-extracts the SQL strings from sqlglot's
pinned dialect tests (not regex -- the helpers differ), runs SQLFluff over
them, and prints rejects not already in the queue. v30.18.0: 391 strings, 41
rejected, 38 distinct constructs, 36 not already queued. Discovery only: a
fixture is a candidate, the reference decides.

Two are verified against `main` and the reserved-words page and queued in
`docs/gaps.md`:

  * `DESCRIBE history.tbl` -- collides with the `DESCRIBE HISTORY` statement
    prefix; `DESCRIBE TABLE history.tbl` parses.
  * `SELECT * FROM stream` -- a table named `stream` needs backticks even
    though Databricks reserves no such word.

The rest, grouped for a later triage pass (all fail on `main` at
`33d8c8459`, none read against the docs yet):

| group | shapes |
| --- | --- |
| scripting | `DECLARE VAR x INT`, `DECLARE a, b, c INT DEFAULT 1` |
| collation in nested types | `ARRAY<STRING COLLATE ...>`, `MAP<..., STRING COLLATE ...>` (`struct.collate` already queued) |
| DESCRIBE | `DESCRIBE EXTENDED t AS JSON`, `history.*` above |
| constraints | `PRIMARY KEY (a, ts TIMESERIES)`, `UNIQUE (a)` |
| functions | `CREATE FUNCTION a AS b`, `HANDLER`, `PARAMETER STYLE` |
| COPY INTO | `FILEFORMAT = ... VALIDATE = ALL FILES = (...) FORMAT_OPTIONS ... COPY_OPTIONS ...` |
| TRUNCATE | `PARTITION(age = 10, city LIKE 'LA')` |
| JSON path | `x:['a']['b']`, `x:y[*].z`, `get_json_object(x:y[*], ...)`, `raw:`full name``, `raw:['a']` (star and delimited already queued) |
| ANALYZE | `COMPUTE DELTA STATISTICS [FOR ALL COLUMNS | FOR COLUMNS a, b]` |
| namespaces | `CREATE NAMESPACE`, `DROP NAMESPACE` (Spark; Databricks uses schemas) |
| tables | `ICEBERG TBLPROPERTIES`, `CHANGE COLUMN`, `STRUCT<a: VARCHAR(50)>` |
| templating | `FROM {x}` (Spark SQL braces, not Databricks -- likely a skip) |

## Valid-variant probes (Phase 4)

`scripts/fuzz_variants.py` generates SQL that must parse and reports where it
does not. Both modes assert their own controls. Run 2026-09-19 against `main`
at `33d8c8459`:

  * `keywords` -- 1017 dialect keywords substituted into column, alias, table
    and DDL-name positions: 31 rejected somewhere, 74 shapes. Most are
    genuinely structural (`AND`, `FROM`, `AS`, `JOIN`), but two groups were
    real, and this probe is what found them:
      - `LEFT`/`RIGHT` are globally reserved in `databricks` although #8050
        removed them from `sparksql`; a lost-inheritance regression, queued in
        `docs/gaps.md` with the two-line fix location.
      - `KEYS`, `PIVOT` and `WINDOW` are rejected as unquoted column aliases;
        queued.
  * `roundtrip` -- 344 files regenerated by sqlglot and re-parsed by SQLFluff:
    12 rejected, 11 constructs. Most were generator artifacts (sqlglot moving
    `IGNORE NULLS` outside the call, rewriting `CLEAR CACHE`) or already-known
    families (templating, JSON paths, Lakebase). One real, unclaimed find:
    parenthesised set-operation operands, queued.

The duplicate check that preceded queueing is now part of the process: the
first two candidates were already claimed upstream -- #8050 merged for
`sparksql` only, and #8523 open for `EXCEPT DISTINCT` -- which turned the first
into a databricks regression rather than a duplicate and removed the second
from the queue. Check upstream before writing anything up.

## Non-goals

  * No sqlglot lint rules; lint stays SQLFluff.
  * No sqlglot on the CI path.
  * No differential number in the baseline while its meaning is still settling;
    revisit only if a stable metric is ever wanted, in its own section.
  * The plugin semantic spike (`qualify`/`lineage`) is deferred entirely.

## Next

1. Triage the 22 second-gap cases into `docs/sqlglot-queue.md` and open PRs
   against sqlglot for the broadly useful ones (parser-level, engine-real).
   The queue's priority-1 candidate is `DESCRIBE DETAIL`.
2. Read the docs for the remaining probe candidates and transcribe the
   confirmed ones into `corpus/reference/`. The array-sort lambda case and the
   set-operator cases are done; the grouped table above is what remains.
3. Re-run `make diff` after SQLFluff merges to watch `primary-gap` and
   `both-gap` fall together.
