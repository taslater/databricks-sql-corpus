"""Configurable lint rules.

This package ships the rule *engine* and a set of rule implementations. It
ships no conventions: every rule is inert until a config turns it on, and the
naming rules do nothing until a config supplies patterns. Conventions belong to
the team adopting the tool -- see examples/ for several, including two that
deliberately contradict each other.

To add a rule: subclass Rule, set an id and description, declare `defaults` for
every option it accepts, implement `check`, and decorate with `@register`. Rules
see the semantic model in dbsqlparse.analysis, never ANTLR contexts.
"""
from __future__ import annotations

from .base import ConfigError, Rule, RuleContext, Violation
from .config import Config, describe_rules, find_config, load_config, load_for_path
from .registry import all_rules, get, register, rule_ids

# Importing these modules is what registers their rules.
from . import antipatterns, metadata, naming  # noqa: E402,F401  (side-effect import)

__all__ = [
    "Config",
    "ConfigError",
    "Rule",
    "RuleContext",
    "Violation",
    "all_rules",
    "describe_rules",
    "find_config",
    "get",
    "load_config",
    "load_for_path",
    "register",
    "rule_ids",
]
