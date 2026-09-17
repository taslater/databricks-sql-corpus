"""Extract a small semantic model from a parse tree.

Rules are written against this model, not against ANTLR contexts. That is a
deliberate boundary:

* A rule author does not need to know Spark's grammar. Writing a naming rule
  should not require knowing that a column definition is a
  `ColDefinitionContext` whose name lives in `errorCapturingIdentifier`.
* The grammar is regenerated from upstream Spark. When Spark renames a rule,
  the breakage is confined to this file rather than spread across every rule.

Type resolution here is deliberately local: a column's type is known only when
the file itself says so, via a CREATE TABLE declaration or an explicit CAST.
Anything else is left as None, and rules skip it. A linter that guesses types
and reports on the guess is worse than one that stays quiet.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from antlr4 import ParserRuleContext
from antlr4.tree.Tree import TerminalNode

from .generated.SqlBaseParser import SqlBaseParser


@dataclass(frozen=True)
class Position:
    line: int
    column: int


@dataclass
class Column:
    """A column with a name and, where the file says so, a type."""

    name: str
    data_type: str | None  # normalised upper case, e.g. "BOOLEAN", "DECIMAL"
    raw_type: str | None  # as written, e.g. "decimal(10,2)"
    position: Position
    comment: str | None = None
    origin: str = "declaration"  # "declaration" | "cast" | "alias"

    @property
    def has_type(self) -> bool:
        return self.data_type is not None


@dataclass
class Table:
    """A table or view being created or replaced."""

    name: str
    position: Position
    columns: list[Column] = field(default_factory=list)
    provider: str | None = None  # the USING clause
    comment: str | None = None
    properties: dict[str, str] = field(default_factory=dict)
    kind: str = "table"  # "table" | "view" | "streaming_table" | "materialized_view"


@dataclass
class SelectStar:
    position: Position
    qualified: bool  # `t.*` rather than a bare `*`


@dataclass
class Analysis:
    """Everything the rules can see for one statement."""

    tables: list[Table] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)  # every named column, any origin
    select_stars: list[SelectStar] = field(default_factory=list)
    statement_kind: str = "unknown"
    drops_without_if_exists: list[tuple[str, Position]] = field(default_factory=list)
    inserts_without_column_list: list[Position] = field(default_factory=list)


# --- helpers ----------------------------------------------------------------


def _position(ctx: ParserRuleContext) -> Position:
    token = ctx.start
    return Position(line=token.line, column=token.column)


def _text(ctx) -> str:
    """Source text of a node, with original spacing where we can get it."""
    if ctx is None:
        return ""
    if isinstance(ctx, TerminalNode):
        return ctx.getText()
    try:
        stream = ctx.start.getInputStream()
        return stream.getText(ctx.start.start, ctx.stop.stop)
    except Exception:
        return ctx.getText()


def _identifier_text(ctx) -> str:
    """Identifier text with any backtick quoting removed."""
    raw = _text(ctx).strip()
    if len(raw) >= 2 and raw[0] == "`" and raw[-1] == "`":
        return raw[1:-1].replace("``", "`")
    return raw


def _string_value(ctx) -> str:
    """Contents of a string literal, quotes stripped."""
    raw = _text(ctx).strip()
    for quote in ("'", '"'):
        if len(raw) >= 2 and raw[0] == quote and raw[-1] == quote:
            return raw[1:-1]
    return raw


def normalise_type(raw: str | None) -> str | None:
    """Reduce a written type to its base name.

    `decimal(10,2)` -> `DECIMAL`, `array<int>` -> `ARRAY`. Rules match on the
    base type; parameters are kept separately on Column.raw_type for any rule
    that wants them.
    """
    if not raw:
        return None
    text = raw.strip()
    for sep in ("(", "<"):
        if sep in text:
            text = text.split(sep, 1)[0]
    return text.strip().upper() or None


# Spark spells several types more than one way. Rules should be able to say
# "TIMESTAMP" and match every spelling of it.
TYPE_ALIASES = {
    "INT": "INTEGER",
    "DEC": "DECIMAL",
    "NUMERIC": "DECIMAL",
    "REAL": "FLOAT",
    "BOOL": "BOOLEAN",
    "TIMESTAMP_LTZ": "TIMESTAMP",
    "TIMESTAMP_NTZ": "TIMESTAMP",
    "LONG": "BIGINT",
    "SHORT": "SMALLINT",
    "BYTE": "TINYINT",
    "CHAR": "STRING",
    "VARCHAR": "STRING",
}


def canonical_type(raw: str | None) -> str | None:
    base = normalise_type(raw)
    if base is None:
        return None
    return TYPE_ALIASES.get(base, base)


# --- the walker -------------------------------------------------------------


class _Analyzer:
    """Single pass over the parse tree, collecting the model above."""

    def __init__(self) -> None:
        self.analysis = Analysis()
        self._table_stack: list[Table] = []

    def run(self, tree: ParserRuleContext) -> Analysis:
        self._visit(tree)
        return self.analysis

    def _visit(self, node) -> None:
        if isinstance(node, ParserRuleContext):
            self._enter(node)
        for i in range(node.getChildCount()):
            self._visit(node.getChild(i))
        if isinstance(node, ParserRuleContext):
            self._exit(node)

    # -- per-node handling --------------------------------------------------

    def _enter(self, ctx: ParserRuleContext) -> None:
        name = type(ctx).__name__

        if name in ("CreateTableContext", "ReplaceTableContext",
                    "CreateStreamingTableContext", "CreateMaterializedViewContext"):
            kind = {
                "CreateStreamingTableContext": "streaming_table",
                "CreateMaterializedViewContext": "materialized_view",
            }.get(name, "table")
            table = Table(name=self._table_name(ctx), position=_position(ctx), kind=kind)
            self._table_stack.append(table)
            self.analysis.tables.append(table)
            if self.analysis.statement_kind == "unknown":
                self.analysis.statement_kind = kind

        elif name in ("ColDefinitionContext", "ColTypeContext"):
            column = self._column_from_definition(ctx)
            self.analysis.columns.append(column)
            if self._table_stack:
                self._table_stack[-1].columns.append(column)

        elif name == "NamedExpressionContext":
            aliased = self._column_from_named_expression(ctx)
            if aliased is not None:
                self.analysis.columns.append(aliased)

        elif name == "StarContext":
            self.analysis.select_stars.append(
                SelectStar(position=_position(ctx), qualified="." in _text(ctx))
            )

        elif name == "TableProviderContext" and self._table_stack:
            self._table_stack[-1].provider = _identifier_text(
                ctx.multipartIdentifier()
            ).lower()

        elif name == "CommentSpecContext" and self._table_stack:
            # A commentSpec inside a column definition belongs to that column and
            # is handled there; this one is the table's own COMMENT.
            if not self._inside(ctx, ("ColDefinitionContext", "ColTypeContext")):
                self._table_stack[-1].comment = _string_value(ctx.stringLit())

        elif name == "PropertyContext" and self._table_stack:
            self._record_property(ctx)

        elif name in ("DropTableContext", "DropViewContext"):
            if not self._has_if_exists(ctx):
                kind = "table" if name == "DropTableContext" else "view"
                self.analysis.drops_without_if_exists.append((kind, _position(ctx)))

        elif name in ("InsertIntoTableContext", "InsertOverwriteTableContext"):
            # `INSERT INTO t (a, b) SELECT ...` and `INSERT INTO t BY NAME ...`
            # both bind values to named columns. A bare `INSERT INTO t SELECT *`
            # binds by position, which breaks silently when the table changes.
            if ctx.identifierList() is None and not self._has_by_name(ctx):
                self.analysis.inserts_without_column_list.append(_position(ctx))

    def _exit(self, ctx: ParserRuleContext) -> None:
        name = type(ctx).__name__
        if name in ("CreateTableContext", "ReplaceTableContext",
                    "CreateStreamingTableContext", "CreateMaterializedViewContext"):
            if self._table_stack:
                self._table_stack.pop()

    # -- extraction helpers -------------------------------------------------

    @staticmethod
    def _has_token(ctx: ParserRuleContext, *token_types: int) -> bool:
        """True when ctx has these tokens as direct children, in order."""
        found = 0
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if isinstance(child, TerminalNode) and child.symbol.type == token_types[found]:
                found += 1
                if found == len(token_types):
                    return True
            elif found and isinstance(child, TerminalNode):
                found = 0
        return False

    @classmethod
    def _has_if_exists(cls, ctx: ParserRuleContext) -> bool:
        return cls._has_token(ctx, SqlBaseParser.IF, SqlBaseParser.EXISTS)

    @classmethod
    def _has_by_name(cls, ctx: ParserRuleContext) -> bool:
        return cls._has_token(ctx, SqlBaseParser.BY, SqlBaseParser.NAME)

    @staticmethod
    def _inside(ctx: ParserRuleContext, names: tuple[str, ...]) -> bool:
        parent = ctx.parentCtx
        while parent is not None:
            if type(parent).__name__ in names:
                return True
            parent = parent.parentCtx
        return False

    def _table_name(self, ctx: ParserRuleContext) -> str:
        for child_name in ("createTableHeader", "replaceTableHeader"):
            getter = getattr(ctx, child_name, None)
            if getter is not None:
                header = getter()
                if header is not None:
                    ref = header.identifierReference()
                    if ref is not None:
                        return _identifier_text(ref)
        getter = getattr(ctx, "identifierReference", None)
        if getter is not None:
            ref = getter()
            if ref is not None:
                return _identifier_text(ref if not isinstance(ref, list) else ref[0])
        return ""

    def _column_from_definition(self, ctx: ParserRuleContext) -> Column:
        name_ctx = ctx.errorCapturingIdentifier()
        raw_type = _text(ctx.dataType())
        comment = None
        for child_index in range(ctx.getChildCount()):
            child = ctx.getChild(child_index)
            if type(child).__name__ == "CommentSpecContext":
                comment = _string_value(child.stringLit())
            elif type(child).__name__ == "ColDefinitionOptionContext":
                for i in range(child.getChildCount()):
                    sub = child.getChild(i)
                    if type(sub).__name__ == "CommentSpecContext":
                        comment = _string_value(sub.stringLit())
        return Column(
            name=_identifier_text(name_ctx),
            data_type=canonical_type(raw_type),
            raw_type=raw_type,
            position=_position(name_ctx if name_ctx is not None else ctx),
            comment=comment,
            origin="declaration",
        )

    def _column_from_named_expression(self, ctx: ParserRuleContext) -> Column | None:
        """A select-list entry. Typed only when it is an explicit CAST."""
        name_ctx = getattr(ctx, "name", None)
        if name_ctx is None:
            return None  # no alias; nothing to name-check
        expression = ctx.expression()
        raw_type = self._cast_target_type(expression)
        return Column(
            name=_identifier_text(name_ctx),
            data_type=canonical_type(raw_type),
            raw_type=raw_type,
            position=_position(name_ctx),
            origin="cast" if raw_type else "alias",
        )

    def _cast_target_type(self, node) -> str | None:
        """The target type of a CAST, when the expression is exactly one.

        `CAST(x AS BOOLEAN) AS flag` gives BOOLEAN. `CAST(a AS INT) + 1` does
        not -- the expression is an addition, not a cast, and inferring the
        result type is analysis we deliberately do not do.
        """
        current = node
        # Unwrap single-child chains down to the operative node.
        while current is not None and isinstance(current, ParserRuleContext):
            name = type(current).__name__
            if name in ("CastContext", "CastByColonContext"):
                data_type = current.dataType()
                return _text(data_type) if data_type is not None else None
            if current.getChildCount() != 1:
                return None
            current = current.getChild(0)
        return None

    def _record_property(self, ctx: ParserRuleContext) -> None:
        key_ctx = getattr(ctx, "key", None)
        value_ctx = getattr(ctx, "value", None)
        if key_ctx is None:
            return
        key = _string_value(key_ctx() if callable(key_ctx) else key_ctx)
        value = ""
        if value_ctx is not None:
            resolved = value_ctx() if callable(value_ctx) else value_ctx
            if resolved is not None:
                value = _string_value(resolved)
        self._table_stack[-1].properties[key] = value


def analyse(tree: ParserRuleContext | None) -> Analysis:
    """Build the semantic model for one parsed statement."""
    if tree is None:
        return Analysis()
    return _Analyzer().run(tree)


__all__ = [
    "Analysis",
    "Column",
    "Position",
    "SelectStar",
    "Table",
    "analyse",
    "canonical_type",
    "normalise_type",
    "SqlBaseParser",
]
