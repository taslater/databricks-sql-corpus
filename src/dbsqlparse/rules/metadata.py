"""Rules about metadata a table is expected to carry.

Useful to data platform teams regardless of naming conventions: documentation
requirements, storage format, and table properties are the things most likely
to be agreed across a whole organisation.
"""
from __future__ import annotations

from typing import Any, ClassVar, Iterable

from .base import ConfigError, Rule, RuleContext, Violation
from .registry import register


@register
class RequireCommentRule(Rule):
    """Require COMMENT on tables and/or columns."""

    id: ClassVar[str] = "require-comment"
    description: ClassVar[str] = "Tables and columns must carry a COMMENT"
    default_severity: ClassVar[str] = "warning"
    defaults: ClassVar[dict[str, Any]] = {
        "tables": True,
        "columns": False,
        # A comment of only whitespace, or shorter than this, does not count.
        # Defaults to 1 so that an empty COMMENT '' is still caught.
        "min_length": 1,
    }

    def validate(self) -> None:
        if not isinstance(self.options["min_length"], int) or self.options["min_length"] < 0:
            raise ConfigError(f"rule '{self.id}': 'min_length' must be a non-negative integer")

    def _missing(self, comment: str | None) -> bool:
        return comment is None or len(comment.strip()) < self.options["min_length"]

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        for table in ctx.analysis.tables:
            if self.options["tables"] and self._missing(table.comment):
                yield self.violation(
                    ctx, table.position, f"table '{table.name}' has no COMMENT"
                )
            if self.options["columns"]:
                for column in table.columns:
                    if self._missing(column.comment):
                        yield self.violation(
                            ctx,
                            column.position,
                            f"column '{column.name}' has no COMMENT",
                        )


@register
class RequireTablePropertiesRule(Rule):
    """Require particular TBLPROPERTIES keys, optionally with set values."""

    id: ClassVar[str] = "require-table-properties"
    description: ClassVar[str] = "Tables must set particular TBLPROPERTIES"
    default_severity: ClassVar[str] = "warning"
    defaults: ClassVar[dict[str, Any]] = {
        # Keys that must be present, whatever their value.
        "required_keys": [],
        # Key -> the exact value it must have.
        "required_values": {},
    }

    def validate(self) -> None:
        if not isinstance(self.options["required_keys"], list):
            raise ConfigError(f"rule '{self.id}': 'required_keys' must be a list")
        if not isinstance(self.options["required_values"], dict):
            raise ConfigError(f"rule '{self.id}': 'required_values' must be a table")

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        required_keys = list(self.options["required_keys"])
        required_values = dict(self.options["required_values"])
        if not required_keys and not required_values:
            return

        for table in ctx.analysis.tables:
            for key in required_keys:
                if key not in table.properties:
                    yield self.violation(
                        ctx,
                        table.position,
                        f"table '{table.name}' is missing required property '{key}'",
                    )
            for key, expected in required_values.items():
                actual = table.properties.get(key)
                if actual is None:
                    yield self.violation(
                        ctx,
                        table.position,
                        f"table '{table.name}' is missing required property '{key}'",
                        suggestion=f"expected '{key}' = '{expected}'",
                    )
                elif actual != expected:
                    yield self.violation(
                        ctx,
                        table.position,
                        f"table '{table.name}' has '{key}' = '{actual}'",
                        suggestion=f"expected '{expected}'",
                    )


@register
class RequireTableProviderRule(Rule):
    """Constrain the USING clause, e.g. to delta only."""

    id: ClassVar[str] = "require-table-provider"
    description: ClassVar[str] = "Tables must be created with an allowed USING provider"
    default_severity: ClassVar[str] = "error"
    defaults: ClassVar[dict[str, Any]] = {
        "allowed": ["delta"],
        # Whether a CREATE TABLE with no USING at all is a violation. Databricks
        # defaults to delta, so this is off unless a team wants it explicit.
        "require_explicit": False,
    }

    def validate(self) -> None:
        if not isinstance(self.options["allowed"], list) or not self.options["allowed"]:
            raise ConfigError(f"rule '{self.id}': 'allowed' must be a non-empty list")

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        allowed = {str(p).lower() for p in self.options["allowed"]}
        for table in ctx.analysis.tables:
            # Views and materialized views have no storage provider.
            if table.kind in ("view", "materialized_view"):
                continue
            if table.provider is None:
                if self.options["require_explicit"]:
                    yield self.violation(
                        ctx,
                        table.position,
                        f"table '{table.name}' has no USING clause",
                        suggestion=f"expected one of: {', '.join(sorted(allowed))}",
                    )
                continue
            if table.provider not in allowed:
                yield self.violation(
                    ctx,
                    table.position,
                    f"table '{table.name}' uses provider '{table.provider}'",
                    suggestion=f"allowed: {', '.join(sorted(allowed))}",
                )
