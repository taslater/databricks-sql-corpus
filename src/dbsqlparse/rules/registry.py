"""Rule registry.

Rules register themselves with `@register`. Keeping the registry separate from
the base class avoids an import cycle and gives one place to ask "what rules
exist?", which the CLI uses for `--list-rules`.
"""
from __future__ import annotations

from typing import Iterator

from .base import ConfigError, Rule

_REGISTRY: dict[str, type[Rule]] = {}


def register(cls: type[Rule]) -> type[Rule]:
    if not cls.id:
        raise ValueError(f"{cls.__name__} must set a non-empty id")
    if cls.id in _REGISTRY and _REGISTRY[cls.id] is not cls:
        raise ValueError(f"duplicate rule id {cls.id!r} ({cls.__name__})")
    _REGISTRY[cls.id] = cls
    return cls


def get(rule_id: str) -> type[Rule]:
    try:
        return _REGISTRY[rule_id]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY)) or "(none registered)"
        raise ConfigError(f"unknown rule {rule_id!r}. Available rules: {known}") from None


def all_rules() -> Iterator[type[Rule]]:
    for rule_id in sorted(_REGISTRY):
        yield _REGISTRY[rule_id]


def rule_ids() -> list[str]:
    return sorted(_REGISTRY)
