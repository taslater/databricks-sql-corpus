"""Turn a real-world Databricks .sql file into parseable SQL statements.

Two things routinely found in Databricks .sql files are not SQL and will stop
the grammar dead:

  * Notebook source format -- a `-- Databricks notebook source` header, cells
    separated by `-- COMMAND ----------`, and `-- MAGIC %md` cells whose
    contents are Markdown or Python rather than SQL.
  * Widget substitution -- `${env}.raw.events_raw`. The Spark lexer has no
    token for `$` at all, so this is a hard lex failure.

Everything here is line- and offset-preserving, so a diagnostic's line and
column still point at the right place in the original file. That matters: a
linter that reports the wrong line is worse than no linter.

Named parameter markers (`:param`) and positional ones (`?`) are left alone --
Spark's grammar has rules for both.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NOTEBOOK_HEADER = "-- Databricks notebook source"
CELL_SEPARATOR_RE = re.compile(r"^--\s*COMMAND\s*-{2,}\s*$")
MAGIC_RE = re.compile(r"^--\s*MAGIC\s*(%[a-zA-Z]+)?(.*)$")
# ${name} widget substitution. Deliberately not matched inside a longer word.
WIDGET_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)?\}")


@dataclass
class Cell:
    """One notebook cell (or the whole file, for a plain .sql file)."""

    index: int
    text: str
    line_offset: int  # 0-based line in the original file where this cell starts
    kind: str  # "sql" | "magic" | "empty"
    magic: str | None = None

    @property
    def is_sql(self) -> bool:
        return self.kind == "sql"


@dataclass
class PreprocessResult:
    text: str
    substitutions: dict[str, str] = field(default_factory=dict)  # placeholder -> original

    @property
    def changed(self) -> bool:
        return bool(self.substitutions)


def is_notebook(text: str) -> bool:
    """True for Databricks notebook-source files.

    We check the header first but fall back to the cell separator, because
    notebooks exported by some tooling lose the header line.
    """
    head = text.lstrip("﻿").lstrip()
    if head.startswith(NOTEBOOK_HEADER):
        return True
    return any(CELL_SEPARATOR_RE.match(line) for line in text.splitlines())


def split_cells(text: str) -> list[Cell]:
    """Split notebook source into cells, tagging which are actually SQL.

    A plain .sql file comes back as a single SQL cell at offset 0, so callers
    do not need to care which kind of file they were handed.
    """
    lines = text.splitlines()
    if not is_notebook(text):
        return [Cell(index=0, text=text, line_offset=0, kind="sql")]

    cells: list[Cell] = []
    current: list[str] = []
    start_line = 0

    def flush() -> None:
        nonlocal current, start_line
        body = "\n".join(current)
        cells.append(_classify(len(cells), body, start_line))
        current = []

    for lineno, line in enumerate(lines):
        if CELL_SEPARATOR_RE.match(line):
            flush()
            start_line = lineno + 1
            continue
        current.append(line)
    flush()
    return cells


def _classify(index: int, body: str, line_offset: int) -> Cell:
    """Decide whether a cell is SQL, a magic cell, or empty."""
    magic = None
    meaningful = False

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == NOTEBOOK_HEADER:
            continue
        match = MAGIC_RE.match(stripped)
        if match:
            # A `-- MAGIC %md` / `%python` cell is not SQL. The directive only
            # appears on the first MAGIC line; later ones are continuations.
            if magic is None and match.group(1):
                magic = match.group(1)
            continue
        if stripped.startswith("--"):
            continue  # ordinary SQL comment
        meaningful = True

    # Only treat a cell as magic when it holds NOTHING but magic and comments.
    # A cell with both a -- MAGIC directive and real SQL is malformed, and the
    # safe reading for a CI gate is to parse it and report, never to skip it
    # silently -- silently skipped content is how broken SQL reaches main.
    if magic is not None and not meaningful:
        return Cell(index, body, line_offset, kind="magic", magic=magic)
    if not meaningful:
        return Cell(index, body, line_offset, kind="empty")
    return Cell(index, body, line_offset, kind="sql")


def _placeholder_for(name: str, width: int) -> str:
    """Build a valid SQL identifier of exactly `width` characters.

    Length preservation is the whole point: every character offset after the
    substitution stays valid, so error positions need no remapping.
    """
    candidate = f"_{name}"
    if len(candidate) > width:
        return candidate[:width]
    return candidate.ljust(width, "_")


def substitute_widgets(text: str) -> PreprocessResult:
    """Replace `${name}` with a same-length identifier so the lexer accepts it."""
    subs: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        original = match.group(0)
        name = match.group(1) or "param"
        placeholder = _placeholder_for(name, len(original))
        subs[placeholder] = original
        return placeholder

    return PreprocessResult(text=WIDGET_RE.sub(repl, text), substitutions=subs)


def prepare(text: str) -> list[tuple[Cell, PreprocessResult]]:
    """Full pipeline: split into cells, keep the SQL ones, substitute widgets."""
    return [(cell, substitute_widgets(cell.text)) for cell in split_cells(text) if cell.is_sql]
