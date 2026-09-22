## Summary

Adds the Databricks ingestion and flow surface:

- **`INSERT WITH SCHEMA EVOLUTION`** and the **`REPLACE ON`** alternative,
  including the parenthesised query source, which a general expression grammar
  mis-reads as a function call
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-dml-insert-into)).
- **`RESTORE [TABLE] <target> [TO] { TIMESTAMP AS OF | VERSION AS OF }`**,
  with the table name and `TO` optional and an arithmetic timestamp expression
  ([docs](https://docs.databricks.com/aws/en/sql/language-manual/delta-restore)).
- **Inline `FLOW`** on a pipeline `CREATE TABLE`, and on a `STREAMING` table
  ([docs](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-table-flow)).
- Bind **`REPLACE USING (...)` and `SEQUENCE BY` together** in the append-flow
  spec, so a standalone `CREATE FLOW` rejects either half on its own. This is
  the over-acceptance [#8509](https://github.com/sqlfluff/sqlfluff/pull/8509)
  shipped: it took `REPLACE USING (...)` without the required `SEQUENCE BY`,
  and rejected the documented pair
  ([docs](https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow)).

Adds fixtures for each and rejection cases for the partial forms a valid-parse
fixture cannot express.

## Note on scope

The inline-`FLOW` machinery overlaps the open draft
[#8520](https://github.com/sqlfluff/sqlfluff/pull/8520) (inline `FLOW` on a
streaming table). They are the same statement family and share the `FLOW`
clause, so whichever lands second should drop the overlap; this branch carries
both the streaming and the plain pipeline form so it is measurable on its own.

## Tests

- `python -m pytest test/dialects/ test/core/parser/parity/ -q -n auto`
  — **9417 passed, 2 xfailed**
- reference conformance: **504 → 518 must-parse (+14)** and the #8509
  over-acceptance now caught (`create-flow.replace-using-without-sequence-by`),
  **0 regressions**
- corpus holds at **542/562** valid, rejection **100%** (1327/1327)

Prepared with an AI coding assistant.
