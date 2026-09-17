"""Regression tests. Most of these lock in a bug that actually bit us."""
from __future__ import annotations

import pytest

from dbsqlparse.parser import ParseOptions, parse_statement, parse_text, split_statements
from dbsqlparse.preprocess import split_cells, substitute_widgets


# --- case sensitivity -------------------------------------------------------
# Spark declares keywords as uppercase literals and folds case in Scala, outside
# the grammar. A straight port of the .g4 rejects all lowercase SQL.
@pytest.mark.parametrize(
    "sql",
    [
        "select 1",
        "SELECT ROW_NUMBER() OVER (PARTITION BY a ORDER BY b DESC) as rn FROM t",
        "Create Or Replace Table t (id BIGINT) using delta",
        "select cast(x as boolean) as is_ok from t",
        "MERGE into t USING s on t.id = s.id when matched then update set *",
    ],
)
def test_keywords_are_case_insensitive(sql):
    assert parse_statement(sql).ok, sql


def test_identifier_case_is_preserved():
    """Case folding must not reach token text -- lint rules read these names."""
    result = parse_statement("select MyCol as My_Alias from T")
    assert result.ok
    text = result.tree.getText()
    assert "MyCol" in text and "My_Alias" in text


# --- widget substitution ----------------------------------------------------
def test_widget_substitution_preserves_length():
    """Offsets must survive, or reported line/columns point at the wrong place."""
    original = "SELECT * FROM ${env}.raw.t WHERE d > ${last_processed_date}"
    result = substitute_widgets(original)
    assert len(result.text) == len(original)
    assert "$" not in result.text


def test_widget_sql_parses():
    assert parse_text("SELECT * FROM ${env}.raw.events_raw").ok


def test_named_and_positional_parameters_need_no_preprocessing():
    assert parse_statement("SELECT * FROM t WHERE id = :my_param").ok
    assert parse_statement("SELECT * FROM t WHERE id = ?").ok


# --- notebook handling ------------------------------------------------------
NOTEBOOK = """-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Title

-- COMMAND ----------

SELECT 1;

-- COMMAND ----------

-- MAGIC %python
-- MAGIC spark.sql("this is not sql")
"""


def test_notebook_cells_are_classified():
    kinds = [c.kind for c in split_cells(NOTEBOOK)]
    assert kinds == ["magic", "sql", "magic"]


def test_notebook_parses_ignoring_magic_cells():
    assert parse_text(NOTEBOOK).ok


def test_cell_with_both_magic_and_sql_is_not_skipped():
    """Regression: a mixed cell was classified magic and silently dropped.

    Silently skipping content is the worst failure mode for a CI gate --
    broken SQL reaches main and the tool reports success.
    """
    mixed = "-- MAGIC %md\n-- MAGIC # Title\nSELECT FROM FROM FROM ((("
    assert not parse_text(mixed).ok


def test_plain_sql_file_is_a_single_cell():
    cells = split_cells("SELECT 1")
    assert len(cells) == 1 and cells[0].is_sql


# --- statement splitting ----------------------------------------------------
def test_semicolons_inside_literals_do_not_split():
    sql = "SELECT 'a;b' AS x; SELECT `weird;col` FROM t"
    assert len(split_statements(sql)) == 2


def test_semicolon_in_comment_does_not_split():
    assert len(split_statements("SELECT 1 -- trailing ; comment\n; SELECT 2")) == 2


def test_multi_statement_file_parses():
    result = parse_text("SELECT 1;\nSELECT 2;\nSELECT 3;")
    assert result.ok and result.statement_count == 3


# --- error positions --------------------------------------------------------
def test_error_line_points_at_the_real_line():
    sql = "SELECT 1;\nSELECT 2;\nSELECT ((( FROM t;"
    result = parse_text(sql)
    assert not result.ok
    assert result.diagnostics[0].line == 3


def test_error_line_is_offset_by_notebook_cell():
    nb = "-- Databricks notebook source\n\n-- COMMAND ----------\n\nSELECT ((( FROM t\n"
    result = parse_text(nb)
    assert not result.ok
    assert result.diagnostics[0].line == 5


# --- keyword strictness -----------------------------------------------------
def test_non_ansi_mode_allows_keywords_as_identifiers():
    """Spark's default. `WHERE` here is a table alias, and that is correct."""
    assert parse_text("SELECT * FROM t WHERE").ok


def test_ansi_mode_rejects_keyword_as_alias():
    opts = ParseOptions(ansi_reserved_keywords=True)
    assert not parse_text("SELECT * FROM t WHERE", options=opts).ok


# --- genuinely invalid SQL --------------------------------------------------
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT a,, b FROM t",
        "SELECT a FROM (SELECT 1",
        "SELECT 'unterminated FROM t",
        "SELECT a FROM t WHERE x =",
        "/* unclosed\nSELECT 1",
        "SELCT 1",
    ],
)
def test_invalid_sql_is_rejected(sql):
    assert not parse_text(sql).ok, sql


# --- Databricks-specific syntax --------------------------------------------
@pytest.mark.parametrize(
    "sql",
    [
        "CREATE OR REPLACE TABLE main.raw.t (id BIGINT) USING delta",
        "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET *",
        "SELECT CAST(x AS MAP<STRING, ARRAY<INT>>) FROM t",
        "SELECT 1 >> 2, 3.5, 2.3D FROM t",
        "CREATE TABLE t (id BIGINT) TBLPROPERTIES ('delta.minReaderVersion' = '3')",
    ],
)
def test_databricks_syntax(sql):
    assert parse_statement(sql).ok, sql
