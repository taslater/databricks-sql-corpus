"""Mine sqlglot's Databricks/Spark dialect tests for constructs SQLFluff misses.

Discovery only, and deliberately not wired into the corpus. sqlglot's fixtures
are parser tests maintained by its core team: a curated set of constructs, the
same kind of source that found real gaps when SQLFluff's own fixtures were
added to the corpus. But a fixture is a candidate, not an oracle -- the
Databricks SQL reference decides. This script prints candidates; a human reads
the docs and transcribes the real ones into `corpus/reference/`.

Extraction is AST-based, not regex: the test files call
`self.validate_identity("...")` and `self.validate_all("...", write={...})`,
and only the read-dialect SQL (the first argument) is interesting. The pinned
ref is the same sqlglot version the differential runner records.

    .venv/bin/python scripts/probe_sqlglot_fixtures.py
    .venv/bin/python scripts/probe_sqlglot_fixtures.py --ref v30.18.0 --show 40
"""
from __future__ import annotations

import argparse
import ast
import collections
import pathlib
import re
import sys
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = REPO_ROOT / "corpus" / "cache" / "sqlglot-fixtures"
RAW = "https://raw.githubusercontent.com/tobymao/sqlglot/{ref}/tests/dialects/{name}.py"

TEST_FILES = ("test_databricks", "test_spark")
HELPERS = {"validate_identity", "validate_all"}
SQL_START = re.compile(
    r"^\s*(SELECT|WITH|CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|MERGE|COPY|SET|"
    r"SHOW|DESCRIBE|DESC|EXPLAIN|TRUNCATE|GRANT|REVOKE|CALL|DECLARE|BEGIN|"
    r"EXECUTE|OPTIMIZE|VACUUM|REFRESH|ANALYZE|USE|REPLACE|COMMENT|MSCK|"
    r"SYNC|LOAD|VALUES|TABLE)\b",
    re.IGNORECASE,
)


def fetch(ref: str, name: str) -> pathlib.Path:
    """Download a pinned test file once, into the reproducible cache."""
    path = CACHE / ref / f"{name}.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = RAW.format(ref=ref, name=name)
        print(f"fetching {url}", file=sys.stderr)
        with urllib.request.urlopen(url) as response:
            path.write_bytes(response.read())
    return path


def extract(path: pathlib.Path) -> list[tuple[str, int]]:
    """Every SQL string passed to a validate_* helper, with its source line."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in HELPERS:
            continue
        args = node.args
        # validate_all's first argument is the read-dialect SQL; the `write`
        # translations are other dialects and are not this corpus's business.
        wanted = args[:1] if func.attr == "validate_all" else args
        for arg in wanted:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                text = arg.value.strip()
                if SQL_START.match(text):
                    out.append((text, node.lineno))
    return out


def known_constructs() -> set[str]:
    """Normalised repros already recorded, so the probe only shows new ones."""
    from dbsqlparse.corpus.constructs import normalise

    known: set[str] = set()
    gaps = REPO_ROOT / "docs" / "gaps.md"
    if gaps.exists():
        for line in gaps.read_text(encoding="utf-8").splitlines():
            for fragment in re.findall(r"`([^`]+)`", line):
                if SQL_START.match(fragment):
                    known.add(normalise(fragment.splitlines()[0], "databricks"))
    for path in (REPO_ROOT / "corpus" / "reference").rglob("*.yml"):
        text = path.read_text(encoding="utf-8")
        for sql in re.findall(r"^\s+sql: (.+)$", text, re.MULTILINE):
            known.add(normalise(sql.strip().split("\\n")[0], "databricks"))
    return known


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="v30.18.0", help="sqlglot tag or commit")
    parser.add_argument("--show", type=int, default=25, help="how many to print")
    args = parser.parse_args(argv)

    from dbsqlparse.corpus.constructs import normalise
    from dbsqlparse.corpus.runners import SqlFluffRunner

    runner = SqlFluffRunner(dialect="databricks")
    known = known_constructs()

    candidates: list[tuple[str, str, int]] = []
    per_file: dict[str, int] = {}
    for name in TEST_FILES:
        path = fetch(args.ref, name)
        strings = extract(path)
        per_file[name] = len(strings)
        for sql, lineno in strings:
            result = runner.check(sql, f"<{name}.py:{lineno}>")
            if result.ok:
                continue
            line = result.line or 1
            source_lines = sql.splitlines()
            raw = source_lines[line - 1] if 0 < line <= len(source_lines) else source_lines[0]
            candidates.append((normalise(raw.strip(), "databricks"), f"{name}.py:{lineno}", line))

    print(f"sqlglot {args.ref}")
    for name, count in per_file.items():
        print(f"  {name}: {count} SQL strings")
    print(f"  SQLFluff rejects {len(candidates)} of them")

    grouped: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    for label, origin, _ in candidates:
        grouped[label].append((origin, _))

    fresh = {k: v for k, v in grouped.items() if k not in known}
    print(f"\n{len(grouped)} distinct constructs rejected; "
          f"{len(fresh)} not already in docs/gaps.md or the reference corpus\n")
    for label, entries in sorted(fresh.items(), key=lambda kv: -len(kv[1]))[: args.show]:
        print(f"{len(entries):4d}  {label}")
        print(f"        {entries[0][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
