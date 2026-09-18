"""Measure parser accuracy against the corpus.

Reports two numbers that mean different things:

    recall      -- share of valid SQL we accept. A miss here is a FALSE
                   POSITIVE: CI blocks a merge request that was fine. This is
                   the number that decides whether the tool is deployable.
    rejection   -- share of guaranteed-invalid SQL we reject. A miss here is a
                   FALSE NEGATIVE: broken SQL sails through review.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..parser import ParseOptions, parse_text
from .mutate import GUARANTEED, mutate_corpus
from .sources import REMOTE_SOURCES, Source

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = REPO_ROOT / "corpus" / "cache"
REPORT_DIR = REPO_ROOT / "corpus" / "reports"

# Heuristics for SQL that is not Databricks at all. Team repos accumulate
# T-SQL from source systems, and counting those as parser failures would
# understate the real recall.
TSQL_MARKERS = (
    re.compile(r"^\s*GO\s*$", re.M | re.I),
    re.compile(r"\bCREATE\s+PROCEDURE\b", re.I),
    re.compile(r"\bALTER\s+PROCEDURE\b", re.I),
    re.compile(r"\[\w+\]\.\[\w+\]"),          # [dbo].[table]
    re.compile(r"\bN'[^']*'"),                 # N'unicode literal'
    re.compile(r"\b(NVARCHAR|UNIQUEIDENTIFIER|DATETIME2|IDENTITY)\b", re.I),
    re.compile(r"@\w+\s+(AS\s+)?(INT|VARCHAR|NVARCHAR|BIT|DATETIME)", re.I),
    re.compile(r"\bINFORMATION_SCHEMA\b", re.I),
    re.compile(r"\bDB_NAME\s*\(", re.I),
)


def looks_like_tsql(text: str) -> bool:
    return sum(bool(p.search(text)) for p in TSQL_MARKERS) >= 1


@dataclass
class FileResult:
    path: str
    source: str
    ok: bool
    statements: int
    errors: list[str] = field(default_factory=list)
    skipped_dialect: bool = False
    seconds: float = 0.0


@dataclass
class SourceReport:
    source: Source
    files: list[FileResult] = field(default_factory=list)

    @property
    def considered(self) -> list[FileResult]:
        return [f for f in self.files if not f.skipped_dialect]

    @property
    def passed(self) -> int:
        return sum(1 for f in self.considered if f.ok)

    @property
    def total(self) -> int:
        return len(self.considered)

    @property
    def skipped(self) -> int:
        return sum(1 for f in self.files if f.skipped_dialect)

    @property
    def rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


def iter_sql_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*.sql") if p.is_file())


def run_source(
    source: Source,
    root: pathlib.Path,
    options: ParseOptions,
    skip_foreign_dialects: bool = True,
) -> SourceReport:
    report = SourceReport(source=source)
    for path in iter_sql_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if skip_foreign_dialects and source.name.startswith("local:") and looks_like_tsql(text):
            report.files.append(
                FileResult(str(path), source.name, ok=False, statements=0, skipped_dialect=True)
            )
            continue
        t0 = time.perf_counter()
        result = parse_text(text, options=options, path=str(path))
        elapsed = time.perf_counter() - t0
        report.files.append(
            FileResult(
                path=str(path),
                source=source.name,
                ok=result.ok,
                statements=result.statement_count,
                errors=[d.message for d in result.diagnostics],
                seconds=elapsed,
            )
        )
    return report


def run_valid_corpus(
    options: ParseOptions, local_dirs: list[str] | None = None
) -> list[SourceReport]:
    from .sources import local_sources

    reports: list[SourceReport] = []
    for source in REMOTE_SOURCES:
        root = CACHE_DIR / source.name
        if not root.exists():
            continue
        reports.append(run_source(source, root, options))
    for source in local_sources(local_dirs or []):
        root = pathlib.Path(source.local_paths[0])
        if root.exists():
            reports.append(run_source(source, root, options))
    return reports


def run_mutation_corpus(
    reports: list[SourceReport], options: ParseOptions, seed: int = 0, limit: int = 2000
) -> dict:
    """Mutate SQL we successfully parsed, then check we now reject it."""
    seeds: list[tuple[str, str]] = []
    for report in reports:
        if report.source.expectation != "valid":
            continue
        for f in report.considered:
            if f.ok:
                text = pathlib.Path(f.path).read_text(encoding="utf-8", errors="replace")
                seeds.append((text, f.path))

    mutants = mutate_corpus(seeds, seed=seed, limit=limit)
    # Values are mixed: counts are ints, "tier" is a string label.
    by_kind: dict[str, dict[str, Any]] = collections.defaultdict(
        lambda: {"total": 0, "rejected": 0, "tier": ""}
    )
    escapes: list[dict] = []

    for m in mutants:
        result = parse_text(m.sql, options=options)
        entry = by_kind[m.kind]
        entry["tier"] = m.tier
        entry["total"] += 1
        if not result.ok:
            entry["rejected"] += 1
        elif m.tier == GUARANTEED:
            if len(escapes) < 25:
                escapes.append({"kind": m.kind, "origin": m.origin, "sql": m.sql[:200]})

    scored_total = sum(v["total"] for v in by_kind.values() if v["tier"] == GUARANTEED)
    scored_rejected = sum(v["rejected"] for v in by_kind.values() if v["tier"] == GUARANTEED)
    return {
        "by_kind": dict(by_kind),
        "guaranteed_total": scored_total,
        "guaranteed_rejected": scored_rejected,
        "rejection_rate": (scored_rejected / scored_total * 100) if scored_total else 0.0,
        "escapes": escapes,
    }


def format_report(reports: list[SourceReport], mutation: dict | None) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("RECALL -- valid SQL we accept (a miss here blocks a good merge request)")
    lines.append("=" * 78)
    lines.append(f"{'source':28s} {'files':>6s} {'pass':>6s} {'rate':>7s} {'skip':>5s}  expectation")
    lines.append("-" * 78)

    grand_total = grand_pass = 0
    for r in sorted(reports, key=lambda r: r.source.name):
        if r.source.expectation == "valid":
            grand_total += r.total
            grand_pass += r.passed
        lines.append(
            f"{r.source.name:28s} {r.total:6d} {r.passed:6d} {r.rate:6.1f}% "
            f"{r.skipped:5d}  {r.source.expectation}"
        )
    lines.append("-" * 78)
    overall = (grand_pass / grand_total * 100) if grand_total else 0.0
    lines.append(f"{'TOTAL (valid sources only)':28s} {grand_total:6d} {grand_pass:6d} {overall:6.1f}%")

    failures = [f for r in reports for f in r.considered
                if not f.ok and r.source.expectation == "valid"]
    if failures:
        lines.append("")
        lines.append("Top failure messages on valid SQL:")
        counter = collections.Counter(
            re.sub(r"'[^']*'", "'...'", f.errors[0]) for f in failures if f.errors
        )
        for msg, n in counter.most_common(12):
            lines.append(f"  {n:4d}  {msg[:68]}")
        lines.append("")
        lines.append("Example failing files:")
        for f in failures[:8]:
            rel = f.path.replace(str(REPO_ROOT) + "/", "")
            lines.append(f"  {rel}")
            if f.errors:
                lines.append(f"      {f.errors[0][:66]}")

    if mutation:
        lines.append("")
        lines.append("=" * 78)
        lines.append("REJECTION -- invalid SQL we catch (a miss here waves broken SQL through)")
        lines.append("=" * 78)
        lines.append(f"{'mutation kind':24s} {'tier':11s} {'total':>6s} {'caught':>7s} {'rate':>7s}")
        lines.append("-" * 78)
        for kind, v in sorted(mutation["by_kind"].items(), key=lambda kv: kv[1]["tier"]):
            rate = (v["rejected"] / v["total"] * 100) if v["total"] else 0.0
            lines.append(
                f"{kind:24s} {v['tier']:11s} {v['total']:6d} {v['rejected']:7d} {rate:6.1f}%"
            )
        lines.append("-" * 78)
        lines.append(
            f"{'SCORED (guaranteed only)':24s} {'':11s} "
            f"{mutation['guaranteed_total']:6d} {mutation['guaranteed_rejected']:7d} "
            f"{mutation['rejection_rate']:6.1f}%"
        )
        if mutation["escapes"]:
            lines.append("")
            lines.append("Invalid SQL that parsed anyway (false negatives):")
            for e in mutation["escapes"][:6]:
                lines.append(f"  [{e['kind']}] {e['sql'][:64]!r}")
    return "\n".join(lines)


def write_json(
    reports: list[SourceReport],
    mutation: dict | None,
    path: pathlib.Path,
    include_local: bool = False,
) -> None:
    """Write the report as JSON.

    Local sources are excluded by default. The committed baseline is a shared
    reference that anyone can reproduce from the public Spark corpus, and a
    private repo's absolute paths, table names and column names have no place
    in it. Pass include_local=True for a local-only report you do not commit.
    """

    def public(report: SourceReport) -> bool:
        return include_local or not report.source.name.startswith("local:")

    def relative(p: str) -> str:
        try:
            return str(pathlib.Path(p).relative_to(REPO_ROOT))
        except ValueError:
            return pathlib.Path(p).name

    payload = {
        "sources": [
            {
                "name": r.source.name,
                "expectation": r.source.expectation,
                "total": r.total,
                "passed": r.passed,
                "skipped_dialect": r.skipped,
                "rate": r.rate,
                "failures": [
                    {"path": relative(f.path), "errors": f.errors[:3]}
                    for f in r.considered
                    if not f.ok
                ],
            }
            for r in reports
            if public(r)
        ],
        "mutation": _public_mutation(mutation, include_local),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _public_mutation(mutation: dict | None, include_local: bool) -> dict | None:
    """Strip mutation escapes, which quote SQL and name its source file."""
    if mutation is None or include_local:
        return mutation
    redacted = dict(mutation)
    escapes = redacted.get("escapes") or []
    redacted["escapes"] = [
        {"kind": e.get("kind"), "origin": pathlib.Path(str(e.get("origin", ""))).name}
        for e in escapes
    ]
    return redacted
