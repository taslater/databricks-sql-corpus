"""Python ports of the Java helper code embedded in Spark's ANTLR grammar.

Spark's SqlBaseLexer.g4 / SqlBaseParser.g4 carry `@members` blocks written in
Java, plus inline actions and semantic predicates that call into them. ANTLR
copies action code into the generated parser verbatim, so those blocks are
invalid under the Python target.

Rather than hand-editing generated code, we strip the Java `@members` blocks
during the patch step and point each grammar at one of these classes via
`options { superClass = ... }`. The behaviour below is a direct port of the
Java in grammar/vendor/ -- keep it in sync when re-vendoring a new Spark tag.
"""
from __future__ import annotations

from antlr4 import Lexer, Parser


class SqlBaseLexerBase(Lexer):
    """Port of the @members block in Spark's SqlBaseLexer.g4."""

    def __init__(self, input=None, output=None):
        super().__init__(input, output)
        # Set when the input ends inside an unclosed /* ... comment. Spark
        # raises a ParseException on this after lexing completes.
        self.has_unclosed_bracketed_comment = False
        # Greater than zero while lexing an ARRAY/MAP/STRUCT type, which is how
        # the lexer tells `MAP<INT, ARRAY<INT>>` from a `>>` shift operator.
        self.complex_type_level_counter = 0

    def isValidDecimal(self) -> bool:
        """True when the char after a decimal token is not [A-Z0-9_].

        "2.3" in the stream "2.3_" is not a valid decimal token, because the
        underscore makes it part of a longer identifier-ish token.
        """
        next_char = self._input.LA(1)
        if next_char == -1:  # EOF
            return True
        ch = chr(next_char)
        if ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_":
            return False
        return True

    def isHint(self) -> bool:
        """True when '/*' is followed by '+', i.e. it opens a /*+ hint */."""
        next_char = self._input.LA(1)
        return next_char != -1 and chr(next_char) == "+"

    def markUnclosedComment(self) -> None:
        self.has_unclosed_bracketed_comment = True

    def incComplexTypeLevelCounter(self) -> None:
        self.complex_type_level_counter += 1

    def decComplexTypeLevelCounter(self) -> None:
        # A '>' outside a complex type is a dangling GT; leave the counter at 0.
        if self.complex_type_level_counter > 0:
            self.complex_type_level_counter -= 1

    def isShiftRightOperator(self) -> bool:
        return self.complex_type_level_counter == 0

    def reset(self) -> None:  # type: ignore[override]
        self.has_unclosed_bracketed_comment = False
        self.complex_type_level_counter = 0
        super().reset()


class SqlBaseParserBase(Parser):
    """Port of the @members block in Spark's SqlBaseParser.g4.

    These four flags gate semantic predicates in the grammar. Spark sets them
    from SQLConf at runtime; we expose them as plain attributes so the parse
    API can flip them per-dialect. The defaults match Spark's own defaults.
    """

    def __init__(self, input=None, output=None):
        super().__init__(input, output)
        # False => INTERSECT binds tighter than UNION/EXCEPT/MINUS (SQL standard).
        self.legacy_setops_precedence_enabled = False
        # False => an exponent literal becomes a double rather than a decimal.
        self.legacy_exponent_literal_as_decimal_enabled = False
        # True => keyword behaviour follows the ANSI SQL standard (more
        # reserved words, so stricter). Databricks defaults to non-ANSI here.
        self.SQL_standard_keyword_behavior = False
        # True => "foo" is an identifier rather than a string literal.
        self.double_quoted_identifiers = False
