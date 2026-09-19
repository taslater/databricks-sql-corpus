"""The reference corpus: cases transcribed from the Databricks SQL reference.

The scraped corpus measures SQLFluff against 867 files of published Databricks
SQL. It samples what people *publish*, not what the dialect *allows*: recall
cannot fail on a construct no file uses, and `mutate.py` derives its invalid
input from corpus SQL, so it cannot invent a partial form either. Both
measurements are blind in the same place, and a fixture written from the same
reading of a doc page agrees with whatever that reading got wrong.

That blind spot shipped a defect. SQLFluff #8509 (merged 2026-09-18)
implemented `[ replace_using_spec ]` as optional-as-a-whole but never bound
its interior, so `main` accepts `REPLACE USING (c)` and rejects the documented
`REPLACE USING (c) SEQUENCE BY d`. Nothing in this repo could have caught it.

This module reads the complement: a small corpus transcribed from the
Databricks SQL reference rather than scraped from GitHub. Each case carries

    verdict     must-parse   documented syntax; the parser must accept it
                must-reject  a partial form the reference does not define;
                             the parser must reject it
    doc/anchor  where the transcription came from
    from        for a must-reject case, the full-form sibling whose production
                it partially omits
    omits       the omitted production, quoted from the reference; required on
                every must-reject case, and checked against the file's syntax
                block, so an invented omission cannot load

Each file carries `syntax` (the reference's production, verbatim) and
`checked` (the date the page was read), both required: the syntax block is
what a reviewer diffs the cases against, and the date is what tells a stale
transcription from a fresh one on a page Databricks has since revised.

The rule that generates the cases: **wherever the reference brackets an
optional multi-token production, the partial forms are explicit must-reject
cases.** That is exactly where optionality gets misplaced in a hand-written
grammar, and it is the check that would have caught #8509 before it merged.

The two readings differ from the scraped corpus's two, so they are reported
separately:

    must-parse pass rate     a miss is a FALSE POSITIVE -- the reference
                             documents syntax that CI would block
    must-reject catch rate   a miss is a FALSE NEGATIVE -- the parser accepts
                             a form the reference does not define

A must-reject case is only *informative* when its full-form sibling parses: if
the whole statement is unsupported, its rejection proves nothing about the
partial form. The report separates the two so a wholly unparsable statement
cannot fake a clean catch rate.

Every batch also runs two controls -- one knowingly valid, one knowingly
invalid -- built here rather than kept in the data, so an edit to a YAML file
cannot remove them. Three separate harness bugs in this repo once made failure
look like success; a control catches all three.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
from dataclasses import dataclass, field

import yaml

from .harness import REPO_ROOT
from .runners import Runner

REFERENCE_DIR = REPO_ROOT / "corpus" / "reference"

MUST_PARSE = "must-parse"
MUST_REJECT = "must-reject"
VERDICTS = (MUST_PARSE, MUST_REJECT)

_FILE_KEYS = frozenset({"statement", "doc", "syntax", "checked", "cases"})
_CASE_KEYS = frozenset({"id", "verdict", "anchor", "sql", "from", "omits", "note"})


class ReferenceError(ValueError):
    """A reference file does not match the schema. Names the file and case."""


@dataclass(frozen=True)
class ReferenceCase:
    """One transcribed statement and the reference's verdict on it."""

    id: str
    verdict: str
    sql: str
    doc: str
    anchor: str
    statement: str
    checked: str = ""
    from_id: str = ""
    omits: str = ""
    note: str = ""


@dataclass(frozen=True)
class CaseResult:
    case: ReferenceCase
    parsed: bool
    message: str | None = None
    line: int | None = None

    @property
    def conforms(self) -> bool:
        """Did the parser do what the reference requires for this case?"""
        return self.parsed if self.case.verdict == MUST_PARSE else not self.parsed


# Kept in code, not in the YAML, so no data edit can drop them. The known-bad
# SQL is structurally invalid -- unbalanced brackets, dangling semicolon -- so
# no keyword-as-identifier reading can rescue it.
CONTROLS: tuple[ReferenceCase, ...] = (
    ReferenceCase(
        id="control.known-good",
        verdict=MUST_PARSE,
        sql="SELECT 1",
        doc="control",
        anchor="control",
        statement="control",
        note="A parser that rejects this cannot be trusted with any case below.",
    ),
    ReferenceCase(
        id="control.known-bad",
        verdict=MUST_REJECT,
        sql="SELECT a FROM ((t;",
        doc="control",
        anchor="control",
        statement="control",
        note="A parser that accepts this cannot be trusted with any case below.",
    ),
)


@dataclass
class ReferenceReport:
    results: list[CaseResult] = field(default_factory=list)
    controls: list[CaseResult] = field(default_factory=list)

    def of(self, verdict: str) -> list[CaseResult]:
        return [r for r in self.results if r.case.verdict == verdict]

    @property
    def controls_ok(self) -> bool:
        return all(r.conforms for r in self.controls)

    @property
    def must_parse_total(self) -> int:
        return len(self.of(MUST_PARSE))

    @property
    def must_parse_passed(self) -> int:
        return sum(1 for r in self.of(MUST_PARSE) if r.conforms)

    @property
    def must_reject_total(self) -> int:
        return len(self.of(MUST_REJECT))

    @property
    def must_reject_caught(self) -> int:
        return sum(1 for r in self.of(MUST_REJECT) if r.conforms)

    @property
    def must_reject_informative(self) -> int:
        """Caught rejections whose full form parses, so the check has teeth."""
        return sum(
            1 for r in self.of(MUST_REJECT)
            if r.conforms and self.sibling_parsed(r)
        )

    @property
    def must_reject_vacuous(self) -> int:
        """Caught rejections whose full form does not parse, so they prove
        nothing about the partial form. The count should fall as gaps close;
        it is the corpus's own health metric."""
        return sum(
            1 for r in self.of(MUST_REJECT)
            if r.conforms and not self.sibling_parsed(r)
        )

    @property
    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if not r.conforms]

    def sibling_parsed(self, result: CaseResult) -> bool:
        """True when this case's full-form sibling parses.

        A must-reject case whose full form does not parse proves nothing: the
        rejection may be for an unrelated reason because the whole statement
        is unsupported. Those are reported as vacuous rather than caught.
        Without a `from:` link, or when the subset under test omits the
        sibling, there is nothing to judge against and the case stands.
        """
        if not result.case.from_id:
            return True
        for other in self.results:
            if other.case.id == result.case.from_id:
                return other.parsed
        return True

    @staticmethod
    def _rate(part: int, whole: int) -> float:
        return (part / whole * 100) if whole else 0.0

    @property
    def must_parse_rate(self) -> float:
        return self._rate(self.must_parse_passed, self.must_parse_total)

    @property
    def must_reject_rate(self) -> float:
        return self._rate(self.must_reject_caught, self.must_reject_total)


def load_reference(root: pathlib.Path | None = None) -> list[ReferenceCase]:
    """Read every case under `corpus/reference/`, or from a given root.

    Validation is strict on purpose. A mistyped `must-parse` that silently
    loads as something else would make the corpus agree with a mistake, which
    is the failure mode this whole corpus exists to prevent. `root` is a
    parameter rather than a monkeypatchable default so tests can point it at
    fixtures without touching the committed corpus.
    """
    root = REFERENCE_DIR if root is None else root
    if not root.is_dir():
        raise ReferenceError(f"no reference corpus at {root}")

    cases: list[ReferenceCase] = []
    origins: dict[str, str] = {}
    for path in sorted([*root.rglob("*.yml"), *root.rglob("*.yaml")]):
        file_cases = _load_file(path)
        by_id = {c.id: c for c in file_cases}
        for case in file_cases:
            if case.id in origins:
                raise ReferenceError(
                    f"{path.name}: duplicate case id {case.id!r}, "
                    f"already defined in {origins[case.id]}"
                )
            origins[case.id] = path.name
            if case.from_id:
                if case.from_id not in by_id:
                    raise ReferenceError(
                        f"{path.name}: case {case.id!r} has `from: {case.from_id}`, "
                        "which is not a case in the same file"
                    )
                if by_id[case.from_id].verdict != MUST_PARSE:
                    raise ReferenceError(
                        f"{path.name}: case {case.id!r} has `from: {case.from_id}`, "
                        "which is not a must-parse case"
                    )
            cases.append(case)
    return cases


def _load_file(path: pathlib.Path) -> list[ReferenceCase]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, ValueError) as error:
        # ValueError covers YAML resolvers that build values eagerly, such as
        # an impossible date in `checked: 2026-13-45`.
        raise ReferenceError(f"{path.name}: not valid YAML: {error}") from error
    if not isinstance(raw, dict):
        raise ReferenceError(f"{path.name}: expected a mapping at the top level")
    unknown = sorted(set(raw) - _FILE_KEYS)
    if unknown:
        raise ReferenceError(f"{path.name}: unknown keys {unknown}")
    for key in ("statement", "doc", "syntax", "checked", "cases"):
        if key not in raw:
            raise ReferenceError(f"{path.name}: missing required key {key!r}")
    statement, doc, syntax, cases = (
        raw["statement"], raw["doc"], raw["syntax"], raw["cases"]
    )
    for label, value in (("statement", statement), ("doc", doc), ("syntax", syntax)):
        if not isinstance(value, str) or not value.strip():
            raise ReferenceError(f"{path.name}: {label} must be a non-empty string")
    if not doc.startswith(("http://", "https://")):
        raise ReferenceError(f"{path.name}: doc must be a URL, got {doc!r}")
    checked = _checked_date(path, raw["checked"])
    if not isinstance(cases, list) or not cases:
        raise ReferenceError(f"{path.name}: cases must be a non-empty list")
    file_cases = [_load_case(path, case, statement, doc, checked) for case in cases]
    block = " ".join(syntax.split()).casefold()
    for case in file_cases:
        quoted = " ".join(case.omits.split()).casefold()
        if case.verdict == MUST_REJECT and quoted not in block:
            raise ReferenceError(
                f"{path.name}: case {case.id!r}: omits {case.omits!r} does not "
                "appear in the syntax block"
            )
    return file_cases


def _checked_date(path: pathlib.Path, value: object) -> str:
    """The date the page was read, as ISO text.

    YAML resolves a bare `2026-09-19` to a date and a timestamp to a datetime,
    so accept what YAML hands back rather than demanding a quoted string. Any
    other shape is a transcription error worth naming.
    """
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        try:
            return datetime.date.fromisoformat(value.strip()).isoformat()
        except ValueError:
            pass
    raise ReferenceError(
        f"{path.name}: checked must be a YYYY-MM-DD date, got {value!r}"
    )


def _load_case(
    path: pathlib.Path, raw: object, statement: str, doc: str, checked: str
) -> ReferenceCase:
    if not isinstance(raw, dict):
        raise ReferenceError(f"{path.name}: every case must be a mapping")
    label = f"{path.name}: case {raw['id']!r}" if "id" in raw else path.name
    unknown = sorted(set(raw) - _CASE_KEYS)
    if unknown:
        raise ReferenceError(f"{label}: unknown keys {unknown}")
    for key in ("id", "verdict", "anchor", "sql"):
        if key not in raw:
            raise ReferenceError(f"{label}: missing required key {key!r}")
    case_id, verdict, anchor, sql = raw["id"], raw["verdict"], raw["anchor"], raw["sql"]
    if not isinstance(case_id, str) or not case_id.strip():
        raise ReferenceError(f"{path.name}: case id must be a non-empty string")
    label = f"{path.name}: case {case_id!r}"
    if verdict not in VERDICTS:
        raise ReferenceError(f"{label}: verdict must be one of {VERDICTS}, got {verdict!r}")
    if not isinstance(anchor, str) or not anchor.strip():
        raise ReferenceError(f"{label}: anchor must be a non-empty string")
    if not isinstance(sql, str) or not sql.strip():
        raise ReferenceError(f"{label}: sql must be a non-empty string")
    from_id = raw.get("from", "")
    if not isinstance(from_id, str):
        raise ReferenceError(f"{label}: from must be a case id")
    if verdict == MUST_REJECT and not from_id:
        raise ReferenceError(
            f"{label}: a must-reject case needs `from:`, the full-form sibling "
            "whose production it partially omits"
        )
    if verdict == MUST_PARSE and from_id:
        raise ReferenceError(f"{label}: only a must-reject case may carry `from:`")
    omits = raw.get("omits", "")
    if not isinstance(omits, str):
        raise ReferenceError(f"{label}: omits must be a string")
    if verdict == MUST_REJECT and not omits.strip():
        raise ReferenceError(
            f"{label}: a must-reject case needs `omits:`, the production text "
            "it leaves out"
        )
    if "note" in raw and not isinstance(raw["note"], str):
        raise ReferenceError(f"{label}: note must be a string")
    return ReferenceCase(
        id=case_id,
        verdict=verdict,
        sql=sql.strip(),
        doc=doc,
        anchor=anchor,
        statement=statement,
        checked=checked,
        from_id=from_id,
        omits=omits,
        note=raw.get("note", ""),
    )


def run_reference_corpus(
    runner: Runner, cases: list[ReferenceCase] | None = None
) -> ReferenceReport:
    """Check every case, then the controls that make the result trustworthy."""
    report = ReferenceReport()
    for case in load_reference() if cases is None else cases:
        report.results.append(_check(runner, case))
    report.controls = [_check(runner, case) for case in CONTROLS]
    return report


def _check(runner: Runner, case: ReferenceCase) -> CaseResult:
    result = runner.check(case.sql, f"<reference:{case.id}>")
    return CaseResult(case, result.ok, result.message, result.line)


def reference_payload(report: ReferenceReport) -> dict:
    """Serialise the report for `corpus/reports/*.json`.

    Per-case results rather than totals alone, so `compare_baseline.py` can
    tell a case that regressed from one that is merely new: adding coverage
    that fails is the corpus working, while a case flipping from conforming
    to not is a regression.
    """
    return {
        "controls_ok": report.controls_ok,
        "must_parse": {
            "total": report.must_parse_total,
            "passed": report.must_parse_passed,
            "rate": report.must_parse_rate,
        },
        "must_reject": {
            "total": report.must_reject_total,
            "caught": report.must_reject_caught,
            "informative": report.must_reject_informative,
            "vacuous": report.must_reject_vacuous,
            "rate": report.must_reject_rate,
        },
        "cases": [
            {
                "id": result.case.id,
                "verdict": result.case.verdict,
                "ok": result.conforms,
                "statement": result.case.statement,
                "doc": result.case.doc,
                "anchor": result.case.anchor,
                "message": None if result.conforms else result.message,
            }
            for result in report.results
        ],
    }


def write_reference_json(report: ReferenceReport, path: pathlib.Path) -> None:
    """Write the report on its own, for the standalone `reference` command."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reference": reference_payload(report)}, indent=2))


def format_reference_report(report: ReferenceReport) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("REFERENCE -- cases transcribed from the Databricks SQL reference")
    lines.append("=" * 78)
    lines.append(
        f"must-parse   {report.must_parse_passed:3d}/{report.must_parse_total:<3d} "
        f"{report.must_parse_rate:6.1f}%  documented syntax the parser accepts"
    )
    lines.append(
        f"must-reject  {report.must_reject_caught:3d}/{report.must_reject_total:<3d} "
        f"{report.must_reject_rate:6.1f}%  partial forms the parser rejects "
        f"({report.must_reject_informative} informative, "
        f"{report.must_reject_vacuous} vacuous)"
    )
    lines.append(f"controls:    {'ok' if report.controls_ok else 'FAILED'}")
    if report.failures:
        lines.append("")
        lines.append("Cases that do not match the reference:")
        for result in report.failures:
            outcome = (
                "accepted but must be rejected"
                if result.case.verdict == MUST_REJECT
                else "not parsed"
            )
            lines.append(f"  [{outcome}] {result.case.id}")
            lines.append(f"      {result.case.doc}{result.case.anchor}")
            if result.message:
                lines.append(f"      {result.message[:100]}")
    vacuous = [
        r for r in report.of(MUST_REJECT)
        if r.conforms and not report.sibling_parsed(r)
    ]
    if vacuous:
        lines.append("")
        lines.append("Vacuous rejections -- the full form does not parse either,")
        lines.append("so rejection proves nothing about the partial form:")
        for result in vacuous:
            lines.append(f"  {result.case.id}")
    if not report.controls_ok:
        lines.append("")
        lines.append("CONTROL FAILED -- the numbers above are not trustworthy:")
        for result in report.controls:
            if not result.conforms:
                lines.append(f"  {result.case.id}: {result.message or 'parsed'}")
    return "\n".join(lines)


def format_reference_gaps(report: ReferenceReport) -> str:
    """The failing cases as paste-ready `docs/gaps.md` entries.

    The triage step after a run is manual copying; this is that step with the
    transcription already attached -- case id, verdict, the doc link, and a
    one-line repro. Only failures appear. A vacuous rejection is not a
    failure, it is a check whose proof is not in yet, and printing it as a gap
    would send someone upstream with a repro that parses.
    """
    lines: list[str] = []
    lines.append(f"reference gaps: {len(report.failures)}")
    for result in report.failures:
        case = result.case
        lines.append("")
        lines.append(f"## {case.id}")
        if case.verdict == MUST_REJECT:
            lines.append("partial form accepted by the parser")
            lines.append(f"from: {case.from_id}")
            lines.append(f"omits: {case.omits}")
        else:
            lines.append("documented syntax rejected by the parser")
        lines.append(f"doc: {case.doc}{case.anchor}")
        lines.append(f"sql: {' '.join(case.sql.split())}")
        if result.message:
            lines.append(f"message: {result.message.splitlines()[0]}")
    if report.must_reject_vacuous:
        lines.append("")
        lines.append(
            f"vacuous ({report.must_reject_vacuous}) -- not gaps yet, "
            "the full form does not parse either:"
        )
        for result in report.of(MUST_REJECT):
            if result.conforms and not report.sibling_parsed(result):
                lines.append(f"  {result.case.id}")
    if not report.controls_ok:
        lines.append("")
        lines.append("CONTROL FAILED -- do not trust this list")
    return "\n".join(lines)
