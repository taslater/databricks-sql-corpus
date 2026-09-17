"""Run the configured rules over SQL.

Parse errors and rule violations are reported through one diagnostic list, but
they are not equivalent: a file that does not parse is not checked by any rule,
because every rule reads a parse tree. The result says so explicitly rather
than reporting "0 violations" for a file nothing could be checked in -- a
silently unchecked file is how broken SQL reaches main.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from .analysis import analyse
from .parser import Diagnostic, ParseOptions, parse_text
from .rules import Config, RuleContext, Violation


@dataclass
class LintResult:
    path: str | None
    parse_errors: list[Diagnostic] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    statements_checked: int = 0

    @property
    def parsed(self) -> bool:
        return not self.parse_errors

    @property
    def ok(self) -> bool:
        return self.parsed and not self.violations

    @property
    def error_count(self) -> int:
        """Problems that should fail a build."""
        return len(self.parse_errors) + sum(
            1 for v in self.violations if v.severity == "error"
        )

    def messages(self) -> list[str]:
        """Every problem, ordered by position in the file."""
        entries: list[tuple[int, int, str]] = []
        for d in self.parse_errors:
            entries.append((d.line, d.column, d.format()))
        for v in self.violations:
            entries.append((v.line, v.column, v.format()))
        entries.sort(key=lambda e: (e[0], e[1]))
        return [text for _, _, text in entries]


def lint_text(
    text: str,
    config: Config | None = None,
    path: str | None = None,
    options: ParseOptions | None = None,
) -> LintResult:
    config = config or Config()
    if options is None:
        options = ParseOptions(
            ansi_reserved_keywords=config.ansi_reserved_keywords,
            double_quoted_identifiers=config.double_quoted_identifiers,
        )

    parsed = parse_text(text, options=options, path=path)
    result = LintResult(path=path, parse_errors=list(parsed.diagnostics))

    if not config.rules:
        return result

    for statement in parsed.statements:
        # A statement that failed to parse has no reliable tree; running rules
        # on a partial one produces confident nonsense.
        if statement.tree is None or statement.diagnostics:
            continue
        ctx = RuleContext(
            analysis=analyse(statement.tree),
            sql=statement.sql,
            path=path,
            line_offset=statement.line_offset,
        )
        result.statements_checked += 1
        for rule in config.rules:
            result.violations.extend(rule.check(ctx))

    return result


def lint_file(
    path: str | pathlib.Path,
    config: Config | None = None,
    options: ParseOptions | None = None,
) -> LintResult:
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return lint_text(text, config=config, path=str(p), options=options)
