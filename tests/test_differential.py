"""The differential report is advisory, but a wrong category would send
someone upstream with the wrong repro or hide an over-acceptance. The join and
classification are pure functions for exactly that reason: they are tested
without a corpus and without sqlglot, and the runner's real behaviour is pinned
separately against the installed version.
"""
from __future__ import annotations

import json

import pytest

from dbsqlparse.corpus import differential
from dbsqlparse.corpus.differential import (
    BOTH_FAIL,
    BOTH_PASS,
    CASE_BOTH_ACCEPT,
    CASE_BOTH_GAP,
    CASE_CONFORMING,
    CASE_OVER_ACCEPT,
    CASE_PRIMARY_GAP,
    CASE_SECOND_GAP,
    CASE_SECOND_LENIENT,
    PRIMARY_ONLY,
    SECOND_ONLY,
    CaseTriage,
    ControlResult,
    DifferentialReport,
    FileTriage,
    classify_case,
    classify_file,
    differential_payload,
    format_differential,
    triage_cases,
    triage_files,
    write_differential_json,
)
from dbsqlparse.corpus.harness import FileResult, SourceReport
from dbsqlparse.corpus.reference import (
    CONTROLS,
    MUST_PARSE,
    MUST_REJECT,
    CaseResult,
    ReferenceCase,
    ReferenceReport,
)
from dbsqlparse.corpus.runners import CheckResult


# ---------------------------------------------------------------------------
# Classification matrices. These encode the policy in docs/sqlglot-plan.md:
# a second-parser rejection is a signal, an acceptance is not.
# ---------------------------------------------------------------------------


def test_classify_file_matrix():
    assert classify_file(True, True) == BOTH_PASS
    assert classify_file(True, False) == SECOND_ONLY
    assert classify_file(False, True) == PRIMARY_ONLY
    assert classify_file(False, False) == BOTH_FAIL


def test_classify_case_must_parse():
    assert classify_case(MUST_PARSE, True, True) == CASE_CONFORMING
    assert classify_case(MUST_PARSE, True, False) == CASE_SECOND_GAP
    assert classify_case(MUST_PARSE, False, True) == CASE_PRIMARY_GAP
    assert classify_case(MUST_PARSE, False, False) == CASE_BOTH_GAP


def test_classify_case_must_reject():
    # both reject -- nothing to report
    assert classify_case(MUST_REJECT, False, False) == CASE_CONFORMING
    # the primary accepts a non-conforming form and the second rejects it:
    # the over-acceptance signal, the #8509 class
    assert classify_case(MUST_REJECT, True, False) == CASE_OVER_ACCEPT
    # both accept -- transcription question rather than a parser finding
    assert classify_case(MUST_REJECT, True, True) == CASE_BOTH_ACCEPT
    # the second accepts what the primary rejects: expected leniency
    assert classify_case(MUST_REJECT, False, True) == CASE_SECOND_LENIENT


# ---------------------------------------------------------------------------
# Corpus join
# ---------------------------------------------------------------------------


def _file(path: str, ok: bool, errors: list[str] | None = None, line: int | None = None):
    return FileResult(
        path=path, source="src", ok=ok, statements=1,
        errors=errors or [], line=line,
    )


def _source(name: str, files: list[FileResult]) -> SourceReport:
    class _S:
        pass

    source = _S()
    source.name = name
    source.expectation = "valid"
    return SourceReport(source=source, files=files)


def test_triage_files_joins_by_path_and_skips_agreement(tmp_path):
    a, b, c = (str(tmp_path / f"{n}.sql") for n in "abc")
    primary = _source("primary-src", [
        _file(a, True), _file(b, False, ["sf error"], line=1), _file(c, False, ["sf error"]),
    ])
    second = _source("second-src", [
        _file(a, True), _file(b, True), _file(c, False, ["glot error"]),
    ])
    out = triage_files([primary], [second])
    # a agrees; b is primary-only; c is both-fail
    assert [f.category for f in out] == [PRIMARY_ONLY, BOTH_FAIL]
    assert out[0].path == b
    assert out[0].message == "sf error"
    assert out[1].other_message == "glot error"


def test_triage_files_skips_files_missing_from_the_other_run(tmp_path):
    a = str(tmp_path / "a.sql")
    primary = _source("p", [_file(a, False, ["sf error"])])
    out = triage_files([primary], [])
    assert out == []


# ---------------------------------------------------------------------------
# Reference join
# ---------------------------------------------------------------------------


def _case(case_id: str, verdict: str, from_id: str = "") -> ReferenceCase:
    return ReferenceCase(
        id=case_id, verdict=verdict, sql="SELECT 1", doc="https://example.com",
        anchor="#syntax", statement="example", from_id=from_id,
    )


def _result(case: ReferenceCase, parsed: bool) -> CaseResult:
    return CaseResult(case, parsed)


def test_triage_cases_must_parse_buckets():
    full = _case("full", MUST_PARSE)
    primary = ReferenceReport(results=[_result(full, False)])
    second = ReferenceReport(results=[_result(full, True)])
    out = triage_cases(primary, second)
    assert [(c.case_id, c.category) for c in out] == [("full", CASE_PRIMARY_GAP)]

    primary = ReferenceReport(results=[_result(full, True)])
    second = ReferenceReport(results=[_result(full, False)])
    assert triage_cases(primary, second)[0].category == CASE_SECOND_GAP

    primary = ReferenceReport(results=[_result(full, False)])
    assert triage_cases(primary, primary)[0].category == CASE_BOTH_GAP


def test_triage_cases_over_acceptance_and_vacuity():
    full = _case("full", MUST_PARSE)
    partial = _case("partial", MUST_REJECT, from_id="full")
    # primary accepts the partial; second rejects it while parsing the full
    # form -> informative over-acceptance
    primary = ReferenceReport(results=[_result(full, True), _result(partial, True)])
    second = ReferenceReport(results=[_result(full, True), _result(partial, False)])
    out = triage_cases(primary, second)
    assert [(c.case_id, c.category, c.informative) for c in out] == [
        ("partial", CASE_OVER_ACCEPT, True)
    ]

    # second cannot parse the full form either, so its rejection of the
    # partial proves nothing -> vacuous
    second_vacuous = ReferenceReport(
        results=[_result(full, False), _result(partial, False)]
    )
    out = triage_cases(
        ReferenceReport(results=[_result(full, False), _result(partial, True)]),
        second_vacuous,
    )
    partial_only = [c for c in out if c.case_id == "partial"]
    assert [(c.case_id, c.informative) for c in partial_only] == [("partial", False)]


def test_triage_cases_leniency_is_not_reported_as_agreement():
    partial = _case("partial", MUST_REJECT, from_id="full")
    full = _case("full", MUST_PARSE)
    primary = ReferenceReport(results=[_result(full, True), _result(partial, False)])
    second = ReferenceReport(results=[_result(full, True), _result(partial, True)])
    out = triage_cases(primary, second)
    assert [(c.case_id, c.category) for c in out] == [
        ("partial", CASE_SECOND_LENIENT)
    ]


# ---------------------------------------------------------------------------
# Controls, formatting, JSON
# ---------------------------------------------------------------------------


class _FakeRunner:
    dialect = "databricks"

    def __init__(self, name: str, results: dict[str, bool], version: str = "test") -> None:
        self.name = name
        self._results = results
        self._version = version

    def version(self) -> str:
        return self._version

    def check(self, text: str, path: str) -> CheckResult:
        ok = self._results.get(path, False)
        return CheckResult(ok, None if ok else "boom")

    def check_many(self, paths):
        return {str(p): self.check("", str(p)) for p in paths}


def test_control_failure_is_the_only_non_zero_signal():
    # A runner that accepts the known-bad control cannot be trusted.
    control_ok = _FakeRunner("ok", {f"<control:{c.id}>": True for c in CONTROLS})
    control_bad = _FakeRunner("bad", {f"<control:{c.id}>": False for c in CONTROLS})
    controls = differential._run_controls((control_ok, control_bad))
    report = DifferentialReport("ok", "bad", controls=controls)
    assert not report.controls_ok
    text = format_differential(report)
    assert "bad FAILED" in text
    assert "misbehaved" in text


def _report() -> DifferentialReport:
    return DifferentialReport(
        primary="sqlfluff",
        second="sqlglot",
        versions={"sqlfluff": "4.3.0", "sqlglot": "30.18.0"},
        controls=[
            ControlResult("sqlfluff", "control.known-good", True),
            ControlResult("sqlfluff", "control.known-bad", True),
            ControlResult("sqlglot", "control.known-good", True),
            ControlResult("sqlglot", "control.known-bad", True),
        ],
        files=[
            FileTriage("/tmp/a.sql", "src", "CHECK ( <id> > 0 )", PRIMARY_ONLY, "Expecting )"),
            FileTriage("/tmp/b.sql", "src", "SELECT <id>", SECOND_ONLY, None, "Expecting )"),
            FileTriage("/tmp/c.sql", "src", "SELECT <id>", BOTH_FAIL, "x", "y"),
        ],
        cases=[
            CaseTriage(
                case_id="doc.gap", verdict=MUST_PARSE, category=CASE_PRIMARY_GAP,
                statement="s", doc="https://example.com", anchor="#a", sql="SELECT 1",
            ),
            CaseTriage(
                case_id="doc.over", verdict=MUST_REJECT, category=CASE_OVER_ACCEPT,
                statement="s", doc="https://example.com", anchor="#b", sql="SELECT 2",
                informative=False,
            ),
        ],
        files_compared=10,
    )


def test_format_differential_labels_and_vacuity():
    text = format_differential(_report())
    assert "ADVISORY ONLY" in text
    assert "sqlfluff-only" in text
    assert "sqlglot-only" in text
    assert "candidate sqlfluff gaps, rank first" in text
    assert "doc.gap" in text
    assert "vacuous" in text
    assert "10 files compared" in text


def test_payload_is_advisory_and_writes(tmp_path):
    report = _report()
    payload = differential_payload(report)
    assert payload["advisory"] is True
    assert payload["controls_ok"] is True
    assert payload["corpus"]["counts"] == {
        "primary_only": 1, "second_only": 1, "both_fail": 1,
    }
    out = tmp_path / "nested" / "diff.json"
    write_differential_json(report, out)
    assert json.loads(out.read_text())["reference"]["cases"][0]["id"] == "doc.gap"


# ---------------------------------------------------------------------------
# Orchestration, with the corpus and the reference stubbed out
# ---------------------------------------------------------------------------


def test_run_differential_joins_and_records_versions(monkeypatch):
    fake_primary = _FakeRunner("sqlfluff", {}, version="4.3.0")
    fake_second = _FakeRunner("sqlglot", {}, version="30.18.0")

    monkeypatch.setattr(
        differential, "run_valid_corpus",
        lambda runner, dirs=None: [_source(runner.name, [])],
    )
    monkeypatch.setattr(
        differential, "run_reference_corpus",
        lambda runner: ReferenceReport(results=[]),
    )
    report = differential.run_differential(fake_primary, fake_second)
    assert report.primary == "sqlfluff"
    assert report.second == "sqlglot"
    assert report.versions == {"sqlfluff": "4.3.0", "sqlglot": "30.18.0"}
    assert len(report.controls) == len(CONTROLS) * 2


# ---------------------------------------------------------------------------
# The installed sqlglot, pinned: the asymmetry the policy rests on.
# ---------------------------------------------------------------------------


@pytest.fixture()
def sqlglot_runner():
    pytest.importorskip("sqlglot")
    from dbsqlparse.corpus.runners import SqlglotRunner

    return SqlglotRunner()


def test_sqlglot_runner_control(sqlglot_runner):
    good = sqlglot_runner.check("SELECT 1", "probe.sql")
    assert good.ok
    bad = sqlglot_runner.check("SELECT a FROM ((t;", "probe.sql")
    assert not bad.ok
    assert bad.line == 1


def test_sqlglot_runner_is_lenient_by_design(sqlglot_runner):
    # Documented in docs/sqlglot-plan.md. If this ever fails, sqlglot tightened
    # and the policy text -- not just this test -- needs revisiting.
    assert sqlglot_runner.check("SELECT a,, b FROM t", "probe.sql").ok


def test_sqlglot_runner_treats_command_fallback_as_failure(sqlglot_runner):
    # Acceptance without understanding would fabricate agreement with
    # SQLFluff, including on the over-acceptance cases this report exists for.
    result = sqlglot_runner.check("CREATE CATALOG c", "probe.sql")
    assert not result.ok
    assert "Command" in (result.message or "")
    # ... while a statement it does model still parses.
    assert sqlglot_runner.check(
        "CREATE OR REFRESH STREAMING TABLE t AS SELECT * FROM STREAM s",
        "probe.sql",
    ).ok
