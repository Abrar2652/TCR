"""Unified command-line entry point.

Usage::

    python -m tcr.cli all          # run every experiment, write results/
    python -m tcr.cli headline      # E1: conformance gap + stability
    python -m tcr.cli selectors     # E2: selector comparison table
    python -m tcr.cli robustness    # E3: seed robustness
    python -m tcr.cli timeline      # E4: Allen-style timeline conformance
    python -m tcr.cli demo          # print the canonical leak gadget walk-through
"""
from __future__ import annotations

import sys

from tcr.experiments import (
    run_headline,
    run_selector_comparison,
    run_seed_robustness,
    run_timeline,
)


def demo() -> None:
    from tcr.cfg.membership import accepts, language_sample
    from tcr.core.types import Domain, Method, RepairInstance
    from tcr.htn.corrupt import delete_action_everywhere
    from tcr.metrics.conformance import gap_over_repairs
    from tcr.negatives.generate import generate_negatives, gold_positive_traces
    from tcr.repair.candidates import target_valid_repairs
    from tcr.repair.selector import cost_only_indifference, select_conformance

    methods = (
        Method("m_s1", "S", ("Main",)),
        Method("m_s2", "S", ("Alt",)),
        Method("m_main", "Main", ("a", "G", "b")),
        Method("m_alt", "Alt", ("b", "G", "a")),
        Method("m_g", "G", ("crit",)),
    )
    gold = Domain(frozenset({"a", "b", "crit"}),
                  frozenset({"S", "Main", "Alt", "G"}), methods, "S")
    target = ("a", "crit", "b")
    print("GOLD language:", sorted(language_sample(gold, 5, limit=50)))
    flawed = delete_action_everywhere(gold, "crit")
    print("After deleting 'crit', flawed accepts target?", accepts(flawed, target))
    inst = RepairInstance("demo", flawed, gold, target, "crit", {"family": "leak"})
    repairs = target_valid_repairs(inst)
    print(f"\n{len(repairs)} target-valid repairs (all make the target derivable):")
    for r in repairs:
        d = r.apply(flawed)
        print(f"  insert {r.insertions} -> language {sorted(language_sample(d,5,limit=50))}")
    negs = generate_negatives(gold, target, "gold_structural", seed=0, n=64)
    labeled = gold_positive_traces(gold, target) + negs
    report = gap_over_repairs(flawed, repairs, labeled)
    indiff = cost_only_indifference(flawed, repairs, labeled)
    sel = select_conformance(flawed, repairs, labeled)
    print(f"\nLayer 1 (trace precision):")
    print(f"  Conformance gap: {report.conformance_gap:.3f} "
          f"({report.n_target_valid - report.n_conformant} of "
          f"{report.n_target_valid} repairs over-accept)")
    print(f"  cost-only expected precision: {indiff['expected_rejection']:.3f}")
    print(f"  conformance-aware precision : {sel.score.rejection:.3f}")

    # Layer 2: Allen-style timeline
    from tcr.temporal.timeline import check_timeline, extract_timeline

    spec = extract_timeline(gold, target)
    print(f"\nLayer 2 (Allen-style timeline):")
    print("  intended relations: " + ", ".join(
        f"{a}/{b}={sorted(r.value for r in rels)}"
        for (a, b), rels in spec.constraints.items()
    ))
    for r in repairs:
        d = r.apply(flawed)
        tl = check_timeline(d, target, spec)
        flags = "OK" if tl.conformant else "VIOLATION " + str(
            [v.observed if isinstance(v.observed, str) else v.observed.value
             for v in tl.violations]
        )
        print(f"  insert {r.insertions} -> timeline {flags}")
    print("\nBoth layers agree: only the insertion into the shared compound G "
          "is conformant.")


def main(argv=None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "all"
    if cmd in ("all", "headline"):
        print("== E1: conformance gap + stability ==")
        run_headline.main()
    if cmd in ("all", "selectors"):
        print("\n== E2: selector comparison ==")
        run_selector_comparison.main()
    if cmd in ("all", "robustness"):
        print("\n== E3: seed robustness ==")
        run_seed_robustness.main()
    if cmd in ("all", "timeline"):
        print("\n== E4: timeline conformance (Allen-style second axis) ==")
        run_timeline.main()
    if cmd == "demo":
        demo()
    if cmd not in ("all", "headline", "selectors", "robustness", "timeline", "demo"):
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
