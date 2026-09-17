"""CLI: python -m dbsqlparse.corpus [fetch|run]"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

from ..parser import ParseOptions
from . import fetch as fetch_mod
from .harness import REPORT_DIR, format_report, run_mutation_corpus, run_valid_corpus, write_json


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dbsqlparse.corpus", description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="download Spark's SQL test corpus")

    run = sub.add_parser("run", help="measure parser accuracy against the corpus")
    run.add_argument(
        "--local", action="append", default=[],
        help="extra local directory of team SQL (repeatable)",
    )
    run.add_argument(
        "--ansi-keywords", action="store_true",
        help="enforce ANSI reserved keywords (stricter; rejects `FROM t WHERE` as an alias)",
    )
    run.add_argument("--mutations", type=int, default=2000, help="mutation budget (0 to skip)")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--json", type=str, default=None, help="also write a JSON report here")

    args = ap.parse_args(argv)

    if args.command == "fetch":
        return fetch_mod.main()

    options = ParseOptions(ansi_reserved_keywords=args.ansi_keywords)

    t0 = time.perf_counter()
    reports = run_valid_corpus(options, local_dirs=args.local)
    if not reports:
        print("no corpus found -- run: python -m dbsqlparse.corpus fetch", file=sys.stderr)
        return 1

    mutation = None
    if args.mutations:
        mutation = run_mutation_corpus(reports, options, seed=args.seed, limit=args.mutations)
    elapsed = time.perf_counter() - t0

    print(format_report(reports, mutation))
    total_files = sum(r.total for r in reports)
    print(f"\nparsed {total_files} files in {elapsed:.1f}s")

    out = pathlib.Path(args.json) if args.json else REPORT_DIR / "latest.json"
    write_json(reports, mutation, out)
    print(f"json report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
