"""Load rule configuration from TOML.

Config is discovered by walking up from the file being linted, so a monorepo
can hold different conventions per directory. Two shapes are accepted:

    # .dbsqlparse.toml
    [rules.type-naming]
    severity = "error"
    patterns = { BOOLEAN = "_ind$" }

    # pyproject.toml
    [tool.dbsqlparse.rules.type-naming]
    ...

No config means no rules: the tool still checks syntax, but stays silent about
style. That default matters for an open-source linter -- a tool that invents
naming opinions on first run gets uninstalled.
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any

from .base import ConfigError, Rule
from .registry import get as get_rule
from .registry import rule_ids

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover
        raise ConfigError(
            "Reading TOML config on Python 3.10 needs the 'tomli' package: "
            "pip install tomli (Python 3.11+ has it built in)"
        ) from None

CONFIG_FILENAMES = (".dbsqlparse.toml", "dbsqlparse.toml")
PYPROJECT = "pyproject.toml"


@dataclass
class Config:
    rules: list[Rule] = field(default_factory=list)
    source: pathlib.Path | None = None
    # Parser switches, kept alongside the rules so one file configures everything.
    ansi_reserved_keywords: bool = False
    double_quoted_identifiers: bool = False

    @property
    def has_rules(self) -> bool:
        return bool(self.rules)


def find_config(start: pathlib.Path) -> pathlib.Path | None:
    """Walk up from `start` looking for a config file."""
    start = start.resolve()
    directory = start if start.is_dir() else start.parent
    for candidate_dir in [directory, *directory.parents]:
        for name in CONFIG_FILENAMES:
            path = candidate_dir / name
            if path.is_file():
                return path
        pyproject = candidate_dir / PYPROJECT
        if pyproject.is_file():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError:
                continue
            if isinstance(data.get("tool"), dict) and "dbsqlparse" in data["tool"]:
                return pyproject
    return None


def _section(data: dict[str, Any], path: pathlib.Path) -> dict[str, Any]:
    if path.name == PYPROJECT:
        return data.get("tool", {}).get("dbsqlparse", {})
    return data


def load_config(path: pathlib.Path) -> Config:
    """Read and validate one config file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read: {exc}") from exc

    section = _section(data, path)
    if not isinstance(section, dict):
        raise ConfigError(f"{path}: expected a table of settings")

    known_keys = {"rules", "ansi_reserved_keywords", "double_quoted_identifiers"}
    unknown = set(section) - known_keys
    if unknown:
        raise ConfigError(
            f"{path}: unknown setting(s) {sorted(unknown)}. "
            f"Valid settings: {', '.join(sorted(known_keys))}"
        )

    config = Config(
        source=path,
        ansi_reserved_keywords=bool(section.get("ansi_reserved_keywords", False)),
        double_quoted_identifiers=bool(section.get("double_quoted_identifiers", False)),
    )

    rules_section = section.get("rules", {})
    if not isinstance(rules_section, dict):
        raise ConfigError(f"{path}: [rules] must be a table")

    for rule_id, rule_config in rules_section.items():
        if not isinstance(rule_config, dict):
            raise ConfigError(
                f"{path}: [rules.{rule_id}] must be a table of options, "
                f"got {type(rule_config).__name__}"
            )
        if rule_config.get("enabled") is False:
            continue
        options = {k: v for k, v in rule_config.items() if k != "enabled"}
        try:
            rule_cls = get_rule(rule_id)
            config.rules.append(rule_cls.from_config(options))
        except ConfigError as exc:
            raise ConfigError(f"{path}: {exc}") from exc

    return config


def load_for_path(path: pathlib.Path) -> Config:
    """Find and load the config governing `path`; empty Config if none."""
    found = find_config(path)
    if found is None:
        return Config()
    return load_config(found)


def describe_rules() -> str:
    """Human-readable listing of every registered rule, for --list-rules."""
    lines = ["Available rules:", ""]
    for rule_cls in [get_rule(rid) for rid in rule_ids()]:
        lines.append(f"  {rule_cls.id}")
        lines.append(f"      {rule_cls.description}")
        lines.append(f"      default severity: {rule_cls.default_severity}")
        if rule_cls.defaults:
            for key, value in sorted(rule_cls.defaults.items()):
                lines.append(f"      option: {key} = {value!r}")
        lines.append("")
    return "\n".join(lines)
