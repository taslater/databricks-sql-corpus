"""The source-pin report decides whether to bump a pinned revision, so a wrong
count is a wrong decision. The API is faked: these tests never touch GitHub.
"""
from __future__ import annotations

import json
import urllib.error

import pytest

from dbsqlparse.corpus import sources_check
from dbsqlparse.corpus.sources import Source
from dbsqlparse.corpus.sources_check import (
    COMMIT_URL,
    COMPARE_URL,
    REPO_URL,
    PinStatus,
    fetch_json,
    format_sources_check,
    run_sources_check,
    sources_payload,
)

REPO = "acme/sql"
PIN = "aaaaaaaaaaaa"
HEAD = "bbbbbbbbbbbb"


def source(name: str = "s", ref: str = PIN, repo: str = REPO) -> Source:
    return Source(name=name, description="d", expectation="valid", repo=repo, ref=ref)


def api(responses: dict, calls: list | None = None):
    def fetch(url: str, token: str | None = None):
        if calls is not None:
            calls.append(url)
        value = responses.get(url)
        if value is None:
            raise AssertionError(f"unexpected url {url}")
        if isinstance(value, Exception):
            raise value
        return value

    return fetch


def happy_responses(*, ahead: int = 3, head: str = HEAD, default: str = "main") -> dict:
    return {
        REPO_URL.format(repo=REPO): {"default_branch": default},
        COMMIT_URL.format(repo=REPO, ref=default): {
            "sha": head,
            "commit": {"committer": {"date": "2026-08-01T00:00:00Z"}},
        },
        COMPARE_URL.format(repo=REPO, base=PIN, head=head): {"ahead_by": ahead},
    }


# ---------------------------------------------------------------------------
# PinStatus
# ---------------------------------------------------------------------------


def test_pin_status_error_and_stale():
    errored = PinStatus(source=source(), error="boom")
    assert not errored.ok
    assert not errored.stale
    current = PinStatus(source=source(), behind=0)
    assert not current.stale
    behind = PinStatus(source=source(), behind=2)
    assert behind.stale


# ---------------------------------------------------------------------------
# run_sources_check
# ---------------------------------------------------------------------------


def test_run_sources_check_reports_commits_behind():
    statuses = run_sources_check(sources=(source(),), fetch=api(happy_responses(ahead=3)))
    assert statuses[0].behind == 3
    assert statuses[0].head == HEAD
    assert statuses[0].head_date.startswith("2026-08-01")
    assert statuses[0].stale


def test_run_sources_check_current_when_ref_is_head():
    statuses = run_sources_check(sources=(source(ref=HEAD),), fetch=api(happy_responses(head=HEAD)))
    assert statuses[0].behind == 0
    assert not statuses[0].stale


def test_run_sources_check_incomparable_when_compare_fails():
    responses = happy_responses()
    responses[COMPARE_URL.format(repo=REPO, base=PIN, head=HEAD)] = urllib.error.HTTPError(
        "u", 404, "Not Found", {}, None
    )
    statuses = run_sources_check(sources=(source(),), fetch=api(responses))
    assert statuses[0].behind is None


def test_run_sources_check_shares_one_compare_per_repo_and_ref():
    calls: list[str] = []
    statuses = run_sources_check(
        sources=(source(name="a"), source(name="b")),
        fetch=api(happy_responses(), calls),
    )
    assert [s.behind for s in statuses] == [3, 3]
    compares = [c for c in calls if "/compare/" in c]
    assert len(compares) == 1


def test_run_sources_check_repo_error_marks_every_source():
    responses = {REPO_URL.format(repo=REPO): urllib.error.HTTPError("u", 500, "x", {}, None)}
    statuses = run_sources_check(sources=(source(name="a"), source(name="b")), fetch=api(responses))
    assert all(not s.ok for s in statuses)
    assert all(s.error for s in statuses)


def test_run_sources_check_skips_local_sources():
    local = Source(name="local:x", description="d", expectation="valid", local_paths=("/x",))
    assert run_sources_check(sources=(local,), fetch=api({})) == []


def test_run_sources_check_defaults_to_remote_sources(monkeypatch):
    monkeypatch.setattr(sources_check, "REMOTE_SOURCES", (source(),))
    statuses = run_sources_check(fetch=api(happy_responses()))
    assert len(statuses) == 1


# ---------------------------------------------------------------------------
# fetch_json
# ---------------------------------------------------------------------------


def test_fetch_json_sends_authorization_when_token_given(monkeypatch):
    seen: dict = {}

    class Response:
        def read(self):
            return json.dumps({"ok": True}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def opener(request, timeout=0):
        seen["headers"] = request.headers
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", opener)
    assert fetch_json("https://api.github.com/x", token="t") == {"ok": True}
    assert seen["headers"].get("Authorization") == "Bearer t"
    assert fetch_json("https://api.github.com/x") == {"ok": True}
    assert seen["headers"].get("Authorization") is None


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def test_format_sources_check_covers_every_state():
    statuses = [
        PinStatus(source=source("behind"), head=HEAD, head_date="2026-08-01T00:00:00Z", behind=4),
        PinStatus(source=source("current", ref=HEAD), head=HEAD, head_date="2026-08-01T00:00:00Z", behind=0),
        PinStatus(source=source("odd"), behind=None),
        PinStatus(source=source("bad"), error="offline"),
    ]
    text = format_sources_check(statuses)
    assert "4 behind" in text
    assert "current" in text
    assert "incomparable" in text
    assert "ERROR  offline" in text


def test_sources_payload():
    payload = sources_payload([PinStatus(source=source(), head=HEAD, behind=1)])
    assert payload["sources"][0]["repo"] == REPO
    assert payload["sources"][0]["behind"] == 1
