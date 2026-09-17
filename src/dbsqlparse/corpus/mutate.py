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
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from antlr4 import CommonTokenStream

from ..generated.SqlBaseLexer import SqlBaseLexer
from ..parser import UpperCaseInputStream

GUARANTEED = "guaranteed"
WEAK = "weak"


@dataclass(frozen=True)
class Mutant:
    sql: str
    kind: str
    tier: str
    origin: str  # description of the source statement


def _tokens(sql: str):
    lexer = SqlBaseLexer(UpperCaseInputStream(sql))
    lexer.removeErrorListeners()
    stream = CommonTokenStream(lexer)
    stream.fill()
    return [t for t in stream.tokens if t.type != -1]  # drop EOF


def _of_type(tokens, type_) -> list:
    return [t for t in tokens if t.type == type_]


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
    closers = _of_type(tokens, SqlBaseLexer.RIGHT_PAREN)
    if closers:
        victim = rng.choice(closers)
        out.append(Mutant(
            sql[: victim.start] + sql[victim.stop + 1 :],
            kind="delete-close-paren", tier=GUARANTEED, origin=origin,
        ))

    openers = _of_type(tokens, SqlBaseLexer.LEFT_PAREN)
    if openers:
        victim = rng.choice(openers)
        out.append(Mutant(
            sql[: victim.start] + "(" + sql[victim.start :],
            kind="insert-open-paren", tier=GUARANTEED, origin=origin,
        ))

    # --- GUARANTEED: unterminated string literal --------------------------
    strings = _of_type(tokens, SqlBaseLexer.STRING_LITERAL)
    if strings:
        victim = rng.choice(strings)
        out.append(Mutant(
            sql[: victim.stop] + sql[victim.stop + 1 :],  # drop the closing quote
            kind="unterminated-string", tier=GUARANTEED, origin=origin,
        ))

    # --- GUARANTEED: doubled comma ----------------------------------------
    commas = _of_type(tokens, SqlBaseLexer.COMMA)
    if commas:
        victim = rng.choice(commas)
        out.append(Mutant(
            sql[: victim.start] + ",," + sql[victim.stop + 1 :],
            kind="double-comma", tier=GUARANTEED, origin=origin,
        ))

    # --- GUARANTEED: truncate after a dangling binary operator ------------
    operators = [
        t for t in tokens
        if t.type in (SqlBaseLexer.PLUS, SqlBaseLexer.EQ, SqlBaseLexer.AND, SqlBaseLexer.OR)
    ]
    if operators:
        victim = rng.choice(operators)
        truncated = sql[: victim.stop + 1].rstrip()
        if truncated:
            out.append(Mutant(
                truncated, kind="dangling-operator", tier=GUARANTEED, origin=origin,
            ))

    # --- GUARANTEED: unclosed bracketed comment ---------------------------
    out.append(Mutant(
        "/* note\n" + sql, kind="unclosed-comment", tier=GUARANTEED, origin=origin,
    ))

    # --- WEAK: plausible typos that may legitimately still parse -----------
    keywords = [
        t for t in tokens
        if t.type in (SqlBaseLexer.FROM, SqlBaseLexer.WHERE, SqlBaseLexer.SELECT)
    ]
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
