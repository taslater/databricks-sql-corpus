"""The baseline comparison is what a reviewer reads instead of two JSON files.

If it stays quiet about a real drop, a regression reaches main with a green
tick next to it.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "compare_baseline.py"

spec = importlib.util.spec_from_file_location("compare_baseline", SCRIPT)
assert spec and spec.loader
compare_baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare_baseline)


def report(sources: dict[str, float], rejection: float = 100.0) -> dict:
    return {
        "sources": [
            {"name": n, "expectation": "valid", "total": 10,
             "passed": int(r / 10), "rate": r, "failures": []}
            for n, r in sources.items()
        ],
        "mutation": {"rejection_rate": rejection, "guaranteed_total": 100},
    }


def write(tmp_path: pathlib.Path, name: str, payload: dict) -> str:
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return str(p)


def run(tmp_path, base: dict, new: dict) -> tuple[int, str]:
    a = write(tmp_path, "base.json", base)
    b = write(tmp_path, "new.json", new)
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = compare_baseline.main([a, b])
    return code, buf.getvalue()


def test_identical_reports_are_clean(tmp_path):
    r = report({"spark-tpch": 100.0})
    code, out = run(tmp_path, r, r)
    assert code == 0
    assert "No accuracy regression" in out


def test_recall_drop_is_flagged(tmp_path):
    code, out = run(tmp_path, report({"spark-tpch": 100.0}), report({"spark-tpch": 90.0}))
    assert code == 1
    assert "WARNING" in out and "spark-tpch" in out


def test_improvement_is_not_flagged(tmp_path):
    code, out = run(tmp_path, report({"dbx-dlt": 20.0}), report({"dbx-dlt": 95.0}))
    assert code == 0
    assert "+75.0 pt" in out


def test_new_source_is_not_a_regression(tmp_path):
    """Adding a source that exposes a gap lowers the headline number.

    That is the corpus doing its job, so it must not read as a regression --
    otherwise the only way to keep CI quiet is to stop measuring.
    """
    code, out = run(
        tmp_path,
        report({"spark-tpch": 100.0}),
        report({"spark-tpch": 100.0, "dbx-dlt-notebooks": 20.0}),
    )
    assert code == 0
    assert "new source" in out


def test_removed_source_is_a_regression(tmp_path):
    code, out = run(tmp_path, report({"a": 100.0, "b": 100.0}), report({"a": 100.0}))
    assert code == 1
    assert "removed" in out


def test_rejection_drop_is_flagged(tmp_path):
    code, out = run(
        tmp_path,
        report({"a": 100.0}, rejection=100.0),
        report({"a": 100.0}, rejection=98.0),
    )
    assert code == 1
    assert "rejection" in out


def test_rounding_noise_is_not_a_regression(tmp_path):
    code, _ = run(tmp_path, report({"a": 100.0}), report({"a": 99.99}))
    assert code == 0


@pytest.mark.parametrize("argv", [[], ["one"], ["a", "b", "c"]])
def test_wrong_argument_count_exits_two(argv):
    assert compare_baseline.main(argv) == 2


# --- corpus hygiene ---------------------------------------------------------
def test_json_wearing_a_sql_extension_is_not_counted_as_a_parser_failure():
    """Published pipelines keep `PipelineSetting.json.sql` next to their SQL.
    Scoring it as a recall miss understates the parser forever, for a reason
    that has nothing to do with the parser."""
    from dbsqlparse.corpus.harness import looks_like_json

    assert looks_like_json('-- Databricks notebook source\n{\n  "clusters": []\n}')
    assert looks_like_json("[1, 2]")
    assert looks_like_json("/* header */ {}")


def test_real_sql_is_not_mistaken_for_json():
    from dbsqlparse.corpus.harness import looks_like_json

    assert not looks_like_json("SELECT 1")
    assert not looks_like_json("-- a comment\nSELECT * FROM t")
    assert not looks_like_json("-- Databricks notebook source\nCREATE TABLE t (a INT)")


# --- mutation tiering -------------------------------------------------------
# A mutation is only GUARANTEED if no keyword rule can rescue it. Getting this
# wrong reports the parser being correct as a false negative.
#
# These assertions used to check the tiering against this project's own
# parser. That parser is retired, so they check it against the parser actually
# under test.
import random

from dbsqlparse.corpus.mutate import GUARANTEED, WEAK, mutate
from dbsqlparse.corpus.runners import SqlFluffRunner


@pytest.fixture(scope="module")
def parses():
    runner = SqlFluffRunner()
    return lambda sql: runner.check(sql, "<test>").ok


def test_the_probe_itself_rejects_broken_sql(parses):
    """Without this, every assertion below could pass on a broken checker."""
    assert not parses("SELECT a FROM ((t;")


def test_trailing_boolean_operator_is_weak_not_guaranteed(parses):
    """`SELECT a OR` is `SELECT a AS OR` in the default keyword mode -- a
    column aliased to the word OR, which is valid."""
    assert parses("SELECT a OR")  # the reading that makes it weak

    kinds = {m.kind: m.tier for m in mutate("SELECT a OR b FROM t", "x", random.Random(0))}
    assert kinds.get("dangling-boolean-operator") == WEAK
    assert kinds.get("dangling-operator", GUARANTEED) == GUARANTEED


def test_equals_inside_a_set_statement_is_not_mutated():
    """An EQ inside a SET statement is never truncated into a mutant.

    The guard exists because Spark accepts `SET key =` as a config assignment
    with an empty value, which makes the truncation valid SQL rather than the
    rejection failure the GUARANTEED tier promises.

    SQLFluff currently rejects that form -- see docs/gaps.md -- so the guard is
    not strictly required against today's SQLFluff. It is kept because it is
    the conservative direction: if SQLFluff later matches Spark here, a
    mutation generated without the guard would silently start reporting a
    false negative. This deliberately does not assert SQLFluff's behaviour,
    since the form is undocumented and either reading may be right.
    """
    mutants = mutate("SET spark.sql.foo = 5", "x", random.Random(0))
    assert not [m for m in mutants if m.kind == "dangling-operator"]


def test_set_after_a_cell_separator_is_still_a_set_statement():
    """Notebooks separate statements with cells, not semicolons. Walking back
    only to a semicolon is how this escaped the first time."""
    notebook = "SELECT 1\n\n-- COMMAND ----------\n\nSET k = 2"
    mutants = mutate(notebook, "x", random.Random(0))
    assert not [m for m in mutants if m.kind == "dangling-operator"]


def test_equals_outside_a_set_statement_is_still_guaranteed(parses):
    mutants = [m for m in mutate("SELECT a = 1 FROM t", "x", random.Random(0))
               if m.kind == "dangling-operator"]
    assert mutants and all(m.tier == GUARANTEED for m in mutants)
    assert all(not parses(m.sql) for m in mutants)


def test_token_offsets_reconstruct_the_input():
    """Mutations splice by character offset, so the offsets must be exact."""
    from dbsqlparse.corpus.mutate import _tokens

    sql = "SELECT a + 1, 'str' FROM (t) WHERE a = 1 AND b;"
    toks = _tokens(sql)
    assert "".join(t.raw for t in toks) == sql
    assert all(sql[t.start : t.stop + 1] == t.raw for t in toks)
