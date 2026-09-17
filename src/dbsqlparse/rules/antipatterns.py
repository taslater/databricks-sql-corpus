"""Rules against patterns that are legal SQL but usually a mistake.

These carry no naming opinion at all, so they are the rules most likely to be
useful to a team that shares none of your conventions.
"""
from __future__ import annotations

from typing import Any, ClassVar, Iterable

from .base import Rule, RuleContext, Violation
from .registry import register


@register
class NoSelectStarRule(Rule):
    """Flag `SELECT *`.

    A star binds to whatever columns the source has at run time, so adding a
    column upstream silently changes what a downstream table contains.
    """

    id: ClassVar[str] = "no-select-star"
    description: ClassVar[str] = "SELECT * hides schema changes; list columns explicitly"
    default_severity: ClassVar[str] = "warning"
    defaults: ClassVar[dict[str, Any]] = {
        # `t.*` is narrower than a bare `*` and some teams allow it.
        "allow_qualified": False,
    }

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        for star in ctx.analysis.select_stars:
            if star.qualified and self.options["allow_qualified"]:
                continue
            what = "t.*" if star.qualified else "SELECT *"
            yield self.violation(
                ctx,
                star.position,
                f"{what} binds to whatever columns exist at run time",
                suggestion="list the columns explicitly",
            )


@register
class DropRequiresIfExistsRule(Rule):
    """Require IF EXISTS on DROP.

    Without it, a re-run of a script fails on the first already-dropped object,
    which in a pipeline means a partial deploy.
    """

    id: ClassVar[str] = "drop-requires-if-exists"
    description: ClassVar[str] = "DROP statements must use IF EXISTS to stay re-runnable"
    default_severity: ClassVar[str] = "error"
    defaults: ClassVar[dict[str, Any]] = {}

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        for kind, position in ctx.analysis.drops_without_if_exists:
            yield self.violation(
                ctx,
                position,
                f"DROP {kind.upper()} without IF EXISTS is not re-runnable",
                suggestion=f"DROP {kind.upper()} IF EXISTS ...",
            )


@register
class InsertRequiresColumnListRule(Rule):
    """Require INSERT to name its columns.

    A bare `INSERT INTO t SELECT ...` binds by position. Add a column to either
    side and the data lands in the wrong column with no error, provided the
    types happen to line up.
    """

    id: ClassVar[str] = "insert-requires-column-list"
    description: ClassVar[str] = (
        "INSERT must name its target columns, or use BY NAME, rather than "
        "binding by position"
    )
    default_severity: ClassVar[str] = "warning"
    defaults: ClassVar[dict[str, Any]] = {}

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        for position in ctx.analysis.inserts_without_column_list:
            yield self.violation(
                ctx,
                position,
                "INSERT binds columns by position",
                suggestion="name the columns, or use INSERT INTO ... BY NAME",
            )
