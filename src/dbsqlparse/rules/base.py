"""Rule framework: what a rule is, and what it is handed.

A rule receives an `Analysis` (see dbsqlparse.analysis) rather than a parse
tree, so writing one needs no knowledge of ANTLR or of Spark's grammar.

Rules are configured, never hard-coded. This project ships no opinion about
what a column should be called -- the naming rules are empty until a config
supplies patterns. Conventions belong to the team adopting the tool, and
examples/ carries several as starting points.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable

from ..analysis import Analysis, Position

SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Violation:
    """One rule firing at one place."""

    rule: str
    message: str
    line: int
    column: int
    severity: str = "error"
    path: str | None = None
    # What would satisfy the rule, when that can be stated concretely.
    suggestion: str | None = None

    def format(self) -> str:
        where = self.path or "<stdin>"
        text = f"{where}:{self.line}:{self.column + 1}: {self.severity}: [{self.rule}] {self.message}"
        if self.suggestion:
            text += f" ({self.suggestion})"
        return text


@dataclass
class RuleContext:
    """Everything a rule can see about one statement."""

    analysis: Analysis
    sql: str
    path: str | None = None
    # Offset of this statement within the file, so positions come out right.
    line_offset: int = 0

    def at(self, position: Position) -> tuple[int, int]:
        return position.line + self.line_offset, position.column


class ConfigError(ValueError):
    """Raised for a config a human needs to fix, with a message saying how."""


@dataclass
class Rule:
    """Base class for rules.

    Subclasses set `id` and `description`, optionally declare `defaults`, and
    implement `check`. Registration is by decorator in registry.py.
    """

    id: ClassVar[str] = ""
    description: ClassVar[str] = ""
    # Option name -> default value. Anything not listed here is rejected at
    # config load, so a typo in a config key is an error rather than a setting
    # that silently does nothing.
    defaults: ClassVar[dict[str, Any]] = {}
    default_severity: ClassVar[str] = "error"

    options: dict[str, Any] = field(default_factory=dict)
    severity: str = "error"

    def __post_init__(self) -> None:
        merged = dict(self.defaults)
        merged.update(self.options)
        self.options = merged

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Rule":
        options = {k: v for k, v in config.items() if k != "severity"}
        unknown = set(options) - set(cls.defaults)
        if unknown:
            known = ", ".join(sorted(cls.defaults)) or "(none)"
            raise ConfigError(
                f"rule '{cls.id}': unknown option(s) {sorted(unknown)}. "
                f"Valid options: {known}"
            )
        severity = config.get("severity", cls.default_severity)
        if severity not in SEVERITIES:
            raise ConfigError(
                f"rule '{cls.id}': severity must be one of {', '.join(SEVERITIES)}, "
                f"got {severity!r}"
            )
        rule = cls(options=options, severity=severity)
        rule.validate()
        return rule

    def validate(self) -> None:
        """Check options beyond their names. Override where it helps."""

    def check(self, ctx: RuleContext) -> Iterable[Violation]:  # pragma: no cover
        raise NotImplementedError

    # -- convenience for subclasses ----------------------------------------

    def violation(
        self,
        ctx: RuleContext,
        position: Position,
        message: str,
        suggestion: str | None = None,
    ) -> Violation:
        line, column = ctx.at(position)
        return Violation(
            rule=self.id,
            message=message,
            line=line,
            column=column,
            severity=self.severity,
            path=ctx.path,
            suggestion=suggestion,
        )
