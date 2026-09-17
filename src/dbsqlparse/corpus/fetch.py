"""Download Spark's SQL test corpus into corpus/cache/.

The cache is gitignored: it is reproducible from a Spark tag, and there is no
reason to commit a few megabytes of someone else's test data.
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .sources import SPARK_SOURCES, SPARK_TAG

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = REPO_ROOT / "corpus" / "cache"

TREE_URL = "https://api.github.com/repos/apache/spark/git/trees/{tag}?recursive=1"
RAW_URL = "https://raw.githubusercontent.com/apache/spark/{tag}/{path}"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "databricks-sql-parser"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def list_spark_sql_files(tag: str = SPARK_TAG) -> list[str]:
    """Every .sql blob path in the Spark tree at `tag`."""
    tree_cache = CACHE_DIR / f"spark-tree-{tag}.json"
    if tree_cache.exists():
        data = json.loads(tree_cache.read_text())
    else:
        raw = _get(TREE_URL.format(tag=tag))
        data = json.loads(raw)
        tree_cache.parent.mkdir(parents=True, exist_ok=True)
        tree_cache.write_text(json.dumps(data))

    if data.get("truncated"):
        print("warning: GitHub truncated the tree listing; corpus may be incomplete",
              file=sys.stderr)
    return [
        t["path"] for t in data["tree"]
        if t["type"] == "blob" and t["path"].endswith(".sql")
    ]


def fetch_spark_corpus(tag: str = SPARK_TAG, workers: int = 12) -> dict[str, int]:
    """Download every .sql file belonging to a known Spark source."""
    all_paths = list_spark_sql_files(tag)
    counts: dict[str, int] = {}

    for source in SPARK_SOURCES:
        assert source.spark_prefix is not None
        paths = [p for p in all_paths if p.startswith(source.spark_prefix)]
        dest_root = CACHE_DIR / source.name
        todo = []
        for path in paths:
            rel = path[len(source.spark_prefix):]
            dest = dest_root / rel
            if not dest.exists():
                todo.append((path, dest))

        if todo:
            def grab(job: tuple[str, pathlib.Path]) -> None:
                path, dest = job
                try:
                    body = _get(RAW_URL.format(tag=tag, path=path), timeout=60)
                except urllib.error.HTTPError as exc:
                    print(f"  skip {path}: HTTP {exc.code}", file=sys.stderr)
                    return
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)

            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(grab, todo))

        counts[source.name] = len(paths)
        print(f"  {source.name:26s} {len(paths):4d} files ({len(todo)} downloaded)")

    return counts


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"fetching Spark SQL corpus @ {SPARK_TAG}")
    total = sum(fetch_spark_corpus().values())
    print(f"corpus cached under {CACHE_DIR} ({total} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
