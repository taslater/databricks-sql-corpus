"""The drift check guards the oracle's freshness, so a bug in it is a bug in
the thing that tells us when to trust the oracle. It also decides what counts
as a finding, and a matcher that quietly matched everything would report a
clean run forever. Hence the matrix below, and the controls.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import urllib.error

import pytest

from dbsqlparse.corpus import drift
from dbsqlparse.corpus.drift import (
    CHANGED,
    ERROR,
    MOVED,
    SAME,
    UNCERTAIN,
    CONTROL_FILE,
    DriftReport,
    DriftVerdict,
    PageBlock,
    check_file,
    compare,
    coverage_urls,
    control_verdicts,
    drift_payload,
    extract_blocks,
    fetch_doc,
    format_diff,
    format_drift_report,
    format_index_report,
    format_stale_report,
    index_diff,
    load_index_ignore,
    run_drift,
    run_index_check,
    sitemap_urls,
    stale_files,
)
from dbsqlparse.corpus.reference import ReferenceFile

DOC = "https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-x"


def ref_file(
    *,
    name: str = "x.yml",
    syntax: str = "SELECT 1",
    doc: str = DOC,
    statement: str = "X",
    checked: str = "2026-01-01",
) -> ReferenceFile:
    return ReferenceFile(
        path=pathlib.Path(name),
        statement=statement,
        doc=doc,
        syntax=syntax,
        checked=checked,
    )


def page(*blocks: str) -> str:
    body = "".join(f"<pre>{b}</pre>" for b in blocks)
    return f"<html><body>{body}</body></html>"


class FakeResponse:
    def __init__(self, url: str, body: str) -> None:
        self._url = url
        self._body = body

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args) -> bool:
        return False


def fake_urlopen(url: str, body: str = "<pre>SELECT 1</pre>", final: str | None = None):
    """A stand-in for `urllib.request.urlopen`, used by the `fetch_doc` test."""

    def opener(request, timeout=0):
        return FakeResponse(final or url, body)

    return opener


def fake_fetch(body: str = "<pre>SELECT 1</pre>", final: str | None = None):
    """A stand-in for `fetch_doc` itself: returns (final_url, page)."""

    def fetch(url: str):
        return final or url, body

    return fetch


# ---------------------------------------------------------------------------
# Block extraction and normalisation
# ---------------------------------------------------------------------------


def test_extract_blocks_returns_every_pre_in_order():
    blocks = extract_blocks(page("A", "B"))
    assert [b.raw for b in blocks] == ["A", "B"]


def test_block_raw_keeps_angle_brackets_via_entities():
    # Stripping tags before unescaping is what keeps `&lt;` alive.
    block = PageBlock("STRUCT &lt; [fieldName] &gt;")
    assert block.raw == "STRUCT < [fieldName] >"
    assert block.tight == "struct<[fieldname]>"


def test_block_raw_strips_real_tags():
    assert PageBlock("SELECT <b>1</b>").raw == "SELECT 1"


def test_block_comparable_strips_prompt():
    assert PageBlock("> CLEAR CACHE").comparable == "clearcache"


def test_block_is_example_matrix():
    assert PageBlock("> SELECT 1").is_example
    assert PageBlock("-- a comment").is_example
    assert not PageBlock("SELECT 1").is_example


def test_verdict_is_finding_matrix():
    assert DriftVerdict(ref_file(), CHANGED).is_finding
    assert DriftVerdict(ref_file(), MOVED).is_finding
    assert not DriftVerdict(ref_file(), SAME).is_finding
    assert not DriftVerdict(ref_file(), UNCERTAIN).is_finding


# ---------------------------------------------------------------------------
# compare(): the match matrix
# ---------------------------------------------------------------------------


def test_compare_same_single_block():
    verdict = compare(ref_file(syntax="SELECT 1"), page("SELECT 1"))
    assert verdict.verdict == SAME


def test_compare_same_ignores_whitespace_and_case():
    # The live page has no space where the transcription breaks the line.
    verdict = compare(ref_file(syntax="to_view_name\n  alter_body"), page("to_view_namealter_body"))
    assert verdict.verdict == SAME


def test_compare_same_via_prompt_stripped_block():
    verdict = compare(ref_file(syntax="CLEAR CACHE"), page("> CLEAR CACHE", "> CLEAR CACHE;"))
    assert verdict.verdict == SAME


def test_compare_same_via_join_of_production_blocks():
    # A production split across blocks with an example interleaved, as on
    # `hints`: the example is excluded, the two productions are joined.
    verdict = compare(ref_file(syntax="A B"), page("A", "> example", "B"))
    assert verdict.verdict == SAME
    assert verdict.detail == "the production blocks"


def test_compare_same_via_consecutive_run():
    # One block is an example, so the join excludes it; the run includes it.
    verdict = compare(ref_file(syntax="A B"), page("A", "> B"))
    assert verdict.verdict == SAME
    assert verdict.detail == "consecutive code blocks"


def test_compare_changed_reports_a_diff():
    verdict = compare(ref_file(syntax="SELECT a"), page("SELECT b"))
    assert verdict.verdict == CHANGED
    assert "-" in verdict.diff and "+" in verdict.diff


def test_compare_moved_when_the_live_url_differs():
    verdict = compare(ref_file(), page("SELECT 1"), live_url="https://docs.databricks.com/elsewhere")
    assert verdict.verdict == MOVED


def test_compare_same_when_the_live_url_matches_with_a_trailing_slash():
    verdict = compare(ref_file(doc=DOC + "/"), page("SELECT 1"), live_url=DOC)
    assert verdict.verdict == SAME


def test_compare_uncertain_when_no_code_block():
    verdict = compare(ref_file(), "<p>prose only</p>")
    assert verdict.verdict == UNCERTAIN


def test_compare_uncertain_when_the_transcription_is_prose():
    verdict = compare(ref_file(syntax="one cell magic command per cell"), page("something else"))
    assert verdict.verdict == UNCERTAIN


# ---------------------------------------------------------------------------
# format_diff
# ---------------------------------------------------------------------------


def test_format_diff_shows_replace_and_insert():
    diff = format_diff("A B C", "A X C D")
    assert "-B" in diff
    assert "+X" in diff
    assert "+D" in diff


def test_format_diff_empty_when_equal():
    assert format_diff("A B", "A B") == ""


def test_format_diff_shows_a_pure_delete():
    assert format_diff("A B C", "A C") == "-B"


def test_compare_changed_for_a_bracketed_production():
    # Exercises the metacharacter branch of the production detector.
    verdict = compare(ref_file(syntax="SELECT [a]"), page("SELECT b"))
    assert verdict.verdict == CHANGED


def test_looks_like_production_matrix():
    assert drift._looks_like_production("SELECT [a]")
    assert drift._looks_like_production("SELECT a")
    assert not drift._looks_like_production("a notebook cell holds one command")


# ---------------------------------------------------------------------------
# check_file(): network errors become verdicts
# ---------------------------------------------------------------------------


def test_check_file_success():
    verdict = check_file(ref_file(), fetch=fake_fetch())
    assert verdict.verdict == SAME


def test_check_file_404_is_moved():
    def fetch(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    verdict = check_file(ref_file(), fetch=fetch)
    assert verdict.verdict == MOVED


def test_check_file_other_http_error():
    def fetch(url):
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)

    verdict = check_file(ref_file(), fetch=fetch)
    assert verdict.verdict == ERROR
    assert "500" in verdict.detail


def test_check_file_url_error():
    def fetch(url):
        raise urllib.error.URLError("offline")

    assert check_file(ref_file(), fetch=fetch).verdict == ERROR


def test_check_file_os_error():
    def fetch(url):
        raise OSError("socket closed")

    assert check_file(ref_file(), fetch=fetch).verdict == ERROR


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_controls_pass_on_a_correct_matcher():
    assert [v.verdict for v in control_verdicts()] == [SAME, CHANGED, UNCERTAIN]


def test_controls_fail_when_the_matcher_matches_everything(monkeypatch):
    monkeypatch.setattr(drift, "compare", lambda *a, **k: DriftVerdict(CONTROL_FILE, SAME))
    assert not DriftReport(verdicts=[], controls=control_verdicts()).controls_ok


# ---------------------------------------------------------------------------
# run_drift
# ---------------------------------------------------------------------------


def test_run_drift_uses_loaded_files_and_reports_progress(monkeypatch):
    files = [ref_file(name="a.yml"), ref_file(name="b.yml")]
    monkeypatch.setattr(drift, "load_reference_files", lambda root=None: files)
    seen: list[tuple[int, int, str]] = []
    report = run_drift(
        fetch=fake_fetch(),
        progress=lambda done, total, file: seen.append((done, total, file.path.name)),
    )
    assert len(report.verdicts) == 2
    assert seen == [(1, 2, "a.yml"), (2, 2, "b.yml")]
    assert report.controls_ok


def test_run_drift_without_progress():
    report = run_drift(files=[ref_file()], fetch=fake_fetch())
    assert len(report.verdicts) == 1


# ---------------------------------------------------------------------------
# staleness
# ---------------------------------------------------------------------------


def test_stale_files_oldest_first():
    files = [
        ref_file(name="new.yml", checked="2026-06-01"),
        ref_file(name="old.yml", checked="2026-01-01"),
        ref_file(name="mid.yml", checked="2026-04-01"),
    ]
    stale = stale_files(90, files=files, today=datetime.date(2026, 7, 1))
    assert [f.path.name for f, _ in stale] == ["old.yml", "mid.yml"]
    assert stale[0][1] > stale[1][1]


def test_stale_files_none_when_fresh():
    assert stale_files(90, files=[ref_file(checked="2026-06-30")], today=datetime.date(2026, 7, 1)) == []


def test_stale_files_loads_when_unspecified(monkeypatch):
    monkeypatch.setattr(drift, "load_reference_files", lambda root=None: [ref_file(checked="2020-01-01")])
    assert stale_files(90, today=datetime.date(2026, 7, 1))


# ---------------------------------------------------------------------------
# the page-set check
# ---------------------------------------------------------------------------


def test_sitemap_urls_filters_to_the_roots():
    xml = (
        f"<url><loc>{DOC}</loc></url>"
        "<url><loc>https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow</loc></url>"
        "<url><loc>https://docs.databricks.com/aws/en/genie/</loc></url>"
    )
    assert sitemap_urls(xml) == {
        DOC,
        "https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-flow",
    }


NEW_URL = "https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-new"
GONE_URL = "https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-gone"


def test_index_diff_new_and_gone():
    files = [ref_file(doc=DOC), ref_file(name="gone.yml", doc=GONE_URL)]
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{NEW_URL}</loc></url>"
    diff = index_diff(xml, files)
    assert diff.new == (NEW_URL,)
    assert diff.gone == (GONE_URL,)
    assert not diff.ok


def test_index_diff_empty_when_ok():
    files = [ref_file(doc=DOC)]
    xml = f"<url><loc>{DOC}</loc></url>"
    assert index_diff(xml, files).ok


def test_index_diff_only_reports_tracked_families():
    # A function page is not a statement page and is never `new`.
    files = [ref_file(doc=DOC)]
    func = "https://docs.databricks.com/aws/en/sql/language-manual/functions/abs"
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{func}</loc></url>"
    assert index_diff(xml, files).ok


def test_index_diff_known_urls_suppress_a_page():
    files = [ref_file(doc=DOC)]
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{NEW_URL}</loc></url>"
    assert index_diff(xml, files, known_urls={NEW_URL}).ok


def test_index_diff_ignore_suppresses_a_page():
    files = [ref_file(doc=DOC)]
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{NEW_URL}</loc></url>"
    assert index_diff(xml, files, ignore=("ddl-new",)).ok


def test_index_diff_ignores_a_bare_root():
    files = [ref_file(doc=DOC)]
    root = "https://docs.databricks.com/aws/en/sql/language-manual/"
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{root}</loc></url>"
    assert index_diff(xml, files).ok


def test_index_diff_trailing_slash_is_covered():
    files = [ref_file(doc=DOC + "/")]
    xml = f"<url><loc>{DOC}</loc></url>"
    assert index_diff(xml, files).ok


def test_index_diff_does_not_report_out_of_root_files_gone():
    files = [ref_file(doc="https://docs.databricks.com/aws/en/notebooks/notebooks-code")]
    xml = "<url><loc>https://docs.databricks.com/aws/en/sql/language-manual/x</loc></url>"
    assert index_diff(xml, files).ok


def test_load_index_ignore_missing_file_uses_defaults(tmp_path):
    assert load_index_ignore(tmp_path / "nope.txt") == drift.DEFAULT_INDEX_IGNORE


def test_load_index_ignore_default_path(monkeypatch, tmp_path):
    monkeypatch.setattr(drift, "INDEX_IGNORE_PATH", tmp_path / "missing.txt")
    assert load_index_ignore() == drift.DEFAULT_INDEX_IGNORE


def test_load_index_ignore_reads_patterns_and_skips_comments(tmp_path):
    path = tmp_path / "ignore.txt"
    path.write_text("# a comment\n\n/functions/\n  /landing/  \n", encoding="utf-8")
    assert load_index_ignore(path) == ("/functions/", "/landing/")


def test_coverage_urls_missing_file_is_empty(tmp_path):
    assert coverage_urls(tmp_path / "nope.md") == set()


def test_coverage_urls_reads_markdown_links(tmp_path):
    path = tmp_path / "coverage.md"
    path.write_text(f"| [x]({DOC}) | done |\n| [y]({NEW_URL}) | n/a |\n", encoding="utf-8")
    assert coverage_urls(path) == {DOC, NEW_URL}


def test_run_index_check_fetches_and_uses_the_ledger(monkeypatch):
    files = [ref_file(doc=DOC)]
    monkeypatch.setattr(drift, "load_reference_files", lambda root=None: files)
    monkeypatch.setattr(drift, "load_index_ignore", lambda path=None: ())
    monkeypatch.setattr(drift, "coverage_urls", lambda path=None: {NEW_URL})
    xml = f"<url><loc>{DOC}</loc></url><url><loc>{NEW_URL}</loc></url>"
    assert run_index_check(fetch=lambda url: (url, xml)).ok


def test_run_index_check_accepts_explicit_arguments():
    xml = f"<url><loc>{DOC}</loc></url>"
    diff = run_index_check(
        files=[ref_file(doc=DOC)],
        fetch=lambda url: (url, xml),
        ignore=(),
        families=("nothing-matches",),
        known_urls=set(),
    )
    assert diff.ok


def test_report_findings_property():
    changed = compare(ref_file(name="c.yml", syntax="SELECT a"), page("SELECT b"))
    ok = compare(ref_file(name="s.yml"), page("SELECT 1"))
    assert [v.file.path.name for v in report_with(changed, ok).findings] == ["c.yml"]


# ---------------------------------------------------------------------------
# fetch_doc
# ---------------------------------------------------------------------------


def test_fetch_doc_reads_body_and_final_url(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen("https://x", "<pre>A</pre>", final="https://y"))
    url, body = fetch_doc("https://x")
    assert url == "https://y"
    assert body == "<pre>A</pre>"


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def report_with(*verdicts: DriftVerdict) -> DriftReport:
    return DriftReport(verdicts=list(verdicts), controls=control_verdicts())


def test_format_drift_report_lists_findings_and_uncertain():
    changed = compare(ref_file(name="c.yml", syntax="SELECT a"), page("SELECT b"))
    moved = compare(ref_file(name="m.yml"), page("SELECT 1"), live_url="https://elsewhere")
    uncertain = compare(ref_file(name="u.yml"), "<p>none</p>")
    ok = compare(ref_file(name="s.yml"), page("SELECT 1"))
    text = format_drift_report(report_with(changed, moved, uncertain, ok))
    assert "c.yml" in text
    assert "m.yml" in text
    assert "uncertain (1)" in text
    assert "controls:   ok" in text


def test_format_drift_report_flags_control_failure():
    report = DriftReport(verdicts=[], controls=[DriftVerdict(CONTROL_FILE, CHANGED)])
    text = format_drift_report(report)
    assert "CONTROL FAILED" in text


def test_format_stale_report_lists_and_empty():
    stale = [(ref_file(name="a.yml"), 120)]
    assert "120d" in format_stale_report(stale)
    assert "(none)" in format_stale_report([])


def test_format_index_report_shows_urls_families_and_ignore():
    diff = drift.IndexDiff(new=("https://new",), gone=("https://gone",))
    text = format_index_report(diff, ("/sql-ref-syntax-",), ("/functions/",))
    assert "https://new" in text
    assert "https://gone" in text
    assert "/sql-ref-syntax-" in text
    assert "suppressed patterns" in text


def test_format_index_report_without_ignore():
    text = format_index_report(drift.IndexDiff(new=(), gone=()), ("/sql-ref-syntax-",))
    assert "suppressed patterns" not in text


def test_drift_payload_and_write(tmp_path):
    changed = compare(ref_file(name="c.yml", syntax="SELECT a"), page("SELECT b"))
    payload = drift_payload(report_with(changed))
    assert payload["totals"][CHANGED] == 1
    assert payload["verdicts"][0]["file"] == "c.yml"
    out = tmp_path / "nested" / "drift.json"
    drift.write_drift_json(report_with(changed), out)
    assert json.loads(out.read_text())["totals"][CHANGED] == 1
