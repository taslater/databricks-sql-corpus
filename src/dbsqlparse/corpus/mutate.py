"""Generate SQL that is guaranteed invalid, to measure false negatives.

Motivation: a corpus of valid SQL cannot detect a parser that accepts
everything. We need input the parser MUST reject.

The catch is that most obvious mutations are not reliably invalid. Spark's
default keyword mode lets nearly any keyword be an identifier, so:

    SELECT a, b FROM t   --> SELECT a b FROM t      (valid: b aliases a)
    SELECT a FROM t      --> SELECT FROM t          (valid: t aliases FROM)

Scoring against mutations like those would count correct behaviour as a miss.
So mutations are split into two tiers:

    GUARANTEED -- invalid on structural grounds no keyword rule can rescue:
                  unbalanced parens, unterminated literals, doubled
                  punctuation, truncation after a dangling operator. These are
                  scored.
    WEAK       -- plausible typos that MIGHT still parse. Generated and
                  reported for inspection, never scored.

Tokenising uses SQLFluff's lexer rather than a regex, for the same reason it
always did: splitting on punctuation with a regex breaks inside string
literals and comments. It used to use this project's own ANTLR lexer; that
parser has been retired, and since SQLFluff is now the subject under test its
lexer is also the one that decides where tokens begin and end.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from ..preprocess import CELL_SEPARATOR_RE

GUARANTEED = "guaranteed"
WEAK = "weak"

# SQLFluff token types, in place of the ANTLR token ids this used to use.
OPEN_PAREN = "start_bracket"
CLOSE_PAREN = "end_bracket"
COMMA = "comma"
SEMICOLON = "semicolon"
PLUS = "plus"
EQUALS = "equals"
WORD = "word"
STRINGS = ("single_quote", "double_quote")
COMMENTS = ("inline_comment", "block_comment")
# SQLFluff's databricks dialect lexes `-- COMMAND ----------` as its own token
# type rather than a comment, because the cell separator is a statement
# delimiter there. Other dialects see a plain comment, so both are handled.
SEPARATORS = ("command",)
IGNORED = ("whitespace", "newline")


@dataclass(frozen=True)
class Mutant:
    sql: str
    kind: str
    tier: str
    origin: str  # description of the source statement


@dataclass(frozen=True)
class Tok:
    """A token with absolute character offsets into the original string.

    SQLFluff reports line/position, not offsets, but `lex` returns every token
    in order including whitespace, so offsets accumulate exactly.
    """

    type: str
    raw: str
    start: int

    @property
    def stop(self) -> int:
        """Index of the token's LAST character, inclusive (as ANTLR reported)."""
        return self.start + len(self.raw) - 1

    @property
    def upper(self) -> str:
        return self.raw.upper()


@lru_cache(maxsize=1)
def _lexer():
    from sqlfluff.core import FluffConfig
    from sqlfluff.core.parser import Lexer

    return Lexer(config=FluffConfig(overrides={"dialect": "databricks"}))


def _tokens(sql: str) -> list[Tok]:
    elements, _ = _lexer().lex(sql)
    out: list[Tok] = []
    offset = 0
    for el in elements:
        raw = el.raw
        if raw:
            out.append(Tok(el.get_type(), raw, offset))
        offset += len(raw)
    return out


def _of_type(tokens: list[Tok], *types: str) -> list[Tok]:
    return [t for t in tokens if t.type in types]


def _words(tokens: list[Tok], *words: str) -> list[Tok]:
    return [t for t in tokens if t.type == WORD and t.upper in words]


def _in_set_statement(tokens: list[Tok], index: int) -> bool:
    """True when tokens[index] sits in a statement opening with SET.

    `SET spark.sql.some.key =` with nothing after the `=` is a legitimate Spark
    config assignment, so truncating there does NOT produce invalid SQL. Every
    other context makes a trailing `=` a syntax error. Without this check the
    mutation is mis-tiered and the corpus reports a false negative that is
    really the parser being correct.

    A statement ends at a semicolon *or* at a notebook cell separator. Walking
    back only to the semicolon misses the common notebook shape, where cells
    hold one unterminated statement each and the nearest semicolon is several
    cells earlier -- which is exactly how this escaped the first time.
    """
    i = index
    while i > 0:
        previous = tokens[i - 1]
        if previous.type == SEMICOLON:
            break
        if previous.type in SEPARATORS or (
            previous.type in COMMENTS
            and CELL_SEPARATOR_RE.match(previous.raw.strip())
        ):
            break
        i -= 1
    for token in tokens[i : index + 1]:
        if token.type in COMMENTS or token.type in IGNORED:
            continue
        return token.type == WORD and token.upper == "SET"
    return False


def mutate(sql: str, origin: str, rng: random.Random) -> list[Mutant]:
    """Produce every mutation that applies to this statement."""
    out: list[Mutant] = []
    try:
        tokens = _tokens(sql)
    except Exception:
        return out
    if len(tokens) < 4:
        return out

    # --- GUARANTEED: unbalanced parentheses -------------------------------
    closers = _of_type(tokens, CLOSE_PAREN)
    if closers:
        victim = rng.choice(closers)
        out.append(Mutant(
            sql[: victim.start] + sql[victim.stop + 1 :],
            kind="delete-close-paren", tier=GUARANTEED, origin=origin,
        ))

    openers = _of_type(tokens, OPEN_PAREN)
    if openers:
        victim = rng.choice(openers)
        out.append(Mutant(
            sql[: victim.start] + "(" + sql[victim.start :],
            kind="insert-open-paren", tier=GUARANTEED, origin=origin,
        ))

    # --- GUARANTEED: unterminated string literal --------------------------
    strings = _of_type(tokens, *STRINGS)
    if strings:
        victim = rng.choice(strings)
        out.append(Mutant(
            sql[: victim.stop] + sql[victim.stop + 1 :],  # drop the closing quote
            kind="unterminated-string", tier=GUARANTEED, origin=origin,
        ))

    # --- GUARANTEED: doubled comma ----------------------------------------
    commas = _of_type(tokens, COMMA)
    if commas:
        victim = rng.choice(commas)
        out.append(Mutant(
            sql[: victim.start] + ",," + sql[victim.stop + 1 :],
            kind="double-comma", tier=GUARANTEED, origin=origin,
        ))

    # --- truncate after a dangling binary operator ------------------------
    # Arithmetic and comparison operators are guaranteed -- nothing can follow
    # `a +` or `a =` at the end of input and still parse -- with one exception:
    # `SET key =` is a valid config assignment with an empty value, so an EQ
    # inside a SET statement is skipped.
    #
    # AND and OR are NOT, and it took a real corpus to notice. In Spark's
    # default keyword mode they are non-reserved, so truncating `SELECT a OR`
    # leaves `SELECT a AS OR` -- a column aliased to the word OR, which is
    # valid. It depends on position (`WHERE x AND` has no such reading), so it
    # cannot be predicted here, which is exactly what WEAK is for. Scoring
    # these would count correct behaviour as a miss.
    arithmetic = [
        t for i, t in enumerate(tokens)
        if t.type == PLUS
        or (t.type == EQUALS and not _in_set_statement(tokens, i))
    ]
    if arithmetic:
        victim = rng.choice(arithmetic)
        truncated = sql[: victim.stop + 1].rstrip()
        if truncated:
            out.append(Mutant(
                truncated, kind="dangling-operator", tier=GUARANTEED, origin=origin,
            ))

    boolean = _words(tokens, "AND", "OR")
    if boolean:
        victim = rng.choice(boolean)
        truncated = sql[: victim.stop + 1].rstrip()
        if truncated:
            out.append(Mutant(
                truncated, kind="dangling-boolean-operator", tier=WEAK, origin=origin,
            ))

    # --- GUARANTEED: unclosed bracketed comment ---------------------------
    out.append(Mutant(
        "/* note\n" + sql, kind="unclosed-comment", tier=GUARANTEED, origin=origin,
    ))

    # --- WEAK: plausible typos that may legitimately still parse -----------
    keywords = _words(tokens, "FROM", "WHERE", "SELECT")
    if keywords:
        victim = rng.choice(keywords)
        out.append(Mutant(
            sql[: victim.start] + sql[victim.stop + 1 :],
            kind="delete-keyword", tier=WEAK, origin=origin,
        ))
    if commas:
        victim = rng.choice(commas)
        out.append(Mutant(
            sql[: victim.start] + sql[victim.stop + 1 :],
            kind="delete-comma", tier=WEAK, origin=origin,
        ))
    return out


def mutate_corpus(statements: list[tuple[str, str]], seed: int = 0, limit: int | None = None):
    """Mutate an iterable of (sql, origin) pairs. Deterministic for a given seed."""
    rng = random.Random(seed)
    mutants: list[Mutant] = []
    for sql, origin in statements:
        mutants.extend(mutate(sql, origin, rng))
        if limit is not None and len(mutants) >= limit:
            break
    return mutants[:limit] if limit is not None else mutants
