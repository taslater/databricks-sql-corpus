"""Differential triage: SQLFluff against an independent second parser.

`make gaps` answers "what fails"; this answers "which failures does another
parser disagree about". The second parser is sqlglot by default -- an
independent implementation of a Databricks dialect, and the parser Databricks
Labs UCX itself uses. It is advisory by design and by policy:

  * Nothing here feeds `baseline.json`, recall, rejection or
    `compare_baseline.py`. The docs-derived reference corpus is the oracle; a
    second parser is a witness.
  * sqlglot is deliberately lenient ("a transpiler, not a validator"), so its
    *rejections* are the signal and its *acceptances* are not. It accepts
    `SELECT a,, b FROM t`, one of mutate.py's GUARANTEED shapes; a low
    rejection score from it would measure the wrong thing. That is why it has
    a runner and no scored metric.
  * The known-bad control runs in every batch, per parser: `SELECT a FROM
    ((t;` must fail in both or the report is not trustworthy.

Categories for corpus files, where "primary" is SQLFluff and "second" is the
comparison parser:

    primary-only   only SQLFluff rejects the file -> candidate SQLFluff gap,
                   rank first
    second-only    only the second parser rejects -> candidate gap in it
    both-fail      neither parses -> de-prioritised; likely non-SQL or
                   unsupported by both
    both-pass      agreement; not reported

For reference cases the same crossing runs per case id, and the vacuity rule
is kept: a must-reject case only proves the second parser's rejection is
meaningful when the second parser can parse the full-form sibling.
"""
from __future__ import annotations

import collections
import json
import pathlib
from dataclasses import dataclass, field

from .constructs import construct
from .harness import FileResult, SourceReport, run_valid_corpus
from .reference import (
    CONTROLS,
    MUST_PARSE,
    MUST_REJECT,
    ReferenceReport,
    run_reference_corpus,
)
from .runners import Runner

# Corpus categories.
PRIMARY_ONLY = "primary-only"
SECOND_ONLY = "second-only"
BOTH_FAIL = "both-fail"
BOTH_PASS = "both-pass"

# Reference-case categories.
CASE_PRIMARY_GAP = "primary-gap"
CASE_SECOND_GAP = "second-gap"
CASE_BOTH_GAP = "both-gap"
CASE_OVER_ACCEPT = "over-acceptance"
CASE_BOTH_ACCEPT = "both-accept"
CASE_SECOND_LENIENT = "second-lenient"
CASE_CONFORMING = "conforming"

# Sections in the report, in the order they are printed.
FILE_SECTIONS = (
    (PRIMARY_ONLY, "only {primary} rejects these; {second} parses them -- "
                   "candidate {primary} gaps, rank first"),
    (SECOND_ONLY, "only {second} rejects these; {primary} parses them -- "
                  "candidate {second} gaps"),
    (BOTH_FAIL, "neither parses these -- de-prioritised"),
)

CASE_SECTIONS = (
    (CASE_PRIMARY_GAP, "{primary} rejects documented syntax that {second} "
                       "parses -- rank first"),
    (CASE_OVER_ACCEPT, "{primary} accepts a form the reference does not "
                       "define and {second} rejects it"),
    (CASE_SECOND_GAP, "{second} rejects documented syntax that {primary} "
                      "parses -- candidate {second} gap"),
    (CASE_BOTH_GAP, "documented syntax neither parser accepts"),
    (CASE_BOTH_ACCEPT, "forms the reference does not define that both "
                       "parsers accept -- review the transcription"),
)


@dataclass(frozen=True)
class ControlResult:
    parser: str
    case_id: str
    ok: bool
    message: str | None = None


@dataclass(frozen=True)
class FileTriage:
    path: str
    source: str
    construct: str
    category: str
    message: str | None = None
    other_message: str | None = None


@dataclass(frozen=True)
class CaseTriage:
    case_id: str
    verdict: str
    category: str
    statement: str
    doc: str
    anchor: str
    sql: str
    message: str | None = None
    other_message: str | None = None
    # For must-reject cases: True when the second parser parses the full-form
    # sibling, so its rejection of the partial form has teeth.
    informative: bool = True


@dataclass
class DifferentialReport:
    primary: str
    second: str
    versions: dict[str, str] = field(default_factory=dict)
    controls: list[ControlResult] = field(default_factory=list)
    files: list[FileTriage] = field(default_factory=list)
    cases: list[CaseTriage] = field(default_factory=list)
    files_compared: int = 0

    @property
    def controls_ok(self) -> bool:
        return all(c.ok for c in self.controls)

    def files_of(self, category: str) -> list[FileTriage]:
        return [f for f in self.files if f.category == category]

    def cases_of(self, category: str) -> list[CaseTriage]:
        return [c for c in self.cases if c.category == category]


def classify_file(primary_ok: bool, second_ok: bool) -> str:
    if primary_ok and second_ok:
        return BOTH_PASS
    if primary_ok:
        return SECOND_ONLY
    if second_ok:
        return PRIMARY_ONLY
    return BOTH_FAIL


def classify_case(verdict: str, primary_parsed: bool, second_parsed: bool) -> str:
    if verdict == MUST_PARSE:
        if primary_parsed and second_parsed:
            return CASE_CONFORMING
        if primary_parsed:
            return CASE_SECOND_GAP
        if second_parsed:
            return CASE_PRIMARY_GAP
        return CASE_BOTH_GAP
    # must-reject: conforming means both reject; the interesting failures are
    # the ones where the primary accepts.
    if primary_parsed and second_parsed:
        return CASE_BOTH_ACCEPT
    if primary_parsed:
        return CASE_OVER_ACCEPT
    if second_parsed:
        return CASE_SECOND_LENIENT
    return CASE_CONFORMING


def triage_files(
    primary_reports: list[SourceReport],
    second_reports: list[SourceReport],
    dialect: str = "databricks",
) -> list[FileTriage]:
    other: dict[str, FileResult] = {
        f.path: f for r in second_reports for f in r.considered
    }
    out: list[FileTriage] = []
    for report in primary_reports:
        for f in report.considered:
            counterpart = other.get(f.path)
            if counterpart is None:
                continue
            category = classify_file(f.ok, counterpart.ok)
            if category == BOTH_PASS:
                continue
            out.append(
                FileTriage(
                    path=f.path,
                    source=report.source.name,
                    construct=construct(f, dialect),
                    category=category,
                    message=f.errors[0] if f.errors else None,
                    other_message=counterpart.errors[0] if counterpart.errors else None,
                )
            )
    return out


def triage_cases(
    primary_report: ReferenceReport, second_report: ReferenceReport
) -> list[CaseTriage]:
    by_id = {r.case.id: r for r in second_report.results}
    out: list[CaseTriage] = []
    for result in primary_report.results:
        counterpart = by_id.get(result.case.id)
        if counterpart is None:
            continue
        category = classify_case(
            result.case.verdict, result.parsed, counterpart.parsed
        )
        if category == CASE_CONFORMING:
            continue
        informative = True
        if result.case.verdict == MUST_REJECT and result.case.from_id:
            sibling = by_id.get(result.case.from_id)
            if sibling is not None and not sibling.parsed:
                informative = False
        out.append(
            CaseTriage(
                case_id=result.case.id,
                verdict=result.case.verdict,
                category=category,
                statement=result.case.statement,
                doc=result.case.doc,
                anchor=result.case.anchor,
                sql=result.case.sql,
                message=result.message,
                other_message=counterpart.message,
                informative=informative,
            )
        )
    return out


def _run_controls(runners: tuple[Runner, ...]) -> list[ControlResult]:
    out: list[ControlResult] = []
    for runner in runners:
        for case in CONTROLS:
            result = runner.check(case.sql, f"<control:{case.id}>")
            conformed = result.ok if case.verdict == MUST_PARSE else not result.ok
            out.append(ControlResult(runner.name, case.id, conformed, result.message))
    return out


def run_differential(
    primary: Runner,
    second: Runner,
    local_dirs: list[str] | None = None,
) -> DifferentialReport:
    """Run both parsers over the corpus and the reference, then join.

    The corpus and the reference are each run once per parser. Nothing here is
    scored; the returned report is advisory data for a human.
    """
    primary_reports = run_valid_corpus(primary, local_dirs)
    second_reports = run_valid_corpus(second, local_dirs)
    dialect = getattr(primary, "dialect", "databricks")
    return DifferentialReport(
        primary=primary.name,
        second=second.name,
        versions={primary.name: primary.version(), second.name: second.version()},
        controls=_run_controls((primary, second)),
        files=triage_files(primary_reports, second_reports, dialect),
        cases=triage_cases(
            run_reference_corpus(primary), run_reference_corpus(second)
        ),
        files_compared=sum(r.total for r in primary_reports),
    )


def _totals(files: list[FileTriage]) -> collections.Counter:
    return collections.Counter(f.category for f in files)


def format_differential(report: DifferentialReport, limit: int = 30) -> str:
    names = {
        "primary": report.primary,
        "second": report.second,
    }
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append(
        f"DIFFERENTIAL -- {report.primary} ({report.versions.get(report.primary, '?')}) "
        f"vs {report.second} ({report.versions.get(report.second, '?')})"
    )
    lines.append("ADVISORY ONLY -- a disagreement is a triage candidate, not a verdict.")
    lines.append("The docs-derived reference is the oracle; this is a second witness.")
    lines.append("=" * 78)
    lines.append(
        "controls: "
        + "; ".join(
            f"{parser} {'ok' if ok else 'FAILED'}"
            for parser, ok in _control_summary(report)
        )
        + "   (a FAILED control makes everything below untrustworthy)"
    )
    if not report.controls_ok:
        for control in report.controls:
            if not control.ok:
                lines.append(
                    f"  {control.parser}: {control.case_id} misbehaved "
                    f"({control.message or 'parsed'})"
                )

    totals = _totals(report.files)
    agreed = max(report.files_compared - len(report.files), 0)
    lines.append("")
    lines.append(
        f"corpus: {report.files_compared} files compared -- "
        f"{totals[PRIMARY_ONLY]} {report.primary}-only, "
        f"{totals[SECOND_ONLY]} {report.second}-only, "
        f"{totals[BOTH_FAIL]} both-fail, "
        f"{agreed} agreed"
    )

    for category, template in FILE_SECTIONS:
        section = [
            f for f in report.files if f.category == category
        ]
        if not section:
            continue
        lines.append("")
        lines.append(template.format(**names) + f"  [{len(section)}]")
        grouped: dict[str, list[FileTriage]] = collections.defaultdict(list)
        for f in section:
            grouped[f.construct].append(f)
        for label, entries in sorted(grouped.items(), key=lambda kv: -len(kv[1]))[:limit]:
            lines.append(f"  {len(entries):4d}  {label}")
            for entry in entries[:2]:
                lines.append(f"          {pathlib.Path(entry.path).name}")
                detail = entry.message if category == PRIMARY_ONLY else entry.other_message
                if detail:
                    lines.append(f"              {detail[:88]}")

    lines.append("")
    lines.append("REFERENCE -- cases transcribed from the Databricks SQL reference")
    if not report.cases:
        lines.append("  no divergences recorded")
    for category, template in CASE_SECTIONS:
        section = report.cases_of(category)
        if not section:
            continue
        lines.append("")
        lines.append(f"  {template.format(**names)}  [{len(section)}]")
        for case in section[:limit]:
            flag = ""
            if case.verdict == MUST_REJECT and not case.informative:
                flag = "  (vacuous: no full form to deviate from in this parser)"
            lines.append(f"      {case.case_id}{flag}")
            detail = case.message if category in (CASE_PRIMARY_GAP, CASE_BOTH_GAP) else case.other_message
            if detail:
                lines.append(f"          {detail[:88]}")
            lines.append(f"          {case.doc}{case.anchor}")
    lenient = report.cases_of(CASE_SECOND_LENIENT)
    if lenient:
        lines.append("")
        lines.append(
            f"  {report.second} accepted {len(lenient)} non-conforming form(s) that "
            f"{report.primary} rejects -- expected leniency, no action"
        )
    return "\n".join(lines)


def _control_summary(report: DifferentialReport) -> list[tuple[str, bool]]:
    by_parser: dict[str, bool] = {}
    for control in report.controls:
        by_parser[control.parser] = by_parser.get(control.parser, True) and control.ok
    return list(by_parser.items())


def differential_payload(report: DifferentialReport) -> dict:
    """Serialise for a triage artefact. Advisory: never merged into baseline."""
    totals = _totals(report.files)
    return {
        "advisory": True,
        "note": (
            "Second-parser triage only; the reference corpus is the oracle. "
            "A rejection by the second parser is a signal; an acceptance is not."
        ),
        "primary": report.primary,
        "second": report.second,
        "versions": report.versions,
        "controls_ok": report.controls_ok,
        "controls": [
            {
                "parser": c.parser,
                "case_id": c.case_id,
                "ok": c.ok,
                "message": c.message,
            }
            for c in report.controls
        ],
        "corpus": {
            "counts": {
                "primary_only": totals[PRIMARY_ONLY],
                "second_only": totals[SECOND_ONLY],
                "both_fail": totals[BOTH_FAIL],
            },
            "files": [
                {
                    "path": pathlib.Path(f.path).name,
                    "source": f.source,
                    "construct": f.construct,
                    "category": f.category,
                }
                for f in report.files
            ],
        },
        "reference": {
            "cases": [
                {
                    "id": c.case_id,
                    "verdict": c.verdict,
                    "category": c.category,
                    "informative": c.informative,
                    "doc": c.doc,
                    "anchor": c.anchor,
                    "sql": c.sql,
                }
                for c in report.cases
            ]
        },
    }


def write_differential_json(report: DifferentialReport, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(differential_payload(report), indent=2))
