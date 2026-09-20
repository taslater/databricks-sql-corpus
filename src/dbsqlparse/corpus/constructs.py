"""The failing line, normalised enough to group findings by construct.

`make gaps` and `make diff` both answer "which construct is failing", and the
two reports only read against each other if a construct means the same thing
in both. This module is that single definition, moved out of `cli.py` when the
differential report arrived.
"""
from __future__ import annotations

import functools
import pathlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .harness import FileResult


@functools.lru_cache(maxsize=1)
def keywords(dialect: str = "databricks") -> frozenset[str]:
    """Every keyword the dialect knows, used to tell syntax from identifiers."""
    from sqlfluff.core.dialects import dialect_selector

    d = dialect_selector(dialect)
    words: set[str] = set()
    for key in ("reserved_keywords", "unreserved_keywords"):
        try:
            words |= set(d.sets(key))
        except (KeyError, AttributeError):
            pass
    return frozenset(words)


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STRING = re.compile(r"""('[^']*'|"[^"]*")""")


def normalise(line: str, dialect: str) -> str:
    """Replace identifiers and literals so the same construct groups together.

    Without this, three materialized views that fail on the same missing
    grammar appear as three separate findings purely because the table names
    differ. Keywords come from the dialect under test rather than a hand-kept
    list, so this stays right as the dialect grows.
    """
    # A comment's prose is never the construct that failed. Collapsing to the
    # marker plus its first word groups every `-- MAGIC` line together, which
    # is the actual finding.
    if line.startswith("--"):
        head = line.split()[:2]
        return " ".join(head) + (" ..." if len(line.split()) > 2 else "")
    kw = keywords(dialect)
    line = _STRING.sub("'...'", line)
    return _IDENT.sub(
        lambda m: m.group(0) if m.group(0).upper() in kw else "<id>", line
    )


def construct(f: FileResult, dialect: str = "databricks") -> str:
    """The failing source line, normalised enough to group on."""
    try:
        lines = pathlib.Path(f.path).read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    except OSError:
        return f.errors[0] if f.errors else "unknown"
    if f.line and 0 < f.line <= len(lines):
        raw = lines[f.line - 1].strip()
        if raw:
            return normalise(raw, dialect)[:88]
    return f.errors[0][:88] if f.errors else "unknown"
