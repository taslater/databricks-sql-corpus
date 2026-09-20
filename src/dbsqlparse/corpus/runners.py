"""The parsers under test.

This project used to ship its own parser and measure that. It no longer does:
SQLFluff parses Databricks SQL better than we did, so the corpus now measures
SQLFluff and the failures become upstream pull requests.

A runner is anything that can answer "does this parse?". Three exist:

    SqlFluffRunner -- the subject. Run in-process against whichever SQLFluff is
                      installed, which is the point: `pip install -e
                      ../sqlfluff` inside a fork checkout measures an unmerged
                      branch, and that is the main workflow.
    SqruffRunner   -- a fast second opinion. When a file fails, a second parser
                      agreeing makes it likely the SQL is broken; a second
                      parser disagreeing makes it likely a real SQLFluff gap.
                      That was the job our own parser did, and sqruff does it
                      ~20x faster. It is largely a port of SQLFluff, though, so
                      its disagreements mostly measure port lag.
    SqlglotRunner  -- an independent second opinion, used only by `make diff`.
                      sqlglot is a different implementation of a Databricks
                      dialect, so a disagreement is real information -- with
                      one asymmetry: it is deliberately lenient, so its
                      *rejections* are the signal and its *acceptances* are
                      not. See docs/sqlglot-plan.md.

None of the runners lints. Rules are switched off so that only parse errors
count -- a style complaint is not a gap.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str | None = None
    line: int | None = None


class Runner(Protocol):
    name: str

    def version(self) -> str: ...

    def check(self, text: str, path: str) -> CheckResult: ...

    def check_many(self, paths: list[pathlib.Path]) -> dict[str, CheckResult]: ...


class SqlFluffRunner:
    """SQLFluff, in-process.

    Deciding "did this parse?" needs all three of these. `violations` alone
    misses a tree that parsed into `unparsable` nodes without raising, and
    `parsed.tree` itself asserts rather than returning None when the root
    variant failed, which is why the AssertionError is caught rather than
    guarded with a None check.
    """

    name = "sqlfluff"

    def __init__(self, dialect: str = "databricks") -> None:
        from sqlfluff.core import FluffConfig, Linter

        self.dialect = dialect
        # A rule must be named and then excluded: an empty `rules` means "all".
        self._linter = Linter(
            config=FluffConfig(
                overrides={
                    "dialect": dialect,
                    "rules": "LT01",
                    "exclude_rules": "LT01",
                }
            )
        )

    def version(self) -> str:
        import sqlfluff

        return getattr(sqlfluff, "__version__", "unknown")

    def check(self, text: str, path: str) -> CheckResult:
        parsed = self._linter.parse_string(text, fname=path)
        try:
            tree = parsed.tree
        except AssertionError:
            tree = None
        if parsed.violations:
            v = parsed.violations[0]
            return CheckResult(False, str(getattr(v, "description", v))[:200], v.line_no)
        if tree is None:
            return CheckResult(False, "root variant not parsed", None)
        unparsable = list(tree.recursive_crawl("unparsable"))
        if unparsable:
            loc = unparsable[0].get_start_loc()
            return CheckResult(False, "unparsable section", loc[0])
        return CheckResult(True)

    def check_many(self, paths: list[pathlib.Path]) -> dict[str, CheckResult]:
        out = {}
        for p in paths:
            text = p.read_text(encoding="utf-8", errors="replace")
            out[str(p)] = self.check(text, str(p))
        return out


class SqruffRunner:
    """sqruff, batched over the CLI.

    sqruff has no Python API, so this shells out. Two things about its CLI are
    load-bearing and cost real debugging to find:

      * findings go to STDERR, while the "processed N files" banner goes to
        stdout. Reading only stdout reports a clean 100% no matter the input.
      * a parse error is marked `????` in the finding line; lint rules carry a
        rule code instead. Only the former counts here.

    Startup is ~30ms and marginal cost ~0.6ms per file, so files are batched.
    """

    name = "sqruff"
    _FAIL = re.compile(r"^== \[(.+?)\] FAIL")
    _PARSE_ERR = re.compile(r"\|\s+\?{4}\s+\|")
    BATCH = 200

    def __init__(self, dialect: str = "databricks", config: str | None = None) -> None:
        self.dialect = dialect
        self._config = config

    @staticmethod
    def available() -> bool:
        return shutil.which("sqruff") is not None

    def version(self) -> str:
        try:
            proc = subprocess.run(
                ["sqruff", "--version"], capture_output=True, text=True
            )
        except OSError:
            return "unknown"
        lines = (proc.stdout + proc.stderr).splitlines()
        return lines[0].strip() if lines else "unknown"

    def _args(self) -> list[str]:
        args = ["sqruff", "lint", "--dialect", self.dialect, "--parsing-errors"]
        if self._config:
            args[2:2] = ["--config", self._config]
        return args

    def check_many(self, paths: list[pathlib.Path]) -> dict[str, CheckResult]:
        results = {str(p): CheckResult(True) for p in paths}
        for i in range(0, len(paths), self.BATCH):
            chunk = [str(p) for p in paths[i : i + self.BATCH]]
            proc = subprocess.run(
                [*self._args(), *chunk], capture_output=True, text=True
            )
            current = None
            for line in (proc.stdout + proc.stderr).splitlines():
                m = self._FAIL.match(line)
                if m:
                    current = m.group(1)
                    continue
                if current and self._PARSE_ERR.search(line):
                    results[current] = CheckResult(False, line.strip()[:200])
                    current = None
        return results

    def check(self, text: str, path: str) -> CheckResult:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "probe.sql"
            f.write_text(text, encoding="utf-8")
            return self.check_many([f])[str(f)]


class SqlglotRunner:
    """sqlglot, in-process -- an independent second opinion, never an oracle.

    sqlglot documents itself as lenient ("the parser is intentionally lenient,
    so it can accept queries that a real engine would reject") and in practice
    accepts `SELECT a,, b FROM t`, which mutate.py tiers as GUARANTEED-invalid.
    That asymmetry is why this runner exists only for `make diff`: a rejection
    is evidence worth triaging, an acceptance is not evidence the SQL is valid.

    Verified before it was trusted (sqlglot 30.18.0, 2026-09-19):

        SELECT 1                          parses
        -- MAGIC comments and multi-statement files   parse
        SELECT a FROM ((t;                ParseError, line 1 col 17
        SELECT a +                        ParseError, line 1 col 10
        SELECT a,, b FROM t               parses  <- leniency, by design

    A second leniency has to be neutralised rather than logged: for syntax it
    does not model, sqlglot warns and returns the whole statement as an opaque
    `Command` node. That is acceptance without understanding -- `CREATE CATALOG
    c`, `CREATE FLOW ...`, `OPTIMIZE t` and `VACUUM t` all land there -- and
    counting it as a parse would fabricate agreement and mask exactly the
    over-acceptances this report is for. A top-level `Command` therefore counts
    as failure, and the logger that announces it is quietened, because a corpus
    run would otherwise drown the report in thousands of fallback lines.

    Both a raised error and errors attached to a returned expression count as
    failure; the one-check habit is how a harness reports a clean 100% by
    accident.
    """

    name = "sqlglot"

    def __init__(self, dialect: str = "databricks") -> None:
        import logging

        import sqlglot

        # The "Falling back to parsing as a 'Command'" warning fires once per
        # statement on a corpus run. It is expected, handled below, and not
        # worth printing thousands of times.
        logging.getLogger("sqlglot").setLevel(logging.ERROR)
        self._sqlglot = sqlglot
        self.dialect = dialect

    def version(self) -> str:
        return getattr(self._sqlglot, "__version__", "unknown")

    def check(self, text: str, path: str) -> CheckResult:
        from sqlglot import exp
        from sqlglot.errors import ErrorLevel, SqlglotError

        try:
            expressions = self._sqlglot.parse(
                text, read=self.dialect, error_level=ErrorLevel.RAISE
            )
        except SqlglotError as error:
            return _sqlglot_failure(error)
        for expression in expressions:
            errors = getattr(expression, "errors", None) or []
            if errors:
                return _sqlglot_failure(errors[0])
            if isinstance(expression, exp.Command):
                return CheckResult(
                    False,
                    "unsupported syntax: sqlglot fell back to an opaque Command",
                )
        return CheckResult(True)

    def check_many(self, paths: list[pathlib.Path]) -> dict[str, CheckResult]:
        out = {}
        for p in paths:
            text = p.read_text(encoding="utf-8", errors="replace")
            out[str(p)] = self.check(text, str(p))
        return out


def _sqlglot_failure(error) -> CheckResult:
    """Turn a SqlglotError or one of its error dicts into a CheckResult."""
    if isinstance(error, dict):
        description = str(error.get("description", error))[:200]
        return CheckResult(False, description, error.get("line"))
    errors = getattr(error, "errors", None) or []
    if errors:
        return _sqlglot_failure(errors[0])
    return CheckResult(False, str(error)[:200])


def get_runner(name: str, dialect: str = "databricks") -> Runner:
    if name == "sqlfluff":
        return SqlFluffRunner(dialect=dialect)
    if name == "sqruff":
        if not SqruffRunner.available():
            raise SystemExit(
                "sqruff is not on PATH. Install it (brew install sqruff) or use "
                "--runner sqlfluff."
            )
        return SqruffRunner(dialect=dialect)
    if name == "sqlglot":
        return SqlglotRunner(dialect=dialect)
    raise SystemExit(
        f"unknown runner {name!r}; expected 'sqlfluff', 'sqruff' or 'sqlglot'"
    )
