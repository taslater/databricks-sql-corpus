"""Doc drift: has a Databricks reference page changed under its transcription?

The reference corpus is a snapshot. Every file records the page it was read
from (`doc`), the production it transcribed (`syntax`) and the date (`checked`),
so the corpus is only as trustworthy as the assumption that the page still says
what it said then. This module watches the page, not the parser: it fetches
each `doc`, extracts the code blocks, and asks whether the transcription still
matches.

It reports; it never edits the corpus. A changed page is a queue item for a
human -- re-read the page, update `syntax:` and the cases, bump `checked:` --
because a tool that rewrites the oracle in place stops being one.

Three checks live here, at three different scales:

    stale      the `checked:` dates -- which pages are old enough to re-read
    drift      the production text -- has the page changed under a file
    index      the page set -- which documented pages have no file, and which
               files point at a page that has gone

The comparison is deliberately forgiving about whitespace. Databricks renders a
production across several inline spans and drops the line breaks between them,
so the live text is `to_view_namealter_body` where the transcription reads
`to_view_name` then `alter_body` on the next line. String equality would call
every such page changed. Normalising away all whitespace bridges it, and the
production's own angle brackets survive because the live side spells them
`&lt;`/`&gt;` while the transcription spells them `<`/`>` -- stripping tags
before unescaping keeps both. Case is folded too: a Databricks re-casing of a
keyword is not a change to the grammar.

A page is `same` when the transcription equals one code block, the ordered join
of the page's production blocks, or a run of consecutive blocks -- the last two
because the reference splits a long production across several blocks on some
pages (`hints`, `group_by`). A block is an example rather than a production
when it opens with the prompt `>` or a `--` comment, which is how the reference
marks the examples it shows below a syntax block. Otherwise the page is
`changed`, and the report carries a token diff against the closest block so the
review has somewhere to start.

A page whose transcription is prose rather than a grammar production cannot be
diffed at all -- `magic_cells.yml` is one -- and is reported `uncertain` rather
than changed, so a permanent, meaningless difference does not drown the real
ones.

Every run also checks controls built here rather than kept in the data: a page
identical to a known file must read `same`, a page that differs must read
`changed`, and a page with no code block must read `uncertain`. Three harness
bugs in this repo once made failure look like success; a control catches all
three.
"""
from __future__ import annotations

import datetime
import difflib
import html
import json
import pathlib
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .reference import ReferenceFile, load_reference_files

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_IGNORE_PATH = REPO_ROOT / "docs" / "reference-index-ignore.txt"
COVERAGE_PATH = REPO_ROOT / "docs" / "reference-coverage.md"

USER_AGENT = (
    "databricks-sql-corpus-drift "
    "(+https://github.com/taslater/databricks-sql-corpus)"
)
SITEMAP_URL = "https://docs.databricks.com/sitemap.xml"
DOC_ROOTS = (
    "https://docs.databricks.com/aws/en/sql/language-manual/",
    "https://docs.databricks.com/aws/en/ldp/developer/",
)

# Verdicts, from the drift check.
SAME = "same"
CHANGED = "changed"
MOVED = "moved"
UNCERTAIN = "uncertain"
ERROR = "fetch-error"
VERDICTS = (SAME, CHANGED, MOVED, UNCERTAIN, ERROR)
# A verdict a human has to look at, as opposed to one that needs no action.
FINDING_VERDICTS = (CHANGED, MOVED)

_PRE = re.compile(r"<pre\b[^>]*>(.*?)</pre>", re.S)
_TAG = re.compile(r"<[^>]+>")
_PROMPT = re.compile(r"^\s*>+\s*")
_LOC = re.compile(r"<loc>(.*?)</loc>", re.S)
# Punctuation kept as its own token so a diff reads as a grammar change rather
# than one long unbroken string. `.` is deliberately absent: `...` should stay
# with the token it follows.
_TOKEN = re.compile(r"[{}\[\](),|<>]|[^\s{}\[\](),|<>]+")
# How a transcription is judged to be a grammar production rather than a
# sentence, used only when nothing matched, to separate "changed" from "this
# was never diffable in the first place". A production has either a bracket or
# another grammar metacharacter, or an all-uppercase keyword -- a reference
# production is written in capitals, a prose note is not.
_PRODUCTION_CHARS = frozenset("{}[]()|<>")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# The page-set check only looks at URL families that can hold a statement or
# clause page. Function, information-schema, concept and how-to pages are
# catalogues, not productions, and never get a reference file; naming the
# families positively keeps a monthly report to the pages that could.
DEFAULT_INDEX_FAMILIES = (
    "/sql-ref-syntax-",
    "/control-flow/",
    "/ldp/developer/ldp-sql-ref-",
    "/delta-",
)
# Ad-hoc suppressions, on top of the families above and the coverage ledger: URL
# substrings for a specific page to stop reporting without narrowing a whole
# family. Read from `docs/reference-index-ignore.txt` so the list is data.
DEFAULT_INDEX_IGNORE: tuple[str, ...] = ()
_COVERAGE_LINK = re.compile(r"\]\((https://docs\.databricks\.com/[^)]+)\)")


class DriftError(RuntimeError):
    """A reference file could not be read for drift."""


def _tight(text: str) -> str:
    """Case-folded with every run of whitespace removed."""
    return "".join(text.split()).casefold()


@dataclass(frozen=True)
class PageBlock:
    """One `<pre>` code block on a reference page, as its raw inner HTML."""

    text: str

    @property
    def raw(self) -> str:
        """The block as plain text, tags stripped before entities are decoded.

        The order matters: stripping tags first leaves `&lt;` alone until the
        unescape, so a production's own angle brackets survive instead of being
        mistaken for an unclosed tag.
        """
        return html.unescape(_TAG.sub("", self.text))

    @property
    def tight(self) -> str:
        """Case-folded with every run of whitespace removed."""
        return _tight(self.raw)

    @property
    def comparable(self) -> str:
        """`tight`, with a leading example prompt (`>`) removed."""
        return _tight(_PROMPT.sub("", self.raw))

    @property
    def is_example(self) -> bool:
        return self.tight.startswith((">", "--"))


@dataclass(frozen=True)
class DriftVerdict:
    """What one page did under its transcription."""

    file: ReferenceFile
    verdict: str
    live_url: str = ""
    detail: str = ""
    diff: str = ""

    @property
    def is_finding(self) -> bool:
        return self.verdict in FINDING_VERDICTS


@dataclass(frozen=True)
class IndexDiff:
    """Documented pages with no file, and files whose page has gone."""

    new: tuple[str, ...]
    gone: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.new and not self.gone


@dataclass(frozen=True)
class DriftReport:
    verdicts: list[DriftVerdict]
    controls: list[DriftVerdict]

    def of(self, verdict: str) -> list[DriftVerdict]:
        return [v for v in self.verdicts if v.verdict == verdict]

    @property
    def controls_ok(self) -> bool:
        return [v.verdict for v in self.controls] == [SAME, CHANGED, UNCERTAIN]

    @property
    def findings(self) -> list[DriftVerdict]:
        return [v for v in self.verdicts if v.is_finding]


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def fetch_doc(url: str, timeout: int = 45) -> tuple[str, str]:
    """Fetch a page: (final URL after redirects, decoded body)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.geturl(), response.read().decode("utf-8", "replace")


def _url_key(url: str) -> str:
    return url.rstrip("/")


# ---------------------------------------------------------------------------
# The drift check
# ---------------------------------------------------------------------------


def extract_blocks(page: str) -> list[PageBlock]:
    """Every `<pre>` block on the page, in document order."""
    return [PageBlock(m.group(1)) for m in _PRE.finditer(page)]


def _matches(ours: str, blocks: list[PageBlock]) -> str:
    """How the transcription matches the page, or "" for no match.

    Tried in order: a single block (the common case), the ordered join of the
    production blocks (a production split over several blocks with examples
    interleaved, as on `hints`), then any run of consecutive blocks.
    """
    if any(block.comparable == ours for block in blocks):
        return "a code block"
    productions = [b.comparable for b in blocks if not b.is_example]
    if productions and "".join(productions) == ours:
        return "the production blocks"
    for start in range(len(blocks)):
        run = ""
        for block in blocks[start:]:
            run += block.comparable
            if run == ours:
                return "consecutive code blocks"
            if len(run) >= len(ours):
                break
    return ""


def _looks_like_production(text: str) -> bool:
    if any(char in _PRODUCTION_CHARS for char in text):
        return True
    return any(
        word.isupper() and len(word) >= 2 for word in _WORD.findall(text)
    )


def _closest(ours: str, blocks: list[PageBlock]) -> PageBlock:
    return max(
        blocks,
        key=lambda block: difflib.SequenceMatcher(
            None, ours, block.comparable
        ).ratio(),
    )


def format_diff(ours_text: str, live_text: str, limit: int = 600) -> str:
    """A compact token diff of the transcription against the closest block."""
    ours = _TOKEN.findall(ours_text)
    live = _TOKEN.findall(live_text)
    parts: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, ours, live
    ).get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete"):
            parts.append("-" + " ".join(ours[i1:i2]))
        if tag in ("replace", "insert"):
            parts.append("+" + " ".join(live[j1:j2]))
    return " ".join(parts)[:limit]


def compare(file: ReferenceFile, page: str, live_url: str = "") -> DriftVerdict:
    """Judge one fetched page against one transcription. No network here."""
    blocks = extract_blocks(page)
    if not blocks:
        return DriftVerdict(
            file, UNCERTAIN, live_url, "no code block on the page"
        )
    ours = _tight(file.syntax)
    matched = _matches(ours, blocks)
    if matched:
        if live_url and _url_key(live_url) != _url_key(file.doc):
            return DriftVerdict(
                file, MOVED, live_url, f"the page redirects here ({matched} matched)"
            )
        return DriftVerdict(file, SAME, live_url, matched)
    if not _looks_like_production(file.syntax):
        return DriftVerdict(
            file,
            UNCERTAIN,
            live_url,
            "the transcription is prose, not a production, so it cannot be diffed",
        )
    best = _closest(ours, blocks)
    return DriftVerdict(
        file,
        CHANGED,
        live_url,
        "the production text differs from the page",
        format_diff(file.syntax, best.raw),
    )


def check_file(file: ReferenceFile, fetch=fetch_doc) -> DriftVerdict:
    """Fetch a file's page and judge it. Network errors become verdicts."""
    try:
        live_url, page = fetch(file.doc)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return DriftVerdict(
                file, MOVED, file.doc, f"HTTP {error.code}: the page is gone or renamed"
            )
        return DriftVerdict(file, ERROR, file.doc, f"HTTP {error.code}")
    except (urllib.error.URLError, OSError) as error:
        return DriftVerdict(file, ERROR, file.doc, str(error))
    return compare(file, page, live_url)


def run_drift(
    files: list[ReferenceFile] | None = None,
    fetch=fetch_doc,
    progress=None,
) -> DriftReport:
    """Check every reference file against its live page. Fetches, so it is slow.

    `progress` is called `(done, total, file)` before each check, so a long run
    is not silent. `fetch` is injected so tests never touch the network.
    """
    files = load_reference_files() if files is None else files
    verdicts: list[DriftVerdict] = []
    for done, file in enumerate(files, start=1):
        if progress is not None:
            progress(done, len(files), file)
        verdicts.append(check_file(file, fetch))
    return DriftReport(verdicts=verdicts, controls=control_verdicts())


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

CONTROL_FILE = ReferenceFile(
    path=pathlib.Path("<control>"),
    statement="control",
    doc="https://example.invalid/control",
    syntax="SELECT 1",
    checked="1970-01-01",
)


def control_verdicts() -> list[DriftVerdict]:
    """Three synthetic pages that must read same, changed and uncertain.

    A matcher that has stopped matching, or one that matches everything, shows
    up here as a control failure rather than as a suspiciously clean run.
    """
    return [
        compare(CONTROL_FILE, "<pre>SELECT 1</pre>"),
        compare(CONTROL_FILE, "<pre>SELECT 2</pre>"),
        compare(CONTROL_FILE, "<p>no code here</p>"),
    ]


# ---------------------------------------------------------------------------
# Staleness (the `checked:` dates)
# ---------------------------------------------------------------------------


def stale_files(
    days: int,
    files: list[ReferenceFile] | None = None,
    today: datetime.date | None = None,
) -> list[tuple[ReferenceFile, int]]:
    """Files last checked more than `days` ago, oldest first, with their age."""
    files = load_reference_files() if files is None else files
    today = datetime.date.today() if today is None else today
    cutoff = today - datetime.timedelta(days=days)
    stale = []
    for file in files:
        checked = datetime.date.fromisoformat(file.checked)
        if checked < cutoff:
            stale.append((file, (today - checked).days))
    return sorted(stale, key=lambda pair: pair[1], reverse=True)


# ---------------------------------------------------------------------------
# The page-set check (sitemap against the files)
# ---------------------------------------------------------------------------


def load_index_ignore(path: pathlib.Path | None = None) -> tuple[str, ...]:
    """Ad-hoc URL substrings to suppress in the page-set check, one per line.

    Data rather than code: `#` starts a comment, blank lines are skipped, and a
    missing file falls back to the built-in patterns so the check still runs.
    """
    path = INDEX_IGNORE_PATH if path is None else path
    if not path.exists():
        return DEFAULT_INDEX_IGNORE
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return tuple(patterns)


def coverage_urls(path: pathlib.Path | None = None) -> set[str]:
    """Every page URL the coverage ledger lists, in any status.

    The ledger records what has been dispositioned -- `done`, `queued` or
    `n/a` -- so a page it lists is not new even when no file transcribes it.
    That is what stops the page-set check reporting the same n/a catalogue
    page every month.
    """
    path = COVERAGE_PATH if path is None else path
    if not path.exists():
        return set()
    return set(_COVERAGE_LINK.findall(path.read_text(encoding="utf-8")))


def sitemap_urls(sitemap_xml: str) -> set[str]:
    """Every documentation URL in the sitemap under the reference roots."""
    return {
        url
        for url in _LOC.findall(sitemap_xml)
        if url.startswith(DOC_ROOTS)
    }


def index_diff(
    sitemap_xml: str,
    files: list[ReferenceFile],
    known_urls: set[str] | None = None,
    families: tuple[str, ...] = DEFAULT_INDEX_FAMILIES,
    ignore: tuple[str, ...] = (),
) -> IndexDiff:
    """Documented pages with no file (`new`), and files whose page is gone.

    A `new` page is a documented statement page in one of the tracked families
    that no file transcribes and the coverage ledger does not list. `gone` is a
    file whose page is no longer in the sitemap -- a rename or a removal, which
    a transcription cannot survive. Pages outside the roots cannot be judged
    against the sitemap, so a file citing one is not reported as gone.
    """
    known = {_url_key(file.doc) for file in files}
    known |= {_url_key(url) for url in (known_urls or set())}
    roots = {_url_key(root) for root in DOC_ROOTS}
    live = sitemap_urls(sitemap_xml)
    new = sorted(
        url
        for url in live
        if _url_key(url) not in known
        and _url_key(url) not in roots
        and any(family in url for family in families)
        and not any(pattern in url for pattern in ignore)
    )
    gone = sorted(
        file.doc
        for file in files
        if file.doc.startswith(DOC_ROOTS) and _url_key(file.doc) not in live
    )
    return IndexDiff(new=tuple(new), gone=tuple(gone))


def run_index_check(
    files: list[ReferenceFile] | None = None,
    fetch=fetch_doc,
    ignore: tuple[str, ...] | None = None,
    families: tuple[str, ...] = DEFAULT_INDEX_FAMILIES,
    known_urls: set[str] | None = None,
) -> IndexDiff:
    """Fetch the sitemap and diff it against the transcribed pages."""
    files = load_reference_files() if files is None else files
    ignore = load_index_ignore() if ignore is None else ignore
    known_urls = coverage_urls() if known_urls is None else known_urls
    _url, sitemap = fetch(SITEMAP_URL)
    return index_diff(sitemap, files, known_urls=known_urls, families=families, ignore=ignore)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _rate(part: int, whole: int) -> float:
    return (part / whole * 100) if whole else 0.0


def format_drift_report(report: DriftReport) -> str:
    lines: list[str] = []
    total = len(report.verdicts)
    lines.append("=" * 78)
    lines.append("DRIFT -- has the reference page changed under its transcription?")
    lines.append("=" * 78)
    for verdict in VERDICTS:
        count = len(report.of(verdict))
        lines.append(
            f"{verdict:11s} {count:3d}/{total:<3d} {_rate(count, total):6.1f}%"
        )
    lines.append(f"controls:   {'ok' if report.controls_ok else 'FAILED'}")
    for verdict in FINDING_VERDICTS:
        found = report.of(verdict)
        if not found:
            continue
        lines.append("")
        lines.append(f"{verdict} ({len(found)}):")
        for item in found:
            lines.append(f"  {item.file.path.name}: {item.detail}")
            lines.append(f"      {item.live_url or item.file.doc}")
            if item.diff:
                lines.append(f"      {item.diff}")
    uncertain = report.of(UNCERTAIN)
    if uncertain:
        lines.append("")
        lines.append(f"uncertain ({len(uncertain)}) -- could not be diffed, review by hand:")
        for item in uncertain:
            lines.append(f"  {item.file.path.name}: {item.detail}")
    if not report.controls_ok:
        lines.append("")
        lines.append("CONTROL FAILED -- the verdicts above are not trustworthy:")
        for item in report.controls:
            lines.append(f"  {item.verdict}: {item.file.path.name}")
    return "\n".join(lines)


def format_stale_report(stale: list[tuple[ReferenceFile, int]]) -> str:
    lines = [f"STALE -- {len(stale)} page(s) last checked more than the cutoff ago"]
    for file, age in stale:
        lines.append(f"  {age:5d}d  {file.path.name:44s} checked {file.checked}")
    if not stale:
        lines.append("  (none)")
    return "\n".join(lines)


def format_index_report(
    diff: IndexDiff,
    families: tuple[str, ...],
    ignore: tuple[str, ...] = (),
) -> str:
    lines = ["=" * 78]
    lines.append("INDEX -- documented pages against the transcribed files")
    lines.append("=" * 78)
    lines.append(f"new   {len(diff.new):3d}  documented pages with no file")
    lines.append(f"gone  {len(diff.gone):3d}  files whose page is no longer in the sitemap")
    for url in diff.new:
        lines.append(f"  new   {url}")
    for url in diff.gone:
        lines.append(f"  gone  {url}")
    lines.append("")
    lines.append(f"families watched ({len(families)}): {' '.join(families)}")
    if ignore:
        lines.append(f"suppressed patterns ({len(ignore)}): {' '.join(ignore)}")
    return "\n".join(lines)


def drift_payload(report: DriftReport) -> dict:
    """The report as JSON, for the drift ledger and the scheduled job."""
    return {
        "controls_ok": report.controls_ok,
        "totals": {verdict: len(report.of(verdict)) for verdict in VERDICTS},
        "verdicts": [
            {
                "file": item.file.path.name,
                "statement": item.file.statement,
                "verdict": item.verdict,
                "doc": item.file.doc,
                "live_url": item.live_url,
                "checked": item.file.checked,
                "detail": item.detail,
                "diff": item.diff,
            }
            for item in report.verdicts
        ],
    }


def write_drift_json(report: DriftReport, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(drift_payload(report), indent=2), encoding="utf-8")
