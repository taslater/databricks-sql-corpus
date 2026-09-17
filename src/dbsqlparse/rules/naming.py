"""Naming rules: type-based patterns and general identifier style.

Neither rule carries an opinion of its own. `type-naming` does nothing until a
config supplies patterns, and `identifier-case` defaults to the least
controversial setting available. What a column should be called is a decision
for the team adopting this tool, not for the tool.
"""
from __future__ import annotations

import re
from typing import Any, ClassVar, Iterable

from ..analysis import canonical_type
from .base import ConfigError, Rule, RuleContext, Violation
from .registry import register

CASE_PATTERNS = {
    "snake": re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$"),
    "upper_snake": re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$"),
    "camel": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "pascal": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
}


@register
class TypeNamingRule(Rule):
    """Require column names to match a pattern determined by their type."""

    id: ClassVar[str] = "type-naming"
    description: ClassVar[str] = (
        "Column names must match a regex chosen by their declared type, "
        "e.g. BOOLEAN columns ending in _ind"
    )
    default_severity: ClassVar[str] = "error"
    defaults: ClassVar[dict[str, Any]] = {
        # Canonical type name -> regex the column name must match.
        "patterns": {},
        # Where a type may be read from. "declaration" is a CREATE TABLE column
        # type; "cast" is an explicit CAST(x AS T) AS name in a select list.
        # Columns whose type cannot be resolved locally are always skipped --
        # this rule never guesses.
        "origins": ["declaration", "cast"],
    }

    def validate(self) -> None:
        patterns = self.options["patterns"]
        if not isinstance(patterns, dict):
            raise ConfigError(f"rule '{self.id}': 'patterns' must be a table of type = regex")
        for type_name, pattern in patterns.items():
            if not isinstance(pattern, str):
                raise ConfigError(
                    f"rule '{self.id}': pattern for {type_name!r} must be a string"
                )
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigError(
                    f"rule '{self.id}': pattern for {type_name!r} is not a valid regex: {exc}"
                ) from exc
        for origin in self.options["origins"]:
            if origin not in ("declaration", "cast", "alias"):
                raise ConfigError(
                    f"rule '{self.id}': unknown origin {origin!r}; "
                    f"valid values are declaration, cast, alias"
                )

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        patterns = {
            (canonical_type(k) or k.upper()): re.compile(v)
            for k, v in self.options["patterns"].items()
        }
        if not patterns:
            return
        origins = set(self.options["origins"])

        for column in ctx.analysis.columns:
            if column.origin not in origins or not column.has_type:
                continue
            pattern = patterns.get(column.data_type)
            if pattern is None:
                continue
            if not pattern.search(column.name):
                yield self.violation(
                    ctx,
                    column.position,
                    f"{column.data_type} column '{column.name}' does not match "
                    f"the required pattern",
                    suggestion=f"expected to match /{pattern.pattern}/",
                )


@register
class IdentifierCaseRule(Rule):
    """Require identifiers to follow one casing convention."""

    id: ClassVar[str] = "identifier-case"
    description: ClassVar[str] = "Identifiers must use a consistent case convention"
    default_severity: ClassVar[str] = "error"
    defaults: ClassVar[dict[str, Any]] = {
        "case": "snake",
        # Which identifiers to check.
        "columns": True,
        "tables": True,
    }

    def validate(self) -> None:
        case = self.options["case"]
        if case not in CASE_PATTERNS:
            raise ConfigError(
                f"rule '{self.id}': unknown case {case!r}; "
                f"valid values are {', '.join(sorted(CASE_PATTERNS))}"
            )

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        pattern = CASE_PATTERNS[self.options["case"]]
        style = self.options["case"]

        if self.options["columns"]:
            for column in ctx.analysis.columns:
                if not pattern.match(column.name):
                    yield self.violation(
                        ctx,
                        column.position,
                        f"column '{column.name}' is not {style} case",
                    )

        if self.options["tables"]:
            for table in ctx.analysis.tables:
                # Check each part of catalog.schema.table separately.
                for part in table.name.split("."):
                    if part and not pattern.match(part):
                        yield self.violation(
                            ctx,
                            table.position,
                            f"table name part '{part}' is not {style} case",
                        )
                        break


@register
class IdentifierLengthRule(Rule):
    """Cap identifier length."""

    id: ClassVar[str] = "identifier-length"
    description: ClassVar[str] = "Identifiers must not exceed a maximum length"
    default_severity: ClassVar[str] = "warning"
    defaults: ClassVar[dict[str, Any]] = {"max_length": 128}

    def validate(self) -> None:
        value = self.options["max_length"]
        if not isinstance(value, int) or value < 1:
            raise ConfigError(f"rule '{self.id}': 'max_length' must be a positive integer")

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        limit = self.options["max_length"]
        for column in ctx.analysis.columns:
            if len(column.name) > limit:
                yield self.violation(
                    ctx,
                    column.position,
                    f"column '{column.name}' is {len(column.name)} characters, "
                    f"over the limit of {limit}",
                )


@register
class ForbiddenNameRule(Rule):
    """Ban names matching any of a list of patterns."""

    id: ClassVar[str] = "forbidden-name"
    description: ClassVar[str] = "Identifiers must not match any forbidden pattern"
    default_severity: ClassVar[str] = "error"
    defaults: ClassVar[dict[str, Any]] = {
        # Regex -> human explanation shown when it matches.
        "patterns": {},
        "columns": True,
        "tables": True,
    }

    def validate(self) -> None:
        patterns = self.options["patterns"]
        if not isinstance(patterns, dict):
            raise ConfigError(
                f"rule '{self.id}': 'patterns' must be a table of regex = reason"
            )
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigError(
                    f"rule '{self.id}': {pattern!r} is not a valid regex: {exc}"
                ) from exc

    def check(self, ctx: RuleContext) -> Iterable[Violation]:
        compiled = [(re.compile(p), reason) for p, reason in self.options["patterns"].items()]
        if not compiled:
            return

        targets = []
        if self.options["columns"]:
            targets += [(c.name, c.position, "column") for c in ctx.analysis.columns]
        if self.options["tables"]:
            targets += [(t.name, t.position, "table") for t in ctx.analysis.tables]

        for name, position, kind in targets:
            for pattern, reason in compiled:
                if pattern.search(name):
                    yield self.violation(
                        ctx,
                        position,
                        f"{kind} '{name}' matches forbidden pattern /{pattern.pattern}/",
                        suggestion=reason or None,
                    )
                    break
