"""Diff a fresh corpus report against the committed baseline.

Reporting only, never gating. `corpus/reports/baseline.json` is committed so an
accuracy change arrives as a reviewable diff, and whether a change is a
regression is a judgement: adding a source that exposes a known gap lowers the
headline number without anything having got worse, and that is progress, not a
failure. This script exists so a human making that call has the numbers in
front of them rather than having to read two JSON files side by side.

A non-zero exit marks the CI job, which is configured not to block the build.

    python scripts/compare_baseline.py baseline.json new.json
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

# Anything below this is rounding on a small source, not a signal.
EPSILON = 0.05


def load(path: str) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())


def sources_by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["name"]: s for s in report.get("sources", [])}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    base, new = load(argv[0]), load(argv[1])
    old_s, new_s = sources_by_name(base), sources_by_name(new)

    rows: list[str] = []
    regressed: list[str] = []

    for name in sorted(set(old_s) | set(new_s)):
        o, n = old_s.get(name), new_s.get(name)
        if o is None:
            rows.append(f"| `{name}` | — | {n['rate']:.1f}% | new source |")
            continue
        if n is None:
            rows.append(f"| `{name}` | {o['rate']:.1f}% | — | **removed** |")
            regressed.append(f"{name}: source removed")
            continue
        delta = n["rate"] - o["rate"]
        if abs(delta) < EPSILON:
            note = "unchanged"
        elif delta > 0:
            note = f"+{delta:.1f} pt"
        else:
            note = f"**{delta:.1f} pt**"
            regressed.append(f"{name}: {o['rate']:.1f}% -> {n['rate']:.1f}%")
        rows.append(f"| `{name}` | {o['rate']:.1f}% | {n['rate']:.1f}% | {note} |")

    print("## Corpus accuracy\n")
    print("### Recall, by source\n")
    print("| source | baseline | this run | change |")
    print("| --- | ---: | ---: | --- |")
    print("\n".join(rows))

    ob = (base.get("mutation") or {}).get("rejection_rate")
    nb = (new.get("mutation") or {}).get("rejection_rate")
    if ob is not None and nb is not None:
        n_tot = (new.get("mutation") or {}).get("guaranteed_total", 0)
        print(f"\n### Rejection\n\n{ob:.1f}% -> **{nb:.1f}%** on {n_tot} guaranteed mutations")
        if nb < ob - EPSILON:
            regressed.append(f"rejection: {ob:.1f}% -> {nb:.1f}%")

    if regressed:
        print("\n> [!WARNING]")
        print("> Accuracy fell. If this is intentional, regenerate the baseline")
        print("> and say why in the commit message:")
        for r in regressed:
            print(f"> - {r}")
        return 1

    print("\nNo accuracy regression against the committed baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
