#!/usr/bin/env python3
"""Vendor Spark's ANTLR grammar for a given Spark release tag.

Databricks SQL is a superset of Spark SQL, and Spark's SqlBase grammar is the
actual source of truth for its parser -- so we start from the real thing rather
than guessing at the syntax. The pristine download lands in grammar/vendor/;
our Databricks extensions are applied separately so the diff stays visible.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VENDOR_DIR = REPO_ROOT / "grammar" / "vendor"

# Spark 4.x moved the grammar out of sql/catalyst into sql/api and split the
# single SqlBase.g4 into a separate lexer and parser grammar.
GRAMMAR_DIR_4X = "sql/api/src/main/antlr4/org/apache/spark/sql/catalyst/parser"
GRAMMAR_DIR_3X = "sql/catalyst/src/main/antlr4/org/apache/spark/sql/catalyst/parser"

RAW = "https://raw.githubusercontent.com/apache/spark/{tag}/{path}"


def grammar_files(tag: str) -> list[tuple[str, str]]:
    """Return (remote path, local filename) pairs for this Spark tag."""
    major = int(tag.lstrip("v").split(".", 1)[0])
    if major >= 4:
        return [
            (f"{GRAMMAR_DIR_4X}/SqlBaseLexer.g4", "SqlBaseLexer.g4"),
            (f"{GRAMMAR_DIR_4X}/SqlBaseParser.g4", "SqlBaseParser.g4"),
        ]
    return [(f"{GRAMMAR_DIR_3X}/SqlBase.g4", "SqlBase.g4")]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "databricks-sql-parser"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--spark-version",
        default="v4.0.4",
        help="Spark git tag to vendor from (default: v4.0.4, the Spark release "
             "behind Databricks Runtime 17.x)",
    )
    args = ap.parse_args()
    tag = args.spark_version if args.spark_version.startswith("v") else f"v{args.spark_version}"

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    manifest = [f"# Vendored from apache/spark @ {tag}", ""]

    for remote, local in grammar_files(tag):
        url = RAW.format(tag=tag, path=remote)
        try:
            body = fetch(url)
        except urllib.error.HTTPError as exc:
            print(f"error: {url} -> HTTP {exc.code}", file=sys.stderr)
            return 1
        dest = VENDOR_DIR / local
        dest.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        manifest.append(f"{local}  sha256:{digest}  {len(body)} bytes")
        manifest.append(f"    source: {url}")
        print(f"vendored {local} ({len(body)} bytes, sha256:{digest[:12]})")

    (VENDOR_DIR / "MANIFEST.txt").write_text("\n".join(manifest) + "\n")
    print(f"wrote {VENDOR_DIR / 'MANIFEST.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
