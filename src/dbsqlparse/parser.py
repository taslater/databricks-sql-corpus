"""Parse API over the generated Spark/Databricks grammar.

Design notes worth knowing before changing this file:

* **Statement splitting uses the lexer, not a regex.** Splitting on ";" with a
  regex breaks on semicolons inside string literals and comments. We tokenise
  once and split on SEMICOLON tokens at paren depth zero, which gets those
  cases right for free.

* **Two-stage parsing.** ANTLR's default ALL(*) prediction is accurate but slow
  on a grammar this size, and this tool has to feel instant in an editor. We
  try SLL first with a bail-out error strategy; SLL is much faster but can
  report a spurious error on input that full LL would accept, so anything that
  fails gets re-parsed with LL before we believe the error. This is ANTLR's
  documented recipe and it is the difference between a linter that runs on
  save and one that does not.
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext
from antlr4.atn.PredictionMode import PredictionMode
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.ErrorStrategy import BailErrorStrategy, DefaultErrorStrategy

from .generated.SqlBaseLexer import SqlBaseLexer
from .generated.SqlBaseParser import SqlBaseParser
from .preprocess import Cell, prepare


class UpperCaseInputStream(InputStream):
    """Case-insensitive input for a case-sensitive grammar.

    Spark's lexer declares every keyword as an uppercase literal (`AS: 'AS';`)
    and gets case-insensitivity from Scala, by wrapping the stream in an
    UpperCaseCharStream before lexing. That wrapper is not part of the .g4, so
    a straight port lexes `SELECT ... as x` as an error while `AS x` succeeds.

    We fold case in LA() only, which is what the lexer's DFA reads. The
    underlying buffer is untouched, so token text -- identifiers, string
    literals, and the names our lint rules care about -- keeps its original
    case.
    """

    def LA(self, offset: int) -> int:
        code = super().LA(offset)
        if code <= 0:  # EOF sentinel
            return code
        upper = chr(code).upper()
        # Some code points uppercase to multiple characters (eg. '\u00df' -> 'SS').
        # Folding those would desynchronise offsets, so leave them as-is.
        return ord(upper) if len(upper) == 1 else code


# ANTLR's default message lists every token it could have accepted, which for
# this grammar is over 400 alternatives on a single line. Useful to nobody.
_EXPECTING_RE = re.compile(r"expecting \{([^}]*)\}")
_MAX_EXPECTED = 6


def tidy_message(msg: str, max_expected: int = _MAX_EXPECTED) -> str:
    """Trim ANTLR's exhaustive 'expecting {...}' list down to something readable."""

    def shorten(match: re.Match[str]) -> str:
        items = [i.strip() for i in match.group(1).split(",") if i.strip()]
        if len(items) <= max_expected:
            return match.group(0)
        shown = ", ".join(items[:max_expected])
        return f"expecting {{{shown}, ... and {len(items) - max_expected} more}}"

    return _EXPECTING_RE.sub(shorten, msg)


@dataclass(frozen=True)
class Diagnostic:
    """One problem, positioned in the original file."""

    line: int  # 1-based
    column: int  # 0-based
    message: str
    code: str = "parse-error"
    severity: str = "error"
    path: str | None = None

    def format(self) -> str:
        where = self.path or "<stdin>"
        return f"{where}:{self.line}:{self.column + 1}: {self.severity}: [{self.code}] {self.message}"


@dataclass
class ParseOptions:
    """Grammar switches Spark exposes through SQLConf.

    Defaults match Spark's own defaults, which is what a Databricks warehouse
    does unless the workspace overrides them.
    """

    # True => keywords follow the ANSI standard and far fewer of them may be
    # used as identifiers. Spark defaults this to False, which is why
    # `SELECT * FROM t WHERE` parses: WHERE is read as a table alias.
    ansi_reserved_keywords: bool = False
    # True => "foo" is an identifier rather than a string literal.
    double_quoted_identifiers: bool = False
    legacy_setops_precedence: bool = False
    legacy_exponent_literal_as_decimal: bool = False


@dataclass
class ParsedStatement:
    sql: str
    tree: ParserRuleContext | None
    line_offset: int  # 0-based line of this statement in the original file
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.tree is not None and not self.diagnostics


@dataclass
class ParseResult:
    path: str | None
    statements: list[ParsedStatement] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    cells: list[Cell] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    @property
    def statement_count(self) -> int:
        return len(self.statements)


class _Collector(ErrorListener):
    """Collects syntax errors instead of printing them to stderr."""

    def __init__(self, line_offset: int = 0, path: str | None = None):
        super().__init__()
        self.line_offset = line_offset
        self.path = path
        self.diagnostics: list[Diagnostic] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.diagnostics.append(
            Diagnostic(
                line=line + self.line_offset,
                column=column,
                message=tidy_message(msg),
                path=self.path,
            )
        )


def _make_lexer(sql: str, collector: ErrorListener | None) -> SqlBaseLexer:
    lexer = SqlBaseLexer(UpperCaseInputStream(sql))
    lexer.removeErrorListeners()
    if collector is not None:
        lexer.addErrorListener(collector)
    return lexer


def _apply_options(parser: SqlBaseParser, options: ParseOptions) -> None:
    parser.SQL_standard_keyword_behavior = options.ansi_reserved_keywords
    parser.double_quoted_identifiers = options.double_quoted_identifiers
    parser.legacy_setops_precedence_enabled = options.legacy_setops_precedence
    parser.legacy_exponent_literal_as_decimal_enabled = (
        options.legacy_exponent_literal_as_decimal
    )


def split_statements(sql: str) -> list[tuple[str, int]]:
    """Split on top-level semicolons, returning (statement, 0-based line offset).

    Uses the real lexer so semicolons inside 'strings', "strings", `backticks`
    and /* comments */ do not split anything.
    """
    lexer = _make_lexer(sql, None)
    try:
        tokens = lexer.getAllTokens()
    except Exception:
        # Unlexable input: hand the whole thing back and let the parser report.
        return [(sql, 0)]

    statements: list[tuple[str, int]] = []
    depth = 0
    start_index = 0  # character offset in sql
    start_line = 0

    for token in tokens:
        if token.type == SqlBaseLexer.LEFT_PAREN:
            depth += 1
        elif token.type == SqlBaseLexer.RIGHT_PAREN:
            depth = max(0, depth - 1)
        elif token.type == SqlBaseLexer.SEMICOLON and depth == 0:
            chunk = sql[start_index : token.stop + 1]
            if chunk.strip().strip(";"):
                statements.append((chunk, start_line))
            start_index = token.stop + 1
            start_line = sql.count("\n", 0, start_index)

    tail = sql[start_index:]
    if tail.strip():
        statements.append((tail, start_line))
    return statements


def parse_statement(
    sql: str,
    options: ParseOptions | None = None,
    line_offset: int = 0,
    path: str | None = None,
) -> ParsedStatement:
    """Parse one statement, SLL first and LL only if SLL complains."""
    options = options or ParseOptions()

    # Stage 1: SLL with bail-out. No error listener -- a failure here is not
    # yet evidence of bad SQL, only that SLL could not decide.
    lexer = _make_lexer(sql, None)
    parser = SqlBaseParser(CommonTokenStream(lexer))
    _apply_options(parser, options)
    parser.removeErrorListeners()
    parser._interp.predictionMode = PredictionMode.SLL
    parser._errHandler = BailErrorStrategy()
    try:
        tree = parser.singleStatement()
        if parser.getNumberOfSyntaxErrors() == 0:
            return ParsedStatement(sql=sql, tree=tree, line_offset=line_offset)
    except Exception:
        # Includes ParseCancellationException from BailErrorStrategy. Any SLL
        # failure just means "ask LL", never "this SQL is bad".
        pass

    # Stage 2: full LL with diagnostics collected.
    collector = _Collector(line_offset=line_offset, path=path)
    lexer = _make_lexer(sql, collector)
    parser = SqlBaseParser(CommonTokenStream(lexer))
    _apply_options(parser, options)
    parser.removeErrorListeners()
    parser.addErrorListener(collector)
    parser._interp.predictionMode = PredictionMode.LL
    parser._errHandler = DefaultErrorStrategy()

    tree = None
    try:
        tree = parser.singleStatement()
    except RecursionError:
        collector.diagnostics.append(
            Diagnostic(
                line=1 + line_offset,
                column=0,
                message="statement too deeply nested to parse",
                code="recursion-limit",
                path=path,
            )
        )

    # Spark treats an unterminated /* comment as an error; the lexer only sets
    # a flag, so surface it here.
    if getattr(lexer, "has_unclosed_bracketed_comment", False):
        collector.diagnostics.append(
            Diagnostic(
                line=1 + line_offset,
                column=0,
                message="unclosed bracketed comment",
                code="unclosed-comment",
                path=path,
            )
        )

    return ParsedStatement(
        sql=sql, tree=tree, line_offset=line_offset, diagnostics=collector.diagnostics
    )


def parse_text(
    text: str, options: ParseOptions | None = None, path: str | None = None
) -> ParseResult:
    """Parse a whole file's worth of SQL: cells, then statements within cells."""
    options = options or ParseOptions()
    result = ParseResult(path=path)
    prepared = prepare(text) if text.strip() else []
    result.cells = [cell for cell, _ in prepared]

    for cell, pre in prepared:
        for chunk, chunk_line in split_statements(pre.text):
            stmt = parse_statement(
                chunk,
                options=options,
                line_offset=cell.line_offset + chunk_line,
                path=path,
            )
            result.statements.append(stmt)
            result.diagnostics.extend(stmt.diagnostics)
    return result


def parse_file(path: str | pathlib.Path, options: ParseOptions | None = None) -> ParseResult:
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_text(text, options=options, path=str(p))
