"""The parsers under test.

This project used to ship its own parser and measure that. It no longer does:
SQLFluff parses Databricks SQL better than we did, so the corpus now measures
SQLFluff and the failures become upstream pull requests.

A runner is anything that can answer "does this parse?". Two exist:

    SqlFluffRunner -- the subject. Run in-process against whichever SQLFluff is
                      installed, which is the point: `pip install -e
                      ../sqlfluff` inside a fork checkout measures an unmerged
                      branch, and that is the main workflow.
    SqruffRunner   -- an independent second opinion. When a file fails, a
                      second parser agreeing makes it likely the SQL is broken;
                      a second parser disagreeing makes it likely a real
                      SQLFluff gap. That was the job our own parser did, and
                      sqruff does it ~20x faster.

Neither runner lints. Rules are switched off so that only parse errors count --
a style complaint is not a gap.
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
    raise SystemExit(f"unknown runner {name!r}; expected 'sqlfluff' or 'sqruff'")
