"""Download the corpus into corpus/cache/.

The cache is gitignored: every source is pinned to an exact revision, so the
cache is reproducible from `sources.py` alone, and there is no reason to commit
a few megabytes of someone else's test data.

One tree listing per (repo, ref) rather than per source, because several
sources usually carve subtrees out of the same repo and the GitHub tree API is
the rate-limited call.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .sources import REMOTE_SOURCES, Source

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = REPO_ROOT / "corpus" / "cache"

TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "databricks-sql-parser"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def list_sql_files(repo: str, ref: str) -> list[str]:
    """Every .sql blob path in `repo` at `ref`, cached on disk."""
    slug = repo.replace("/", "-")
    tree_cache = CACHE_DIR / f"tree-{slug}-{ref}.json"
    if tree_cache.exists():
        data = json.loads(tree_cache.read_text())
    else:
        data = json.loads(_get(TREE_URL.format(repo=repo, ref=ref)))
        tree_cache.parent.mkdir(parents=True, exist_ok=True)
        tree_cache.write_text(json.dumps(data))

    if data.get("truncated"):
        print(f"warning: GitHub truncated the tree listing for {repo}; "
              "corpus may be incomplete", file=sys.stderr)
    return [
        t["path"] for t in data.get("tree", [])
        if t["type"] == "blob" and t["path"].endswith(".sql")
    ]


def fetch_source(source: Source, all_paths: list[str], workers: int = 12) -> int:
    """Download every .sql file belonging to one source. Returns the file count."""
    assert source.repo is not None and source.ref is not None
    paths = [p for p in all_paths if p.startswith(source.prefix)]
    dest_root = CACHE_DIR / source.name

    todo: list[tuple[str, pathlib.Path]] = []
    for path in paths:
        rel = path[len(source.prefix):]
        dest = dest_root / rel
        if not dest.exists():
            todo.append((path, dest))

    if todo:
        def grab(job: tuple[str, pathlib.Path]) -> None:
            path, dest = job
            url = RAW_URL.format(repo=source.repo, ref=source.ref, path=urllib.parse.quote(path))
            try:
                body = _get(url, timeout=60)
            except urllib.error.HTTPError as exc:
                print(f"  skip {path}: HTTP {exc.code}", file=sys.stderr)
                return
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(grab, todo))

    print(f"  {source.name:26s} {len(paths):4d} files ({len(todo)} downloaded)")
    return len(paths)


def fetch_corpus(workers: int = 12) -> dict[str, int]:
    """Download every remote source, one tree listing per (repo, ref)."""
    by_origin: dict[tuple[str, str], list[Source]] = collections.defaultdict(list)
    for source in REMOTE_SOURCES:
        assert source.repo is not None and source.ref is not None
        by_origin[(source.repo, source.ref)].append(source)

    counts: dict[str, int] = {}
    for (repo, ref), sources in by_origin.items():
        print(f"{repo} @ {ref[:12]}")
        all_paths = list_sql_files(repo, ref)
        for source in sources:
            counts[source.name] = fetch_source(source, all_paths, workers=workers)
    return counts


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(fetch_corpus().values())
    print(f"corpus cached under {CACHE_DIR} ({total} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
