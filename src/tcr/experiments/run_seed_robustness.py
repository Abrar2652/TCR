"""E3: seed robustness -> confirms the headline result is not a seed artifact.

We re-run the conformance-gap measurement across many base seeds and report the
distribution of (a) the conformance gap on ambiguous families and (b) the
precision gain of our selector over the cost-only expected baseline, under the
gold_structural regime (the regime that surfaces the gap). A submittable result
must be sign-stable: the gain must be >= 0 for every seed, and the control
family must show a zero gap for every seed.
"""
from __future__ import annotations

import json
import os
import statistics

from tcr.data.synthetic import generate_suite
from tcr.htn.corrupt import build_instances
from tcr.metrics.conformance import gap_over_repairs
from tcr.negatives.generate import generate_negatives, gold_positive_traces
from tcr.repair.candidates import target_valid_repairs
from tcr.repair.selector import cost_only_indifference, select_conformance


def run(seeds=range(20), n_per_family: int = 10, regime: str = "gold_structural") -> dict:
    per_seed = []
    control_max_gap = 0.0
    min_gain = float("inf")
    for s in seeds:
        suite = generate_suite(n_per_family, base_seed=1000 + s)
        gaps_ambig, gains = [], []
        control_gaps = []
        for inst in build_instances(suite):
            repairs = target_valid_repairs(inst)
            if not repairs:
                continue
            negs = generate_negatives(inst.gold, inst.target, regime,
                                      seed=hash((inst.name, s)) % 99999, n=64)
            labeled = gold_positive_traces(inst.gold, inst.target) + negs
            report = gap_over_repairs(inst.flawed, repairs, labeled)
            indiff = cost_only_indifference(inst.flawed, repairs, labeled)
            sel = select_conformance(inst.flawed, repairs, labeled)
            gain = sel.score.rejection - indiff["expected_rejection"]
            if inst.metadata["family"] == "linear_control":
                control_gaps.append(report.conformance_gap)
            else:
                gaps_ambig.append(report.conformance_gap)
                gains.append(gain)
        if gains:
            per_seed.append({
                "seed": 1000 + s,
                "mean_gap_ambiguous": round(statistics.mean(gaps_ambig), 4),
                "mean_gain": round(statistics.mean(gains), 4),
                "min_gain": round(min(gains), 4),
                "control_max_gap": round(max(control_gaps) if control_gaps else 0.0, 4),
            })
            min_gain = min(min_gain, min(gains))
            control_max_gap = max(control_max_gap, max(control_gaps) if control_gaps else 0.0)
    summary = {
        "n_seeds": len(per_seed),
        "global_min_gain": round(min_gain, 4) if per_seed else None,
        "control_max_gap_over_all_seeds": round(control_max_gap, 4),
        "sign_stable": bool(per_seed) and min_gain >= -1e-9 and control_max_gap <= 1e-9,
    }
    return {"per_seed": per_seed, "summary": summary}


def main(out_path: str = "results/seed_robustness.json") -> dict:
    payload = run()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload["summary"], indent=2))
    return payload


if __name__ == "__main__":
    main()
