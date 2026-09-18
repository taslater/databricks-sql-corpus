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
