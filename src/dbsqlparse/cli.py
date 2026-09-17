"""Command line entry point: `dbsqlparse [files...]`.

Exit codes are chosen for CI:

    0  nothing wrong, or only warnings
    1  at least one error (a parse failure, or a rule set to severity "error")
    2  the tool could not run -- bad config, missing file

Separating 1 from 2 matters in a pipeline: a broken config should not look
like a SQL problem.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from .linter import LintResult, lint_file, lint_text
from .parser import ParseOptions
from .rules import Config, ConfigError, describe_rules, find_config, load_config, load_for_path

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2


def collect_paths(inputs: list[str]) -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []
    for raw in inputs:
        p = pathlib.Path(raw)
        if p.is_dir():
            paths.extend(sorted(p.rglob("*.sql")))
        else:
            paths.append(p)
    return paths


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="dbsqlparse",
        description="Parse and lint Databricks SQL. Rules are configured, never assumed.",
    )
    ap.add_argument("paths", nargs="*", help="SQL files or directories ('-' for stdin)")
    ap.add_argument(
        "--config",
        metavar="FILE",
        help="TOML config to use. Default: nearest .dbsqlparse.toml or "
             "pyproject.toml [tool.dbsqlparse], searching upward from each file",
    )
    ap.add_argument(
        "--no-config",
        action="store_true",
        help="ignore any config file and check syntax only",
    )
    ap.add_argument(
        "--list-rules",
        action="store_true",
        help="print every available rule with its options, then exit",
    )
    ap.add_argument(
        "--ansi-keywords",
        action="store_true",
        help="enforce ANSI reserved keywords. Stricter: rejects things like "
             "`SELECT * FROM t WHERE`, which Spark otherwise reads as a table alias",
    )
    ap.add_argument(
        "--double-quoted-identifiers",
        action="store_true",
        help='treat "foo" as an identifier rather than a string literal',
    )
    ap.add_argument(
        "--quiet", action="store_true", help="print diagnostics only, no summary"
    )
    return ap


def _resolve_config(args, for_path: pathlib.Path | None) -> Config:
    if args.no_config:
        return Config()
    if args.config:
        path = pathlib.Path(args.config)
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        return load_config(path)
    if for_path is None:
        return Config()
    return load_for_path(for_path)


def _report(result: LintResult) -> None:
    for message in result.messages():
        print(message)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        print(describe_rules())
        print("Enable rules in .dbsqlparse.toml. See examples/ for complete configs.")
        return EXIT_OK

    override = ParseOptions(
        ansi_reserved_keywords=args.ansi_keywords,
        double_quoted_identifiers=args.double_quoted_identifiers,
    ) if (args.ansi_keywords or args.double_quoted_identifiers) else None

    # stdin
    if not args.paths or args.paths == ["-"]:
        try:
            config = _resolve_config(args, pathlib.Path.cwd())
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        result = lint_text(sys.stdin.read(), config=config, path="<stdin>", options=override)
        _report(result)
        return EXIT_VIOLATIONS if result.error_count else EXIT_OK

    paths = collect_paths(args.paths)
    if not paths:
        print("error: no SQL files found", file=sys.stderr)
        return EXIT_USAGE

    try:
        config = _resolve_config(args, paths[0])
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    files_with_errors = 0
    total_errors = 0
    total_warnings = 0
    unparseable = 0

    for path in paths:
        if not path.exists():
            print(f"{path}: error: no such file", file=sys.stderr)
            files_with_errors += 1
            total_errors += 1
            continue
        result = lint_file(path, config=config, options=override)
        _report(result)
        if not result.parsed:
            unparseable += 1
        errors = result.error_count
        warnings = sum(1 for v in result.violations if v.severity != "error")
        total_errors += errors
        total_warnings += warnings
        if errors:
            files_with_errors += 1

    if not args.quiet:
        # Diagnostics go to stdout and the summary to stderr, which are
        # buffered separately; without this flush the summary can appear
        # above the findings it is summarising.
        sys.stdout.flush()
        summary = [f"checked {len(paths)} file(s)"]
        if config.source:
            summary.append(f"config: {config.source}")
        elif not args.no_config:
            summary.append("no config found -- syntax only")
        print("\n" + ", ".join(summary), file=sys.stderr)
        if total_errors or total_warnings:
            print(
                f"{total_errors} error(s), {total_warnings} warning(s) "
                f"in {files_with_errors} file(s)",
                file=sys.stderr,
            )
            if unparseable:
                # These files were not rule-checked at all; say so rather than
                # letting a clean rule report imply they passed.
                print(
                    f"note: {unparseable} file(s) failed to parse and were not "
                    f"checked against any rule",
                    file=sys.stderr,
                )
        else:
            print("no problems found", file=sys.stderr)

    return EXIT_VIOLATIONS if total_errors else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
