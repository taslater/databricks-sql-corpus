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


def _reference_diff(base: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Compare the reference section case by case, and print the summary.

    Case-level rather than rate-level on purpose: a rate can hide a case
    flipping conforming -> not behind two new cases that happen to fail on
    arrival. A newly added case that fails is new coverage, like a new source,
    and is reported rather than gated. A case that used to conform and no
    longer does is a regression, and so is a case that disappears -- removal
    is how a check silently stops checking.
    """
    new_ref = new.get("reference")
    if new_ref is None:
        return []
    old_ref = base.get("reference") or {}
    old_cases = {c["id"]: c for c in old_ref.get("cases", [])}
    new_cases = {c["id"]: c for c in new_ref.get("cases", [])}
    new_mp, new_mr = new_ref.get("must_parse", {}), new_ref.get("must_reject", {})
    old_mp, old_mr = old_ref.get("must_parse", {}), old_ref.get("must_reject", {})

    print("\n### Reference conformance\n")
    if not old_ref:
        print(
            f"New reference corpus: {new_mp.get('total', 0)} must-parse and "
            f"{new_mr.get('total', 0)} must-reject cases."
        )
    else:
        print("| metric | baseline | this run |")
        print("| --- | ---: | ---: |")
        print(
            f"| must-parse passed | {old_mp.get('passed')}/{old_mp.get('total')} | "
            f"**{new_mp.get('passed')}/{new_mp.get('total')}** |"
        )
        print(
            f"| must-reject caught | {old_mr.get('caught')}/{old_mr.get('total')} | "
            f"**{new_mr.get('caught')}/{new_mr.get('total')}** "
            f"({new_mr.get('informative', 0)} informative, "
            f"{new_mr.get('vacuous', 0)} vacuous) |"
        )

    regressed: list[str] = []
    if new_ref.get("controls_ok") is False:
        regressed.append("reference controls failed")

    flips = [
        cid for cid, case in old_cases.items()
        if cid in new_cases and case.get("ok") and not new_cases[cid].get("ok")
    ]
    added = [cid for cid in new_cases if cid not in old_cases]
    failing_on_arrival = [cid for cid in added if not new_cases[cid].get("ok")]
    removed = [cid for cid in old_cases if cid not in new_cases]
    regressed.extend(f"reference case {cid}: conforming -> not" for cid in flips)
    regressed.extend(f"reference case removed: {cid}" for cid in removed)

    notes = []
    if added:
        line = f"{len(added)} new case(s), {len(failing_on_arrival)} failing on arrival"
        if failing_on_arrival:
            line += ": " + ", ".join(failing_on_arrival[:5])
        notes.append(line)
    if flips:
        notes.append("regressed: " + ", ".join(flips))
    if removed:
        notes.append("removed: " + ", ".join(removed))
    old_vacuous, new_vacuous = old_mr.get("vacuous", 0), new_mr.get("vacuous", 0)
    if old_ref and old_vacuous != new_vacuous:
        notes.append(f"vacuous rejections: {old_vacuous} -> {new_vacuous}")
    for note in notes:
        print(f"\n- {note}")
    return regressed


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

    regressed.extend(_reference_diff(base, new))

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
