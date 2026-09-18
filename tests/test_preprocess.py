"""Notebook splitting and parameter substitution.

`preprocess.py` outlives the parser this project used to ship: it is the
reference implementation for the three parameter shapes SQLFluff's
`placeholder` templater does not yet handle (`${a.b}`, `{{ x }}` and `${}`).
These tests are the specification for that upstream contribution, so they
assert the substitution contract only -- no parsing.
"""
from __future__ import annotations

import pytest

from dbsqlparse.preprocess import split_cells, substitute_widgets


# --- parameter substitution -------------------------------------------------
def test_widget_substitution_preserves_length():
    """Offsets must survive, or reported line/columns point at the wrong place."""
    original = "SELECT * FROM ${env}.raw.t WHERE d > ${last_processed_date}"
    result = substitute_widgets(original)
    assert len(result.text) == len(original)
    assert "$" not in result.text


# Four spellings appear in real notebooks. Every one has to keep its length,
# or a diagnostic after it points at the wrong column.
@pytest.mark.parametrize(
    "widget",
    ["${env}", "${test.nrows}", "$db", "{{ station_list }}", "${}"],
    ids=["braced", "braced-dotted", "bare", "dashboard", "empty"],
)
def test_every_parameter_form_is_substituted_and_keeps_its_length(widget):
    original = f"SELECT * FROM {widget}.t"
    result = substitute_widgets(original)
    assert len(result.text) == len(original)
    assert "$" not in result.text and "{" not in result.text


def test_dotted_widget_does_not_become_a_qualified_name():
    """`${a.b}` must stand in for ONE identifier, not `_a`.`b`."""
    result = substitute_widgets("SELECT * FROM ${test.nrows}")
    assert "." not in result.text[len("SELECT * FROM "):]


# --- notebook cells ---------------------------------------------------------
NOTEBOOK = """-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Title

-- COMMAND ----------

SELECT 1

-- COMMAND ----------

-- MAGIC %python
-- MAGIC spark.sql("this is not sql")
"""


def test_notebook_cells_are_classified():
    kinds = [c.kind for c in split_cells(NOTEBOOK)]
    assert kinds == ["magic", "sql", "magic"]


def test_cell_with_both_magic_and_sql_is_not_skipped():
    """Regression: a mixed cell was classified magic and silently dropped.

    Silently skipping content is the worst failure mode for a CI gate --
    broken SQL reaches main and the tool reports success.
    """
    mixed = "-- MAGIC %md\n-- MAGIC # Title\nSELECT 1"
    cells = split_cells(mixed)
    assert any(c.is_sql for c in cells)


def test_plain_sql_file_is_a_single_cell():
    cells = split_cells("SELECT 1")
    assert len(cells) == 1 and cells[0].is_sql
