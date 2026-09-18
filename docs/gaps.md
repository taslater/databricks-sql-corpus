# SQLFluff Databricks gap queue

The upstream work queue. Every entry is a construct that appears in published
Databricks SQL and that SQLFluff's `databricks` dialect cannot parse, with a
minimal reproduction verified against SQLFluff `main`.

This file replaces the `GAPS` inventory that lived in
`tests/test_databricks_gap.py`, which tracked gaps in this project's own
retired parser. Of the twelve gaps that inventory still held when the parser
was retired, **ten were already supported by SQLFluff** — which is the
clearest single argument for having retired it. The two that were not are
recorded below.

## Open

| construct | repro | corpus files |
| --- | --- | ---: |
| `EXECUTE IMMEDIATE … USING` | `EXECUTE IMMEDIATE s USING (a AS b);` | 1 |
| `DESCRIBE HISTORY` as a relation | `SELECT * FROM (DESCRIBE HISTORY t);` | 2 |
| `DESCRIBE DETAIL` as a relation | `SELECT * FROM (DESCRIBE DETAIL t);` | 1 |
| `SHOW GRANTS ON <object>` | `SHOW GRANTS ON demo.schema.names;` | 1 |
| `CREATE TEMPORARY STREAMING LIVE VIEW` | `CREATE TEMPORARY STREAMING LIVE VIEW v AS SELECT 1;` | 1 |
| `CREATE CATALOG … MANAGED LOCATION` | `CREATE CATALOG c MANAGED LOCATION 's3://x';` | 1 |
| `GRANT READ VOLUME ON VOLUME` | ``GRANT READ VOLUME ON VOLUME c.s.w TO `grp`;`` | 1 |
| `-- MAGIC` body line starting with `%` | the `magic_line` matcher is `(-- MAGIC)( [^%]{1})([^\n]*)`, which excludes `%` | 1 |
| `DOUBLE PRECISION` | `CREATE TABLE t (x DOUBLE PRECISION);` | 0 |
| `CONVERT TO DELTA … NO STATISTICS` | `CONVERT TO DELTA t NO STATISTICS;` | 0 |

The last two have no corpus file: they came from the retired inventory, so
they are real syntax but not yet observed in the wild. Lower priority.

## Templating, not dialect

Four corpus files fail on parameter syntax rather than grammar. SQLFluff's
`placeholder` templater with `param_style = dollar` already handles `${name}`
and `$name`, declared or not. It does **not** handle:

| shape | example |
| --- | --- |
| dotted | `${test.nrows}` |
| dashboard | `{{ station_list }}` |
| empty | `${}` |

`src/dbsqlparse/preprocess.py` is the reference implementation for all three
and is kept for that reason. The fix upstream is widening the `dollar` regex
in `src/sqlfluff/core/templaters/placeholder.py`, or adding a `databricks`
param style.

## Not gaps

Recorded so they are not re-investigated:

- `PipelineSetting.json.sql` — JSON with a `.sql` extension.
- `create_raw_tags.sql` — Lakebase (Databricks **PostgreSQL**), not Databricks
  SQL. `TEXT PRIMARY KEY`, `DOUBLE PRECISION`.

## Landed

Open pull requests against `sqlfluff/sqlfluff`:

| PR | construct |
| --- | --- |
| [#8507](https://github.com/sqlfluff/sqlfluff/pull/8507) | magic cell body after a single-line directive |
| [#8508](https://github.com/sqlfluff/sqlfluff/pull/8508) | materialized view declaring only expectations |
| [#8509](https://github.com/sqlfluff/sqlfluff/pull/8509) | `PRIVATE` streaming tables, `CREATE FLOW` append flows (closes #8455) |
| [#8510](https://github.com/sqlfluff/sqlfluff/pull/8510) | `DESC HISTORY` / `DESC DETAIL` |

## Unverified divergences

Behaviour where SQLFluff differs from Apache Spark, but the Databricks and
Spark documentation does not settle which is right. Recorded rather than
filed, so they are not re-investigated from scratch.

| form | Spark / the retired parser | SQLFluff |
| --- | --- | --- |
| `SET spark.sql.foo =` (empty value) | accepted | rejected |

Spark's reference gives `SET property_key[ = property_value ]`, which reads as
either `SET key` or `SET key = value` and says nothing about an empty value.
The corpus contains no instance either way. `corpus/mutate.py` keeps its
`_in_set_statement` guard regardless, because skipping a mutation is the safe
direction.
