"""E2: head-to-head selector comparison -> the paper's main results table.

For every corrupted instance we compute, under each negative-generation regime,
the precision (negative-rejection) achieved by:

    cost_only (expected)  -- incumbent objective, averaged over its min-cost
                             indifference set (the fair characterization)
    cost_only (worst)     -- adversarial tie-break of the incumbent
    conformance (ours)    -- precision-maximizing selection

Fitness is reported too and is 1.0 for every selector by construction (all
operate on target-valid repairs), which is the point: we improve precision at no
cost to recall. Results are written to results/selector_comparison.json and
printed as a table.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict

from tcr.data.synthetic import FAMILIES, generate_suite
from tcr.htn.corrupt import build_instances
from tcr.negatives.generate import REGIMES, generate_negatives, gold_positive_traces
from tcr.repair.candidates import target_valid_repairs
from tcr.repair.selector import cost_only_indifference, select_conformance


def run(n_per_family: int = 20, seed: int = 7, n_neg: int = 64) -> dict:
    suite = generate_suite(n_per_family, base_seed=seed)
    instances = build_instances(suite)
    by_family = defaultdict(list)
    for inst in instances:
        by_family[inst.metadata["family"]].append(inst)

    table = []
    for family in FAMILIES:
        for regime in REGIMES:
            co_exp, co_worst, conf, fit = [], [], [], []
            for inst in by_family.get(family, []):
                repairs = target_valid_repairs(inst)
                if not repairs:
                    continue
                negs = generate_negatives(
                    inst.gold, inst.target, regime,
                    seed=hash((inst.name, regime)) % 99999, n=n_neg,
                )
                labeled = gold_positive_traces(inst.gold, inst.target) + negs
                indiff = cost_only_indifference(inst.flawed, repairs, labeled)
                sel = select_conformance(inst.flawed, repairs, labeled)
                co_exp.append(indiff["expected_rejection"])
                co_worst.append(indiff["worst_rejection"])
                conf.append(sel.score.rejection)
                fit.append(sel.score.fitness)
            if not conf:
                continue
            table.append({
                "family": family,
                "regime": regime,
                "n": len(conf),
                "fitness_all": round(statistics.mean(fit), 4),
                "precision_cost_only_expected": round(statistics.mean(co_exp), 4),
                "precision_cost_only_worst": round(statistics.mean(co_worst), 4),
                "precision_conformance": round(statistics.mean(conf), 4),
                "precision_gain_vs_expected": round(
                    statistics.mean(conf) - statistics.mean(co_exp), 4
                ),
            })
    return {"selector_comparison": table}


def main(out_path: str = "results/selector_comparison.json") -> dict:
    payload = run()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    # pretty print
    rows = payload["selector_comparison"]
    hdr = f"{'family':14s} {'regime':18s} {'n':>3s} {'fit':>5s} {'co_exp':>6s} {'co_wst':>6s} {'ours':>5s} {'gain':>6s}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['family']:14s} {r['regime']:18s} {r['n']:>3d} "
              f"{r['fitness_all']:>5.2f} {r['precision_cost_only_expected']:>6.3f} "
              f"{r['precision_cost_only_worst']:>6.3f} {r['precision_conformance']:>5.3f} "
              f"{r['precision_gain_vs_expected']:>+6.3f}")
    return payload


if __name__ == "__main__":
    main()
