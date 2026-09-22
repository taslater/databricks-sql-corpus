## What

Adds a `databricks` style to the placeholder templater for notebook widget and
dashboard parameters:

```sql
SELECT * FROM ${catalog}.${schema}.t;   -- dotted widget name
SELECT * FROM {{ station_list }};        -- dashboard parameter
SELECT * FROM t WHERE d = '${}';         -- anonymous widget
SELECT * FROM ${name};                   -- bare widget
```

The existing styles cover `${name}`-style parameters but not the dotted
Databricks form, the `{{ … }}` dashboard form, or the empty widget `${}`. The
new style recognises all four token shapes.

The change also fixes a latent bug the new style exposes: the templater
assumed every style matched a `param_name` group, so a match with no group at
all (or, here, an empty `${}` where the group matched the empty string) raised
`KeyError`/produced a `None` name. Both now fall back to the existing 1-based
parameter index, which is the behaviour a style without names already relies
on.

## Tests

- `test/core/templaters/placeholder_test.py`: the four parameter shapes, plus a
  style-with-no-name case covering the index fallback.
- The four corpus files that use these forms now parse; `dbx-dlt-notebooks`
  goes 18/19 → 19/19, with zero regressions elsewhere.
- Templater suite **239 passed**; corpus mutation stays **100%**.

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
