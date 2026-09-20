"""Valid-variant probes: generate SQL that MUST parse, and check that it does.

Discovery only, like the fixture probe -- candidates are triaged against the
Databricks SQL reference before anything is queued. Two modes:

  keywords  -- substitute every dialect keyword into ordinary identifier
               positions (column, alias, table name, DDL name) and require
               SQLFluff to keep parsing. Databricks "does not formally
               disallow any specific literals from being used as identifiers",
               so a rejection is a candidate false positive of the kind that
               `SELECT * FROM stream` turned out to be. The doc's alias-only
               exception list and the words it marks special in expressions
               are excluded.
  roundtrip -- parse corpus SQL with sqlglot, regenerate it in the databricks
               dialect, and ask SQLFluff to parse the regenerated form. The
               generator is not an oracle: it can emit sqlglot-flavoured text
               the engine would reject, so every disagreement needs a docs
               read. Statements sqlglot only accepts as an opaque `Command`
               are skipped -- that is not a parse.

Both modes assert a known-bad and a known-good control before reporting, for
the same reason every other probe here does.

    .venv-main/bin/python scripts/fuzz_variants.py keywords
    .venv-main/bin/python scripts/fuzz_variants.py roundtrip --limit-files 200
"""
from __future__ import annotations

import argparse
import collections

# The [reserved words reference] says these cannot be used as unquoted table
# aliases, so the alias context is skipped for them.
ALIAS_RESERVED = {
    "ANTI", "CROSS", "EXCEPT", "FULL", "INNER", "INTERSECT", "JOIN", "LATERAL",
    "LEFT", "MASK", "MINUS", "NATURAL", "ON", "RIGHT", "SEMI", "UNION", "USING",
}
# The same page marks these special within expressions; the docs recommend
# backticks, so requiring them to parse unquoted would test the wrong thing.
SPECIAL_IN_EXPRESSIONS = {"NULL", "DEFAULT", "TRUE", "FALSE", "LATERAL"}

CONTEXTS = {
    "column": "SELECT {kw} FROM t",
    "alias": "SELECT a AS {kw} FROM t",
    "table": "SELECT * FROM {kw}",
    "ddl": "CREATE TABLE {kw} (a INT)",
}


def _controls(runner) -> bool:
    """Known-good must parse; known-bad must not. Report if either fails."""
    good = runner.check("SELECT 1", "<control:known-good>")
    bad = runner.check("SELECT a FROM ((t;", "<control:known-bad>")
    ok = good.ok and not bad.ok
    print(f"controls: known-good {'ok' if good.ok else 'FAILED'}, "
          f"known-bad {'ok' if not bad.ok else 'FAILED'}")
    return ok


def keywords_mode(args) -> int:
    from dbsqlparse.corpus.constructs import keywords
    from dbsqlparse.corpus.runners import SqlFluffRunner

    runner = SqlFluffRunner(dialect=args.dialect)
    if not _controls(runner):
        return 1

    words = sorted(
        w for w in keywords(args.dialect)
        if w.isascii() and w.isidentifier() and w.upper() not in SPECIAL_IN_EXPRESSIONS
    )
    print(f"keywords: {len(words)} checked in up to {len(CONTEXTS)} contexts each")

    failures: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for word in words:
        for context, template in CONTEXTS.items():
            if context == "alias" and word.upper() in ALIAS_RESERVED:
                continue
            sql = template.format(kw=word)
            result = runner.check(sql, f"<keyword:{word}:{context}>")
            if not result.ok:
                failures[word].append((context, str(result.message)[:90]))

    print(f"\n{len(failures)} keyword(s) rejected in at least one identifier position")
    print(f"{sum(len(v) for v in failures.values())} failing shapes total\n")
    for word, entries in sorted(failures.items(), key=lambda kv: -len(kv[1])):
        print(f"{len(entries)}  {word}")
        for context, message in entries:
            print(f"       {context:6s} {CONTEXTS[context].format(kw=word)}")
            print(f"              {message}")
    return 0


def roundtrip_mode(args) -> int:
    import logging

    import sqlglot
    from sqlglot import exp
    from sqlglot.errors import ErrorLevel, SqlglotError

    # Same quietening as SqlglotRunner: the fallback warning is expected.
    logging.getLogger("sqlglot").setLevel(logging.ERROR)

    from dbsqlparse.corpus.constructs import normalise
    from dbsqlparse.corpus.harness import CACHE_DIR, looks_like_json
    from dbsqlparse.corpus.runners import SqlFluffRunner
    from dbsqlparse.corpus.sources import REMOTE_SOURCES

    runner = SqlFluffRunner(dialect=args.dialect)
    if not _controls(runner):
        return 1

    candidates: list[tuple[str, str, str]] = []
    checked = skipped = 0
    for source in REMOTE_SOURCES:
        if source.expectation != "valid":
            continue
        root = CACHE_DIR / source.name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.sql"))[: args.limit_files or None]:
            text = path.read_text(encoding="utf-8", errors="replace")
            if looks_like_json(text):
                continue
            try:
                expressions = sqlglot.parse(
                    text, read=args.dialect, error_level=ErrorLevel.RAISE
                )
            except SqlglotError:
                continue
            # parse() can hand back None for an empty segment; a file with any
            # Command in it is a fallback, not a parse, so it is skipped.
            expressions = [e for e in expressions if e is not None]
            if not expressions or any(
                isinstance(e, exp.Command) for e in expressions
            ):
                skipped += 1
                continue
            generated = ";\n".join(e.sql(dialect=args.dialect) for e in expressions)
            checked += 1
            result = runner.check(generated, f"<roundtrip:{path.name}>")
            if result.ok:
                continue
            line = result.line or 1
            lines = generated.splitlines()
            raw = lines[line - 1] if 0 < line <= len(lines) else lines[0]
            candidates.append(
                (normalise(raw.strip(), args.dialect), path.name, str(result.message)[:90])
            )

    print(f"round-tripped {checked} file(s); skipped {skipped} as Command-fallback")
    grouped: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for label, name, message in candidates:
        grouped[label].append((name, message))
    print(f"{len(candidates)} regenerated file(s) SQLFluff rejects; "
          f"{len(grouped)} distinct constructs\n")
    for label, entries in sorted(grouped.items(), key=lambda kv: -len(kv[1]))[: args.show]:
        print(f"{len(entries):4d}  {label}")
        print(f"        {entries[0][0]}")
        print(f"        {entries[0][1]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    kw = sub.add_parser("keywords", help="keywords in identifier positions")
    kw.add_argument("--dialect", default="databricks")

    rt = sub.add_parser("roundtrip", help="sqlglot regenerate -> SQLFluff parse")
    rt.add_argument("--dialect", default="databricks")
    rt.add_argument("--limit-files", type=int, default=0,
                    help="per source, 0 for all")
    rt.add_argument("--show", type=int, default=30)
    args = parser.parse_args(argv)

    if args.mode == "keywords":
        return keywords_mode(args)
    return roundtrip_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
