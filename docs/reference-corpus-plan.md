# Plan: growing the reference corpus

A work plan for extending `corpus/reference/` from 7 pages / 35 cases to
broad coverage of the Databricks SQL reference. Written 2026-09-19.

Read `AGENTS.md` first — specifically "The blind spot, and the reference
corpus". This file is the *how* and the *in what order*; that section is the
*why*, and it is not repeated here.

## What "great" means here

The scraped corpus samples **what people publish**. The reference corpus
samples **what the dialect allows**. A construct no published file uses is
invisible to recall and to mutation both, and that is the hole SQLFluff
#8509 fell through. The reference corpus is great when a defect of the #8509
shape — a bracketed optional production implemented as optional-as-a-whole,
with its interior left unbound — cannot merge without a case going red.

Three things follow from that, and they are the whole design:

1. **Every bracketed optional production in a syntax block gets a
   must-reject case for its partial forms.** This is the rule that would
   have caught #8509. It is not optional and it is not a nice-to-have; it is
   the reason the corpus exists.
2. **Every case cites the page and anchor it came from**, so a reviewer can
   check the transcription rather than trust it.
3. **A must-reject case only counts when its full-form sibling parses.**
   Otherwise the rejection may be for an unrelated reason. The harness calls
   this vacuous and reports it separately; see `sibling_parsed()`.

## Non-negotiables

These break the project if violated. They are not style preferences.

- **Never copy a doc example body.** Transcribe a *minimal skeleton of your
  own construction* from the syntax block. `SELECT * FROM STREAM s`, tables
  named `t`, columns named `a`/`b`/`c`. The doc examples are Databricks'
  copyrighted text; the syntax productions are facts about a grammar. This
  is what keeps `NOTICE` honest and the repo publishable.
- **No employer SQL, ever.** Not as a case, not as an example, not as
  inspiration for a case. Every case comes from the public reference.
- **Never invent syntax.** If the page does not show it, it does not go in.
  A hallucinated must-parse case becomes a false gap in `docs/gaps.md`,
  which becomes a bad upstream PR, which is exactly the failure mode this
  corpus was built to prevent. When unsure, leave the case out and note the
  uncertainty in the PR description.
- **Never edit `corpus/reports/baseline.json` by hand**, and never
  regenerate it from an editable fork install. `make baseline` refuses one
  on purpose.
- **Do not weaken the loader to make a case load.** If `reference.py`
  rejects your YAML, the YAML is wrong.

## The case schema

Enforced strictly by `_load_file` / `_load_case` in
`src/dbsqlparse/corpus/reference.py`. Unknown keys are errors.

File level — `statement`, `doc` and `cases` required; `syntax` optional but
**always write it**, because it is what a reviewer diffs the cases against:

```yaml
# A comment explaining why this page is interesting, if it is.
statement: DROP VIEW
doc: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-drop-view
syntax: DROP [ MATERIALIZED ] VIEW [ IF EXISTS ] view_name
cases:
  ...
```

Case level — `id`, `verdict`, `anchor` and `sql` required; `from` required
on every `must-reject` and forbidden on every `must-parse`:

```yaml
  - id: drop-view.materialized          # <file-stem-kebab>.<what-it-is>
    verdict: must-parse                 # or must-reject
    anchor: "#syntax"                   # the heading the production is under
    sql: |
      DROP MATERIALIZED VIEW mv
    note: |                             # optional; use it for anything a
      Why this case is here.            # reviewer would otherwise ask about

  - id: drop-view.materialized-without-view
    verdict: must-reject
    anchor: "#syntax"
    from: drop-view.materialized        # the full-form sibling
    omits: "VIEW"                       # the production text left out
    sql: |
      DROP MATERIALIZED mv
```

Every must-reject case also carries a `reason:` — `omission` (the default)
for a partial form, or `exclusive-alternative` for a statement that mixes
two alternatives the reference makes exclusive. An `exclusive-alternative`
case records both mixed alternatives in `conflicts: [ FIRST, SECOND ]`
instead of `omits:`, and each is checked against the `syntax:` block:

```yaml
  - id: grant.all-privileges-in-list
    verdict: must-reject
    anchor: "#syntax"
    from: grant.multiple-privileges
    reason: exclusive-alternative
    conflicts: [ "ALL PRIVILEGES", "privilege_type" ]
    sql: |
      GRANT ALL PRIVILEGES, SELECT ON TABLE t TO p
```

Conventions the loader does not enforce but that reviews should:

- **`omits:` on every omission**, quoting the production text verbatim
  from the `syntax:` block. It is what makes the case reviewable; the loader
  checks it against the block, and `conflicts:` the same way.
- **One file per reference page**, named after the statement in
  `snake_case.yml`; ids in `kebab-case` prefixed with the statement.
- **Ids are permanent.** `baseline.json` diffs case by case, so renaming an
  id reads as "case removed + case added", which `compare_baseline.py`
  scores as a regression. Pick the name once.

## The per-page workflow

Do one page at a time, start to finish. Do not open six pages and
half-transcribe them.

1. **Fetch the live page.** Resolve the URL from the language manual index
   (`https://docs.databricks.com/aws/en/sql/language-manual/`) rather than
   guessing a slug — the slugs are not predictable, and Lakeflow pages live
   under `/aws/en/ldp/developer/` instead. Record the exact URL in `doc:`.
2. **Copy the syntax block into `syntax:`** verbatim. This is the contract
   the rest of the file is derived from.
3. **Write the must-parse cases.** One per *alternative* in the production,
   plus one for each meaningfully different combination of optional clauses.
   Minimal skeletons, your own construction.
4. **Apply the bracket rule.** Walk the `syntax:` block left to right. For
   every `[ ... ]` containing more than one token, write a must-reject case
   for each partial form — the bracket with its interior half-supplied.
   Point `from:` at the full-form must-parse sibling and quote the missing
   text in `omits:`. Also cover: empty parenthesised lists where at least
   one item is required, clauses used without the keyword that gates them
   (the `PRIVATE`-without-`STREAMING` shape), and mixed exclusive
   alternatives (`{ A | B }` written as `A, B`), which use
   `reason: exclusive-alternative` and `conflicts:` instead of `omits:`.
5. **Run it:** `make reference PY=.venv-main/bin/python` for the worktree on
   `main`, or `make reference` for whatever the default venv holds. It needs
   no fetched corpus and takes seconds.
6. **Triage every disagreement.** This is the step that matters:
   - A **must-parse case that fails** means either your transcription is
     wrong or SQLFluff is. Assume yours first. Re-read the page. Only when
     you have confirmed the syntax on the live page does it become a gap —
     and then it goes in `docs/gaps.md` with the case id, the repro, and the
     doc quote that establishes it.
   - A **must-reject case that is accepted** is an over-acceptance finding —
     the #8509 shape. These are the valuable ones. Same treatment.
   - A **must-reject case reported vacuous** means its sibling does not
     parse, so the case proves nothing yet. That is fine and expected when
     the sibling is itself an open gap; leave it and it becomes informative
     when the gap closes.
7. **Commit the page on its own**, with the counts before and after in the
   message. One page per commit keeps the baseline diff readable.

After a batch of pages, regenerate the baseline from a **release** install
(`make baseline PY=.venv-release/bin/python`) and read the diff before
committing it. A newly added failing case is new coverage, not a regression;
`scripts/compare_baseline.py` already distinguishes the two.

## The page queue

Work top to bottom. Tier 1 is not the most interesting work; it is the work
that pays off soonest, because each of these pages pins a PR that is already
open or already planned.

### Tier 1 — pages backing work in flight

| page | why now |
| --- | --- |
| GRANT / REVOKE / SHOW GRANTS + the Unity Catalog **privileges reference** | Pins #8512 and #8516, and produces the case set for the *securable list* PR before that PR is written. The highest-value single page in the queue. |
| CREATE CATALOG | Pins #8511 (`MANAGED LOCATION`). |
| CREATE VIEW (incl. `LIVE` / `STREAMING LIVE`) | Pins #8513, which *removes* `OR REFRESH` — a must-reject case is the only durable guard. |
| EXECUTE IMMEDIATE | Pins #8515, including its six rejection boundaries. |
| CONVERT TO DELTA | Pins #8517. |
| CREATE VOLUME | Completes the volume story started in #8512. |

Doing these first means that when the review queue drains and it is time to
open the securable-list PR, the reference cases already exist and the PR
arrives with its evidence attached instead of assembled afterwards.

### Tier 1.5 — semi-structured types: VARIANT, STRUCT, JSON, XML

Added 2026-09-19. This tier jumped the queue because it is load-bearing for
the Databricks work the corpus exists to support, and because it currently
has **zero** reference coverage: no case in `corpus/reference/` mentions
VARIANT, STRUCT, ARRAY, MAP, JSON or XML, and `docs/reference-coverage.md`
marks the data-types pages `n/a` on the grounds that types are "already
covered through the table statements". That reasoning holds for `INT` and
`STRING`. It does not hold here, for three reasons: the complex types have
their own bracketed generic grammar with its own partial forms; VARIANT
access (`v:field`, `v:['k']`, `::` casts) is *expression* grammar that no
statement page covers; and nested generics are a classic parser failure
(`STRUCT<a: ARRAY<STRUCT<b: INT>>>` ends in `>>>`, which a naive lexer reads
as shift operators).

**Read this before writing cases: the support is already good.** Probed
against `main` at `33d8c8459` with a known-bad control in the batch, all of
the following already parse — `VARIANT` columns and casts, `parse_json`,
`v:field`, `v:field.sub`, `v:['key']`, `v:field::STRING`, `a::INT`,
`STRUCT<a: INT, b: STRING>`, `ARRAY<INT>`, `MAP<STRING, INT>`, four-deep
nesting ending in `>>>>`, `struct()`, `named_struct()`, `from_json`,
`to_json`, `schema_of_json`, `get_json_object`, `json_tuple`, `xpath`,
`from_xml`, `schema_of_xml`, `variant_get`, `try_variant_get`,
`is_variant_null`. The rejection side is in good shape too: `STRUCT<>`,
`STRUCT<a>`, `STRUCT<a: INT,>`, `ARRAY<>`, `ARRAY<INT, INT>`, `MAP<STRING>`,
`MAP<STRING, INT, INT>`, `VARIANT<a: INT>`, `SELECT v:` and `SELECT v:[]`
are all correctly rejected.

So this tier is **mostly regression-pinning, not gap-hunting**, and that
changes how to write it. The point is not to find bugs today; it is to make
sure a future rewrite cannot silently drop this surface the way #7405 dropped
LIVE / STREAMING LIVE views from `CreateViewStatementSegment`. Write the cases
as the permanent record of behaviour that is currently correct.

**Two real gaps were found, both needing doc verification before they are
claimed.** Verify each against the live page first — the transcription is
wrong more often than the parser is:

- **`STRUCT<a: INT NOT NULL>` is rejected.** The data-types page gives the
  production as `STRUCT < [fieldName : fieldType [NOT NULL][COMMENT str][, …]] >`,
  so `NOT NULL` is documented per field. `COMMENT` works
  (`STRUCT<a: INT COMMENT 'c'>` parses); `NOT NULL` does not, alone or
  combined. This is a small, high-confidence, well-bounded fix — a good
  candidate for the next upstream PR once the review queue drains.
- **Bare `OBJECT` as a column type is rejected**, while `CAST(v AS OBJECT)`
  is accepted — an internal inconsistency. `OBJECT` is documented as a type
  ("values in a VARIANT with the structure described by a set of fields"),
  but with no parameterised syntax and marked unsupported across all the
  language mappings. Treat this one as genuinely uncertain: establish what
  the reference actually promises before filing anything, and if it stays
  ambiguous, leave it out. Nothing unshown goes in.

A third, `STRUCT<>`, is ambiguous by construction: the page brackets the
whole field list, which *could* mean an empty struct is legal. Do not write
a case in either direction without evidence beyond the brackets.

**Pages for this tier**, in order:

| page | what it pins |
| --- | --- |
| Data types | `STRUCT` / `ARRAY` / `MAP` / `VARIANT` / `OBJECT` productions and their partial forms. The anchor page for the tier. |
| JSON path expression (already `queued`) | `v:field`, `v:['k']`, wildcards, the access grammar VARIANT depends on |
| SQL expression (already `queued`) | `::` cast, field access, subscripting |
| LATERAL VIEW clause (already `queued`) | `explode` / `inline` over ARRAY and MAP columns |
| `read_files` / `from_json` / `from_xml` signatures | the JSON and XML ingestion surface, to the extent the reference gives productions rather than function prose |

When this tier is done, flip the data-types rows in
`docs/reference-coverage.md` from `n/a` to `done` and correct the legend —
the current wording ("type/format reference already covered through the table
statements") is the assumption this tier disproves.

### Tier 2 — dense optional productions

This is where the bracket rule earns the most, because these pages are
mostly brackets. Expect gaps.

CREATE TABLE (`USING` / `LIKE` / `CLONE` / partitioning / `TBLPROPERTIES`),
ALTER TABLE, CREATE SCHEMA, CREATE FUNCTION (SQL and Python),
MERGE INTO, COPY INTO, OPTIMIZE (incl. `ZORDER BY`), VACUUM,
CREATE CONNECTION, CREATE EXTERNAL LOCATION, CREATE SHARE / CREATE RECIPIENT.

### Tier 3 — query and DML clauses

SELECT (`QUALIFY`, `LATERAL VIEW`, `PIVOT` / `UNPIVOT`, `TABLESAMPLE`,
hints), window functions, common table expressions, set operators, `VALUES`,
INSERT (`INSERT INTO` / `OVERWRITE` / `BY NAME` / `REPLACE WHERE`),
UPDATE, DELETE.

### Tier 4 — the long tail

SET / RESET, USE, the `SHOW *` family, ANALYZE TABLE, CACHE / UNCACHE,
REFRESH, RESTORE, time travel (`VERSION AS OF` / `TIMESTAMP AS OF`),
identity columns, table constraints, column masks and row filters.

Stop when new pages stop finding anything. Coverage of the manual is not the
goal; coverage of *bracketed optional productions* is.

## Harness improvements worth making

These make the corpus better as an instrument, not just bigger. Roughly in
value order. All six landed with the Tier 1 batch; item 1 was widened after
review into the `reason:` / `omits:` / `conflicts:` model above, because
`omits:` was being stretched to cover a case that omits nothing.

1. **Require `omits:` on must-reject cases**, in `_load_case`. It is the
   field that makes a case reviewable. One `if` and a test.
2. **Check that `omits:` is a substring of the file's `syntax:` block.** A
   cheap mechanical proof that the omission is real and not invented —
   catches a whole class of transcription error automatically. Requires
   making `syntax:` mandatory, which it should be anyway. Normalise
   whitespace before comparing.
3. **Track page coverage.** A `docs/reference-coverage.md` listing every
   page in the language manual with a status (`done` / `queued` / `n/a`),
   so "what is left" is a file rather than a memory. Generate the initial
   list from the manual index once, by hand.
4. **Add a `checked:` date per file.** Databricks revises these pages. A
   transcription verified in September 2026 is a claim about the page as it
   was that day, and there is currently no way to tell a stale file from a
   fresh one.
5. **`make reference-gaps`** — print only the failing and non-vacuous cases,
   in the shape a `docs/gaps.md` entry wants. The triage step in the
   workflow above is currently manual copying.
6. **Report vacuity as a trend.** The count of vacuous must-reject cases
   should fall as gaps close. It is the corpus's own health metric and
   nothing currently watches it.

Keep `reference.py` at 100% line and branch coverage — `make test` enforces
it, and every change above needs its test in the same commit.

## Definition of done, per batch

A batch of pages is finished when all of these hold:

- `make reference` runs clean, controls ok, and the counts are recorded in
  the commit message.
- `make test` passes, with `reference.py` still at 100% line and branch
  coverage.
- Every new must-parse case that SQLFluff rejects has been **re-verified
  against the live page** and either fixed or filed in `docs/gaps.md` with
  its case id.
- Every new must-reject case carries `from:` and, according to its `reason:`,
  either an `omits:` or a `conflicts:` that quotes the `syntax:` block.
- No case contains a body copied from a doc example.
- `baseline.json` regenerated from a release install, diff read, and the
  new-coverage-versus-regression split stated in the commit message.

## What not to do

- **Do not open upstream pull requests from this work without checking
  first.** There are already nine in flight from one contributor against one
  reviewing maintainer, and three of those are stuck as drafts behind an
  account-level throttle. Finding a gap and *recording* it is the
  deliverable here; converting it to a PR is a separate decision with its
  own timing.
- **Do not add cases for constructs SQLFluff already handles just to raise
  the count.** A case that has never been red and never will be is noise in
  the baseline diff. Cases exist to catch something.

  **The exception is deliberate regression-pinning on a high-value surface.**
  #7405 rewrote `CreateViewStatementSegment` from scratch and silently lost
  LIVE / STREAMING LIVE views; nothing caught it for months. A green case over
  a construct that matters is worth its place when it is guarding against that
  — a rewrite quietly dropping support — rather than padding a count. Say so
  in the file's header comment when that is the reason, so the next reader can
  tell the two apart. Tier 1.5 is written under this exception.
- **Do not batch ten pages into one commit.** The baseline diff is the
  review surface; make it readable.
- **Do not fix SQLFluff and the corpus in the same change.** The corpus is
  the oracle; an oracle edited in the same breath as the thing it measures
  is not an oracle.
