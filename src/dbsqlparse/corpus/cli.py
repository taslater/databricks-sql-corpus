"""CLI: python -m dbsqlparse.corpus [fetch|run|gaps]"""
from __future__ import annotations

import argparse
import collections
import functools
import pathlib
import re
import sys
import time

from . import fetch as fetch_mod
from .harness import (
    REPORT_DIR,
    format_report,
    run_mutation_corpus,
    run_valid_corpus,
    write_json,
)
from .reference import (
    MUST_REJECT,
    ReferenceError,
    ReferenceReport,
    format_reference_gaps,
    format_reference_report,
    reference_payload,
    run_reference_corpus,
    write_reference_json,
)
from .runners import get_runner


def _add_runner_args(p: argparse.ArgumentParser, local: bool = True) -> None:
    p.add_argument(
        "--runner", default="sqlfluff", choices=["sqlfluff", "sqruff", "both"],
        help="which parser to measure (default: sqlfluff)",
    )
    p.add_argument("--dialect", default="databricks")
    if local:
        p.add_argument(
            "--local", action="append", default=[],
            help="extra local directory of team SQL (repeatable)",
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dbsqlparse.corpus", description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="download the pinned public SQL corpus")

    run = sub.add_parser("run", help="measure a parser against the corpus")
    _add_runner_args(run)
    run.add_argument("--mutations", type=int, default=2000, help="mutation budget (0 to skip)")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--json", type=str, default=None, help="also write a JSON report here")

    gaps = sub.add_parser(
        "gaps", help="group the failures by construct -- the upstream work queue"
    )
    _add_runner_args(gaps)
    gaps.add_argument("--limit", type=int, default=40, help="how many groups to show")

    reference = sub.add_parser(
        "reference", help="check cases transcribed from the Databricks SQL reference"
    )
    _add_runner_args(reference, local=False)
    reference.add_argument(
        "--json", type=str, default=None, help="also write a JSON report here"
    )

    reference_gaps = sub.add_parser(
        "reference-gaps",
        help="print the reference divergences as paste-ready gaps.md entries",
    )
    _add_runner_args(reference_gaps, local=False)

    args = ap.parse_args(argv)

    if args.command == "fetch":
        return fetch_mod.main()

    names = ["sqlfluff", "sqruff"] if args.runner == "both" else [args.runner]

    if args.command == "gaps":
        return _gaps(names, args)
    if args.command == "reference":
        return _reference(names, args)
    if args.command == "reference-gaps":
        return _reference_gaps(names, args)

    exit_code = 0
    for name in names:
        runner = get_runner(name, dialect=args.dialect)
        t0 = time.perf_counter()
        reports = run_valid_corpus(runner, local_dirs=args.local)
        if not reports:
            print("no corpus found -- run: python -m dbsqlparse.corpus fetch", file=sys.stderr)
            return 1

        mutation = None
        if args.mutations:
            mutation = run_mutation_corpus(
                reports, runner, seed=args.seed, limit=args.mutations
            )
        elapsed = time.perf_counter() - t0

        if len(names) > 1:
            print(f"\n{'#' * 78}\n# {name}\n{'#' * 78}")
        print(format_report(reports, mutation))
        total_files = sum(r.total for r in reports)
        print(f"\nchecked {total_files} files in {elapsed:.1f}s with {name}")

        reference_report = _run_reference(runner)
        if reference_report is None:
            exit_code = 1
        else:
            if not reference_report.controls_ok:
                exit_code = 1
            print()
            print(format_reference_report(reference_report))

        if args.json or name == "sqlfluff":
            out = pathlib.Path(args.json) if args.json else REPORT_DIR / "latest.json"
            payload = reference_payload(reference_report) if reference_report else None
            write_json(reports, mutation, out, payload)
            print(f"json report: {out}")
    return exit_code


def _run_reference(runner) -> ReferenceReport | None:
    """Run the reference corpus, or report why it could not be read.

    A broken YAML file is a data error worth naming rather than a traceback,
    but it must not pass silently: the numbers it would have produced are
    exactly the ones the scraped corpus cannot see.
    """
    try:
        return run_reference_corpus(runner)
    except ReferenceError as error:
        print(f"reference corpus error: {error}", file=sys.stderr)
        return None


def _reference(names: list[str], args) -> int:
    """The doc-derived corpus on its own -- no fetched corpus required."""
    exit_code = 0
    for name in names:
        runner = get_runner(name, dialect=args.dialect)
        report = _run_reference(runner)
        if report is None:
            return 2
        if len(names) > 1:
            print(f"\n{'#' * 78}\n# {name}\n{'#' * 78}")
        print(format_reference_report(report))
        if not report.controls_ok:
            exit_code = 1
        if args.json or name == "sqlfluff":
            out = pathlib.Path(args.json) if args.json else REPORT_DIR / "reference.json"
            write_reference_json(report, out)
            print(f"json report: {out}")
    return exit_code


def _reference_gaps(names: list[str], args) -> int:
    """Only the divergences, shaped for `docs/gaps.md` -- no rates, no cases
    that conformed. The triage step of the reference workflow, automated."""
    exit_code = 0
    for name in names:
        runner = get_runner(name, dialect=args.dialect)
        report = _run_reference(runner)
        if report is None:
            return 2
        if len(names) > 1:
            print(f"\n{'#' * 78}\n# {name}\n{'#' * 78}")
        print(format_reference_gaps(report))
        if not report.controls_ok:
            exit_code = 1
    return exit_code


def _gaps(names: list[str], args) -> int:
    """Group failures by the source line that failed.

    A corpus run answers "how many"; this answers "which construct", which is
    the form the work actually takes upstream. Grouping by the failing line
    collapses twenty notebooks that all trip over the same statement into one
    entry.
    """
    groups: dict[str, list[str]] = collections.defaultdict(list)
    failed_paths: dict[str, set[str]] = {}

    for name in names:
        runner = get_runner(name, dialect=args.dialect)
        reports = run_valid_corpus(runner, local_dirs=args.local)
        if not reports:
            print("no corpus found -- run: python -m dbsqlparse.corpus fetch", file=sys.stderr)
            return 1
        failed: set[str] = set()
        for report in reports:
            if report.source.expectation != "valid":
                continue
            for f in report.considered:
                if f.ok:
                    continue
                failed.add(f.path)
                if name == names[0]:
                    groups[_construct(f, args.dialect)].append(f.path)
        failed_paths[name] = failed
        if name == names[0]:
            reference_report = _run_reference(runner)

    primary = names[0]
    print(f"{len(groups)} distinct failing constructs under {primary}\n")
    for construct, paths in sorted(groups.items(), key=lambda kv: -len(kv[1]))[: args.limit]:
        marker = ""
        if len(names) > 1:
            other = names[1]
            # Compare the FILES, not the construct label: the other parser may
            # fail the same file at a different line, which would look like
            # agreement if only the labels were compared. Both parsers failing
            # points at the SQL; only one failing points at that parser.
            also = sum(1 for p in paths if p in failed_paths[other])
            if also == 0:
                marker = f"  [{other}: parses all {len(paths)}]"
            elif also == len(paths):
                marker = f"  [{other}: also fails all]"
            else:
                marker = f"  [{other}: also fails {also}/{len(paths)}]"
        print(f"{len(paths):4d}  {construct}{marker}")
        for f in sorted({pathlib.Path(p).name for p in paths})[:3]:
            print(f"        {f}")

    print()
    print("REFERENCE -- cases transcribed from the Databricks SQL reference")
    if reference_report is None:
        return 1
    if not reference_report.controls_ok:
        print("  CONTROL FAILED -- the reference numbers are not trustworthy")
    failures = reference_report.failures
    if not failures:
        print("  no divergences")
    for result in failures[: args.limit]:
        kind = (
            "accepted partial form"
            if result.case.verdict == MUST_REJECT
            else "documented syntax rejected"
        )
        print(f"  {result.case.id}  [{kind}]")
        print(f"      {result.case.doc}{result.case.anchor}")
    return 0


@functools.lru_cache(maxsize=1)
def _keywords(dialect: str = "databricks") -> frozenset[str]:
    """Every keyword the dialect knows, used to tell syntax from identifiers."""
    from sqlfluff.core.dialects import dialect_selector

    d = dialect_selector(dialect)
    words: set[str] = set()
    for key in ("reserved_keywords", "unreserved_keywords"):
        try:
            words |= set(d.sets(key))
        except (KeyError, AttributeError):
            pass
    return frozenset(words)


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STRING = re.compile(r"""('[^']*'|"[^"]*")""")


def _normalise(line: str, dialect: str) -> str:
    """Replace identifiers and literals so the same construct groups together.

    Without this, three materialized views that fail on the same missing
    grammar appear as three separate findings purely because the table names
    differ. Keywords come from the dialect under test rather than a hand-kept
    list, so this stays right as the dialect grows.
    """
    # A comment's prose is never the construct that failed. Collapsing to the
    # marker plus its first word groups every `-- MAGIC` line together, which
    # is the actual finding.
    if line.startswith("--"):
        head = line.split()[:2]
        return " ".join(head) + (" ..." if len(line.split()) > 2 else "")
    kw = _keywords(dialect)
    line = _STRING.sub("'...'", line)
    return _IDENT.sub(
        lambda m: m.group(0) if m.group(0).upper() in kw else "<id>", line
    )


def _construct(f, dialect: str = "databricks") -> str:
    """The failing source line, normalised enough to group on."""
    try:
        lines = pathlib.Path(f.path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return f.errors[0] if f.errors else "unknown"
    if f.line and 0 < f.line <= len(lines):
        raw = lines[f.line - 1].strip()
        if raw:
            return _normalise(raw, dialect)[:88]
    return f.errors[0][:88] if f.errors else "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
