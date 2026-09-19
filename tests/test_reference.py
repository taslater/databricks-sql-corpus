"""The reference harness is the oracle for the blind spot the scraped corpus
cannot see. If the loader accepts a mistyped case, or the conformance mapping
is inverted, the corpus agrees with the mistake -- which is the exact failure
mode `corpus/reference/` exists to prevent. Hence the schema table below.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from dbsqlparse.corpus import cli, reference
from dbsqlparse.corpus.reference import (
    CONTROLS,
    MUST_PARSE,
    MUST_REJECT,
    CaseResult,
    ReferenceCase,
    ReferenceError,
    ReferenceReport,
    format_reference_report,
    load_reference,
    reference_payload,
    run_reference_corpus,
    write_reference_json,
)
from dbsqlparse.corpus.runners import CheckResult, SqlFluffRunner

FULL_FORM = "create-flow.append-replace-using-sequence-by"
PARTIAL_FORM = "create-flow.replace-using-without-sequence-by"
FULL_SQL = (
    "CREATE FLOW f AS INSERT INTO t BY NAME "
    "REPLACE USING (c) SEQUENCE BY d SELECT * FROM STREAM s"
)

VALID_FILE = f"""
statement: CREATE FLOW
doc: https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow
syntax: INSERT [ONCE] INTO t BY NAME [ replace_using_spec ] query
cases:
  - id: {FULL_FORM}
    verdict: must-parse
    anchor: "#syntax"
    sql: |
      {FULL_SQL}
  - id: {PARTIAL_FORM}
    verdict: must-reject
    anchor: "#syntax"
    from: {FULL_FORM}
    omits: SEQUENCE BY sequence_column
    sql: CREATE FLOW f AS INSERT INTO t BY NAME REPLACE USING (c) SELECT * FROM STREAM s
    note: The pair is not separable.
"""


def write(root: pathlib.Path, name: str, body: str) -> pathlib.Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def case_list(*bodies: str, statement: str = "S", doc: str = "https://example.com/ref") -> str:
    items = "\n".join("  - " + b.replace("\n", "\n" + " " * 4) for b in bodies)
    return f"statement: {statement}\ndoc: {doc}\ncases:\n{items}\n"


def one_case(body: str, statement: str = "S", doc: str = "https://example.com/ref") -> str:
    return case_list(body, statement=statement, doc=doc)


def make_case(
    id_: str,
    verdict: str,
    *,
    from_id: str = "",
    sql: str = "SELECT 1",
) -> ReferenceCase:
    return ReferenceCase(
        id=id_,
        verdict=verdict,
        sql=sql,
        doc="https://docs.databricks.com/x",
        anchor="#syntax",
        statement="S",
        from_id=from_id,
    )


class FakeRunner:
    """Accepts `accepted` text and rejects everything else.

    `accepted=None` means accept everything, which is what a parser that has
    stopped parsing would look like from the inside -- the known-bad control
    exists to make that visible.
    """

    name = "fake"

    def __init__(self, accepted: set[str] | None = None) -> None:
        self.accepted = accepted
        self.seen: list[str] = []

    def check(self, text: str, path: str) -> CheckResult:
        self.seen.append(path)
        ok = True if self.accepted is None else text in self.accepted
        return CheckResult(ok, None if ok else "rejected by the fake", 7)

    def check_many(self, paths: list[pathlib.Path]) -> dict[str, CheckResult]:
        raise NotImplementedError


@pytest.fixture
def conforming_runner() -> FakeRunner:
    return FakeRunner(accepted={"SELECT 1", FULL_SQL})


# --- loading ----------------------------------------------------------------
def test_a_valid_file_loads_with_its_metadata(tmp_path):
    write(tmp_path, "create_flow.yml", VALID_FILE)
    cases = load_reference(tmp_path)
    assert [c.id for c in cases] == [FULL_FORM, PARTIAL_FORM]

    full, partial = cases
    assert full.verdict == MUST_PARSE
    assert full.statement == "CREATE FLOW"
    assert full.doc.startswith("https://docs.databricks.com/")
    assert full.anchor == "#syntax"
    assert full.sql == FULL_SQL  # the block scalar's trailing newline is stripped
    assert (full.from_id, full.omits, full.note) == ("", "", "")
    assert partial.from_id == FULL_FORM
    assert partial.omits == "SEQUENCE BY sequence_column"
    assert partial.note == "The pair is not separable."
    assert partial.verdict == MUST_REJECT


def test_yaml_extension_loads_and_other_files_are_ignored(tmp_path):
    write(tmp_path, "a.yaml", VALID_FILE)
    write(tmp_path, "README.md", "prose, not a case")
    write(tmp_path, "notes.txt", "also not a case")
    assert len(load_reference(tmp_path)) == 2


def test_files_sort_and_case_order_within_a_file_is_kept(tmp_path):
    write(tmp_path, "b.yml", one_case("id: b\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 2"))
    write(tmp_path, "a.yml", one_case("id: a\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1"))
    write(
        tmp_path, "sub/c.yaml",
        one_case("id: c\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 3"),
    )
    assert [c.id for c in load_reference(tmp_path)] == ["a", "b", "c"]


def test_a_missing_root_is_an_error_not_an_empty_corpus(tmp_path):
    with pytest.raises(ReferenceError, match="no reference corpus"):
        load_reference(tmp_path / "absent")


def test_the_committed_reference_corpus_loads():
    """A schema error in a committed case would otherwise surface only as a
    traceback from whatever run happened to read it first."""
    cases = load_reference()
    assert cases
    assert all(case.sql and case.doc.startswith("https://") for case in cases)


def test_a_case_may_carry_omits_and_note_that_are_empty(tmp_path):
    """`omits` and `note` are optional strings, and an absent one is `""`."""
    body = one_case(
        "id: x\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1\nomits: ''\nnote: ''"
    )
    write(tmp_path, "case.yml", body)
    case = load_reference(tmp_path)[0]
    assert case.omits == "" and case.note == ""


# --- file schema ------------------------------------------------------------
@pytest.mark.parametrize(
    "body, fragment",
    [
        ("[unclosed", "not valid YAML"),
        ("- one\n- two\n", "expected a mapping at the top level"),
        ("", "expected a mapping at the top level"),
        (
            "statement: S\ndoc: https://x\ncases: []\nextra: 1\n",
            "unknown keys ['extra']",
        ),
        ("doc: https://x\ncases: []\n", "missing required key 'statement'"),
        ("statement: S\ncases: []\n", "missing required key 'doc'"),
        ("statement: S\ndoc: https://x\n", "missing required key 'cases'"),
        ("statement: [1]\ndoc: https://x\ncases: []\n", "statement must be a non-empty string"),
        ("statement: ''\ndoc: https://x\ncases: []\n", "statement must be a non-empty string"),
        ("statement: S\ndoc: [1]\ncases: []\n", "doc must be a non-empty string"),
        ("statement: S\ndoc: ''\ncases: []\n", "doc must be a non-empty string"),
        ("statement: S\ndoc: not-a-url\ncases: []\n", "doc must be a URL"),
        ("statement: S\ndoc: https://x\nsyntax: [1]\ncases: []\n", "syntax must be a string"),
        ("statement: S\ndoc: https://x\ncases: 3\n", "cases must be a non-empty list"),
        ("statement: S\ndoc: https://x\ncases: []\n", "cases must be a non-empty list"),
    ],
)
def test_invalid_file_schemas_are_rejected(tmp_path, body, fragment):
    write(tmp_path, "case.yml", body)
    with pytest.raises(ReferenceError, match=re.escape(fragment)):
        load_reference(tmp_path)


# --- case schema ------------------------------------------------------------
VALID_CASE = "id: x\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1"


@pytest.mark.parametrize(
    "body, fragment",
    [
        ("just a string", "every case must be a mapping"),
        (
            "id: x\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1\nextra: 1",
            "unknown keys ['extra']",
        ),
        ("verdict: must-parse\nanchor: '#s'\nsql: SELECT 1", "missing required key 'id'"),
        ("id: x\nanchor: '#s'\nsql: SELECT 1", "missing required key 'verdict'"),
        ("id: x\nverdict: must-parse\nsql: SELECT 1", "missing required key 'anchor'"),
        ("id: x\nverdict: must-parse\nanchor: '#s'", "missing required key 'sql'"),
        ("id: [1]\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1", "case id must be a non-empty string"),
        ("id: ''\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1", "case id must be a non-empty string"),
        ("id: x\nverdict: maybe\nanchor: '#s'\nsql: SELECT 1", "verdict must be one of"),
        ("id: x\nverdict: must-parse\nanchor: [1]\nsql: SELECT 1", "anchor must be a non-empty string"),
        ("id: x\nverdict: must-parse\nanchor: ''\nsql: SELECT 1", "anchor must be a non-empty string"),
        ("id: x\nverdict: must-parse\nanchor: '#s'\nsql: [1]", "sql must be a non-empty string"),
        ("id: x\nverdict: must-parse\nanchor: '#s'\nsql: ''", "sql must be a non-empty string"),
        (
            "id: x\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1\nfrom: [1]",
            "from must be a case id",
        ),
        (
            "id: x\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1",
            "a must-reject case needs `from:`",
        ),
        (
            "id: x\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1\nfrom: y",
            "only a must-reject case may carry `from:`",
        ),
        (
            "id: x\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1\nfrom: y\nomits: [1]",
            "omits must be a string",
        ),
        (
            "id: x\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1\nfrom: y\nnote: [1]",
            "note must be a string",
        ),
    ],
)
def test_invalid_case_schemas_are_rejected(tmp_path, body, fragment):
    write(tmp_path, "case.yml", one_case(body))
    with pytest.raises(ReferenceError, match=re.escape(fragment)):
        load_reference(tmp_path)


def test_duplicate_case_ids_are_rejected_across_files(tmp_path):
    write(tmp_path, "a.yml", one_case(VALID_CASE))
    write(tmp_path, "b.yml", one_case(VALID_CASE))
    with pytest.raises(ReferenceError, match="duplicate case id 'x'"):
        load_reference(tmp_path)


def test_duplicate_case_ids_are_rejected_within_a_file(tmp_path):
    write(tmp_path, "case.yml", case_list(VALID_CASE, VALID_CASE))
    with pytest.raises(ReferenceError, match="duplicate case id 'x'"):
        load_reference(tmp_path)


def test_from_must_resolve_within_the_same_file(tmp_path):
    write(tmp_path, "a.yml", one_case("id: full\nverdict: must-parse\nanchor: '#s'\nsql: SELECT 1"))
    write(
        tmp_path, "b.yml",
        one_case(
            "id: partial\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1\nfrom: full"
        ),
    )
    with pytest.raises(ReferenceError, match="not a case in the same file"):
        load_reference(tmp_path)


def test_from_must_point_at_a_must_parse_case(tmp_path):
    write(
        tmp_path, "a.yml",
        case_list(
            "id: one\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 1\nfrom: two",
            "id: two\nverdict: must-reject\nanchor: '#s'\nsql: SELECT 2\nfrom: one",
        ),
    )
    with pytest.raises(ReferenceError, match="not a must-parse case"):
        load_reference(tmp_path)


# --- running ----------------------------------------------------------------
def test_everything_accepted_fails_must_reject_and_the_bad_control(tmp_path):
    write(tmp_path, "case.yml", VALID_FILE)
    report = run_reference_corpus(FakeRunner(accepted=None), load_reference(tmp_path))
    assert (report.must_parse_total, report.must_parse_passed) == (1, 1)
    assert (report.must_reject_total, report.must_reject_caught) == (1, 0)
    assert report.must_reject_informative == 0
    assert not report.controls_ok
    assert [r.case.id for r in report.failures] == [PARTIAL_FORM]


def test_everything_rejected_fails_must_parse_and_the_good_control(tmp_path):
    write(tmp_path, "case.yml", VALID_FILE)
    report = run_reference_corpus(FakeRunner(accepted=set()), load_reference(tmp_path))
    assert report.must_parse_passed == 0
    assert (report.must_reject_total, report.must_reject_caught) == (1, 1)
    assert report.must_reject_informative == 0  # the full form did not parse either
    assert not report.controls_ok
    assert [r.case.id for r in report.failures] == [FULL_FORM]


def test_conforming_parser_records_messages_and_informative_rejections(
    tmp_path, conforming_runner
):
    write(tmp_path, "case.yml", VALID_FILE)
    report = run_reference_corpus(conforming_runner, load_reference(tmp_path))
    assert report.controls_ok
    assert report.failures == []
    assert (report.must_parse_passed, report.must_reject_caught) == (1, 1)
    assert report.must_reject_informative == 1

    partial = report.of(MUST_REJECT)[0]
    assert partial.parsed is False
    assert partial.message == "rejected by the fake"
    assert partial.line == 7


def test_runner_sees_a_stable_pseudo_path(tmp_path, conforming_runner):
    write(tmp_path, "case.yml", VALID_FILE)
    run_reference_corpus(conforming_runner, load_reference(tmp_path))
    assert f"<reference:{FULL_FORM}>" in conforming_runner.seen


def test_run_without_explicit_cases_reads_the_reference_dir(tmp_path, monkeypatch):
    write(tmp_path, "case.yml", VALID_FILE)
    monkeypatch.setattr(reference, "REFERENCE_DIR", tmp_path)
    report = run_reference_corpus(FakeRunner(accepted={"SELECT 1"}))
    assert report.must_parse_total == 1
    assert report.must_parse_passed == 0


def test_sibling_parsing_is_three_way():
    """No link, a present sibling, and a sibling missing from the subset."""
    unlinked = CaseResult(make_case("x", MUST_REJECT), parsed=False)
    assert ReferenceReport(results=[unlinked]).sibling_parsed(unlinked)

    orphan = CaseResult(make_case("y", MUST_REJECT, from_id="absent"), parsed=False)
    assert ReferenceReport(results=[orphan]).sibling_parsed(orphan)

    full = make_case("full", MUST_PARSE)
    partial = make_case("partial", MUST_REJECT, from_id="full")
    parsed = ReferenceReport(results=[CaseResult(full, parsed=True), CaseResult(partial, parsed=False)])
    assert parsed.sibling_parsed(parsed.results[1])
    unparsed = ReferenceReport(results=[CaseResult(full, parsed=False), CaseResult(partial, parsed=False)])
    assert not unparsed.sibling_parsed(unparsed.results[1])


def test_rates_and_control_status_are_safe_on_an_empty_report():
    report = ReferenceReport()
    assert report.must_parse_rate == 0.0
    assert report.must_reject_rate == 0.0
    assert report.failures == []
    assert report.controls_ok


# --- formatting -------------------------------------------------------------
def test_a_clean_report_prints_rates_and_ok_controls():
    report = ReferenceReport(
        results=[
            CaseResult(make_case("a", MUST_PARSE), parsed=True),
            CaseResult(make_case("b", MUST_REJECT, from_id="a"), parsed=False),
        ],
        controls=[CaseResult(c, parsed=c.verdict == MUST_PARSE) for c in CONTROLS],
    )
    out = format_reference_report(report)
    assert re.search(r"must-parse\s+1/1", out)
    assert re.search(r"must-reject\s+1/1", out)
    assert "controls:    ok" in out
    assert "not match the reference" not in out
    assert "CONTROL FAILED" not in out


def test_failures_vacuous_rejections_and_failed_controls_are_all_printed():
    full = make_case("full", MUST_PARSE)
    full2 = make_case("full2", MUST_PARSE)
    good = make_case("good", MUST_PARSE)
    report = ReferenceReport(
        results=[
            CaseResult(full, parsed=False),  # a failure with no message
            CaseResult(full2, parsed=False, message="syntax error"),
            CaseResult(make_case("partial", MUST_REJECT, from_id="full"), parsed=True,
                       message="accepted anyway"),
            CaseResult(make_case("vacuous", MUST_REJECT, from_id="full2"), parsed=False),
            CaseResult(good, parsed=True),
            CaseResult(make_case("linked_ok", MUST_REJECT, from_id="good"), parsed=False),
        ],
        controls=[
            CaseResult(CONTROLS[0], parsed=False, message="boom"),
            CaseResult(CONTROLS[1], parsed=True),
            CaseResult(CONTROLS[0], parsed=True),  # a conforming control is skipped
        ],
    )
    out = format_reference_report(report)
    assert "[not parsed] full" in out
    assert "https://docs.databricks.com/x#syntax" in out
    assert "syntax error" in out
    assert "[accepted but must be rejected] partial" in out
    assert "accepted anyway" in out
    assert "Vacuous rejections" in out
    assert "  vacuous" in out
    assert "  linked_ok" not in out
    assert "CONTROL FAILED" in out
    assert "control.known-good: boom" in out
    assert "control.known-bad: parsed" in out


def test_a_clean_report_with_no_failures_has_no_extra_sections():
    report = ReferenceReport(controls=[CaseResult(c, parsed=c.verdict == MUST_PARSE) for c in CONTROLS])
    out = format_reference_report(report)
    assert re.search(r"must-parse\s+0/0", out)
    assert re.search(r"must-reject\s+0/0", out)
    assert "Vacuous" not in out
    assert "CONTROL FAILED" not in out


# --- serialisation ----------------------------------------------------------
def test_the_payload_carries_per_case_results_so_a_baseline_diff_can_tell_regressions():
    report = ReferenceReport(
        results=[
            CaseResult(make_case("full", MUST_PARSE), parsed=True),
            CaseResult(
                make_case("partial", MUST_REJECT, from_id="full"),
                parsed=True,
                message="accepted anyway",
            ),
        ],
    )
    payload = reference_payload(report)
    assert payload["controls_ok"] is True
    assert payload["must_parse"] == {"total": 1, "passed": 1, "rate": 100.0}
    assert payload["must_reject"] == {
        "total": 1, "caught": 0, "informative": 0, "rate": 0.0
    }
    assert payload["cases"][0] == {
        "id": "full",
        "verdict": MUST_PARSE,
        "ok": True,
        "statement": "S",
        "doc": "https://docs.databricks.com/x",
        "anchor": "#syntax",
        "message": None,
    }
    assert payload["cases"][1]["ok"] is False
    assert payload["cases"][1]["message"] == "accepted anyway"


def test_the_standalone_json_report_creates_its_parent(tmp_path):
    report = ReferenceReport(
        controls=[CaseResult(c, parsed=c.verdict == MUST_PARSE) for c in CONTROLS]
    )
    out = tmp_path / "nested" / "reference.json"
    write_reference_json(report, out)
    payload = json.loads(out.read_text())
    assert payload["reference"]["controls_ok"] is True
    assert payload["reference"]["cases"] == []


# --- CLI --------------------------------------------------------------------
def _bare_cli(monkeypatch, report):
    monkeypatch.setattr(cli, "get_runner", lambda name, dialect: FakeRunner())
    monkeypatch.setattr(cli, "run_reference_corpus", lambda runner: report)


def test_the_reference_command_prints_and_writes_a_report(tmp_path, monkeypatch, capsys):
    report = ReferenceReport(
        results=[CaseResult(make_case("full", MUST_PARSE), parsed=True)],
        controls=[CaseResult(c, parsed=c.verdict == MUST_PARSE) for c in CONTROLS],
    )
    _bare_cli(monkeypatch, report)
    out = tmp_path / "reference.json"
    assert cli.main(["reference", "--json", str(out)]) == 0
    assert "REFERENCE --" in capsys.readouterr().out
    assert json.loads(out.read_text())["reference"]["must_parse"]["passed"] == 1


def test_the_reference_command_fails_when_a_control_fails(tmp_path, monkeypatch):
    report = ReferenceReport(controls=[CaseResult(CONTROLS[1], parsed=True)])
    _bare_cli(monkeypatch, report)
    assert cli.main(["reference", "--json", str(tmp_path / "r.json")]) == 1


def test_the_reference_command_names_a_broken_corpus(monkeypatch, capsys):
    def broken(runner):
        raise ReferenceError("no reference corpus at /nowhere")

    monkeypatch.setattr(cli, "get_runner", lambda name, dialect: FakeRunner())
    monkeypatch.setattr(cli, "run_reference_corpus", broken)
    assert cli.main(["reference"]) == 2
    assert "reference corpus error" in capsys.readouterr().err


# --- controls against the real parser ---------------------------------------
def test_the_controls_are_what_they_claim():
    """Without this, a broken checker could report a clean sweep.

    The known-bad SQL is the same structurally invalid probe the mutation
    tests use; a runner that accepts it cannot be trusted with any case.
    """
    report = run_reference_corpus(SqlFluffRunner(), cases=[])
    assert report.controls_ok
    assert report.results == []
