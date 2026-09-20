"""Source pins: is a corpus source still at the revision we pinned?

Every remote source in `sources.py` is pinned to an exact revision, so the
scraped corpus and `baseline.json` do not drift on someone else's schedule.
That is the right default, but it means the *scraped* corpus slowly stops
sampling current practice: a repo that keeps landing new SQL is frozen at the
commit we chose. This module reports how far each pin is behind its repo's
default branch, so bumping one is a decision with a number attached rather than
a guess. It reports; it never edits `sources.py`.

A pin is compared with GitHub's compare API, which answers `ahead_by`: how many
commits the default branch has that the pin does not. A pin that is not an
ancestor of the default branch (a force-push, a tag on a side branch) has no
such count, and is reported as such rather than as zero.

The published-to-a-branch advice in `docs/maintenance.md` is the reference for
what to do with a stale pin; this only tells you which are stale.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .sources import REMOTE_SOURCES, Source

USER_AGENT = (
    "databricks-sql-corpus-sources "
    "(+https://github.com/taslater/databricks-sql-corpus)"
)
REPO_URL = "https://api.github.com/repos/{repo}"
COMMIT_URL = "https://api.github.com/repos/{repo}/commits/{ref}"
COMPARE_URL = "https://api.github.com/repos/{repo}/compare/{base}...{head}"


@dataclass(frozen=True)
class PinStatus:
    """One source's pin, and how far behind the repo's default branch it is."""

    source: Source
    head: str = ""
    head_date: str = ""
    behind: int | None = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def stale(self) -> bool:
        return self.ok and bool(self.behind)


def fetch_json(url: str, token: str | None = None, timeout: int = 30) -> object:
    """GET a JSON document from the GitHub API, optionally authenticated."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def run_sources_check(
    sources: tuple[Source, ...] | None = None,
    fetch=fetch_json,
    token: str | None = None,
) -> list[PinStatus]:
    """Check every remote source, one repo lookup per repo.

    Sources that share a repo and a ref -- the six Spark sources share one tag
    -- share a compare call, because the GitHub compare API is the rate-limited
    one.
    """
    sources = REMOTE_SOURCES if sources is None else sources
    by_repo: dict[str, list[Source]] = {}
    for source in sources:
        if source.is_remote:
            by_repo.setdefault(source.repo, []).append(source)  # type: ignore[arg-type]

    statuses: list[PinStatus] = []
    for repo, group in by_repo.items():
        try:
            info = fetch(REPO_URL.format(repo=repo), token=token)
            default = info["default_branch"]  # type: ignore[index]
            head = fetch(COMMIT_URL.format(repo=repo, ref=default), token=token)
            head_sha = head["sha"]  # type: ignore[index]
            head_date = head["commit"]["committer"]["date"]  # type: ignore[index]
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            OSError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            for source in group:
                statuses.append(PinStatus(source=source, error=str(error)))
            continue

        ahead: dict[str, int | None] = {}
        for source in group:
            if source.ref == head_sha:
                behind: int | None = 0
            else:
                if source.ref not in ahead:
                    ahead[source.ref] = _commits_ahead(
                        repo, source.ref, head_sha, fetch, token
                    )
                behind = ahead[source.ref]
            statuses.append(
                PinStatus(
                    source=source,
                    head=head_sha,
                    head_date=head_date,
                    behind=behind,
                )
            )
    return statuses


def _commits_ahead(
    repo: str, base: str, head: str, fetch, token: str | None
) -> int | None:
    """How many commits `head` has that `base` does not, or None if incomparable."""
    try:
        comparison = fetch(
            COMPARE_URL.format(repo=repo, base=base, head=head), token=token
        )
        return comparison["ahead_by"]  # type: ignore[index]
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        return None


def format_sources_check(statuses: list[PinStatus]) -> str:
    lines = ["=" * 78]
    lines.append("SOURCE PINS -- commits between a pinned revision and the branch")
    lines.append("=" * 78)
    for status in statuses:
        name = status.source.name
        pinned = status.source.ref or ""
        if status.error:
            lines.append(f"  {name:26s} ERROR  {status.error}")
        elif status.behind == 0:
            lines.append(f"  {name:26s} current  {pinned[:12]}")
        elif status.behind is None:
            lines.append(
                f"  {name:26s} incomparable  {pinned[:12]} (not an ancestor of the branch)"
            )
        else:
            lines.append(
                f"  {name:26s} {status.behind:5d} behind  {pinned[:12]}"
                f"  (head {status.head[:12]}, {status.head_date[:10]})"
            )
    return "\n".join(lines)


def sources_payload(statuses: list[PinStatus]) -> dict:
    return {
        "sources": [
            {
                "name": status.source.name,
                "repo": status.source.repo,
                "pinned": status.source.ref,
                "head": status.head,
                "head_date": status.head_date,
                "behind": status.behind,
                "error": status.error,
            }
            for status in statuses
        ]
    }
