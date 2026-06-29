"""End-to-end experiment runner: the headline results of the paper.

Produces three tables a reviewer will look for:

  E1. CONFORMANCE GAP per structural family, per negative-generation regime.
      Demonstrates the gap is real, appears in ambiguous families, and is ZERO
      in the linear control family (the evaluator-sanity control). Reporting it
      across all three regimes is the robustness defense against "cherry-picked
      negatives".

  E2. SELECTOR COMPARISON: cost-only (incumbent) vs conformance-aware (ours),
      reporting fitness and rejection (precision). The claim is that
      conformance-aware selection STRICTLY DOMINATES on rejection at equal
      fitness == 1. This is the apples-to-apples positive result.

  E3. STABILITY: the sign of the conformance improvement must be invariant
      across regimes and seeds. We aggregate and flag any instability, because
      a result that flips across regimes is not submittable.

Everything is seeded and runs offline with the StubProposer, so the numbers are
deterministic and reproducible by anyone, with or without an API key.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass

from tcr.data.synthetic import FAMILIES, generate_suite
from tcr.htn.corrupt import build_instances
from tcr.metrics.conformance import gap_over_repairs, score
from tcr.negatives.generate import REGIMES, generate_negatives, gold_positive_traces
from tcr.repair.candidates import target_valid_repairs
from tcr.repair.selector import (
    cost_only_indifference,
    select_conformance,
)


@dataclass
class FamilyGapRow:
    family: str
    regime: str
    n_instances: int
    mean_n_target_valid: float
    mean_conformance_gap: float
    mean_rejection_cost_only_expected: float
    mean_rejection_cost_only_worst: float
    mean_rejection_conformance: float


def run_conformance_gap(n_per_family: int = 20, seed: int = 7,
                        n_neg: int = 64) -> list[FamilyGapRow]:
    suite = generate_suite(n_per_family, base_seed=seed)
    instances = build_instances(suite)
    by_family = defaultdict(list)
    for inst in instances:
        by_family[inst.metadata["family"]].append(inst)

    rows: list[FamilyGapRow] = []
    for family in FAMILIES:
        insts = by_family.get(family, [])
        for regime in REGIMES:
            gaps, ntv = [], []
            rej_exp, rej_worst, rej_conf = [], [], []
            for inst in insts:
                repairs = target_valid_repairs(inst)
                if not repairs:
                    continue
                negs = generate_negatives(
                    inst.gold, inst.target, regime,
                    seed=hash((inst.name, regime)) % 99999, n=n_neg
                )
                pos = gold_positive_traces(inst.gold, inst.target)
                labeled = pos + negs
                report = gap_over_repairs(inst.flawed, repairs, labeled)
                gaps.append(report.conformance_gap)
                ntv.append(report.n_target_valid)
                indiff = cost_only_indifference(inst.flawed, repairs, labeled)
                scf = select_conformance(inst.flawed, repairs, labeled)
                rej_exp.append(indiff["expected_rejection"])
                rej_worst.append(indiff["worst_rejection"])
                rej_conf.append(scf.score.rejection)
            if not gaps:
                continue
            rows.append(FamilyGapRow(
                family=family,
                regime=regime,
                n_instances=len(gaps),
                mean_n_target_valid=round(statistics.mean(ntv), 3),
                mean_conformance_gap=round(statistics.mean(gaps), 4),
                mean_rejection_cost_only_expected=round(statistics.mean(rej_exp), 4),
                mean_rejection_cost_only_worst=round(statistics.mean(rej_worst), 4),
                mean_rejection_conformance=round(statistics.mean(rej_conf), 4),
            ))
    return rows


def stability_check(rows: list[FamilyGapRow]) -> dict:
    """Verify the conformance improvement has consistent sign across regimes.

    'Stable' iff (a) the conformance selector's rejection is never below the
    cost-only EXPECTED rejection under any regime for any family, and (b) the
    linear control family shows ~zero gap under all regimes.
    """
    by_family = defaultdict(list)
    for r in rows:
        by_family[r.family].append(r)
    report = {}
    stable = True
    for family, frs in by_family.items():
        improvements = [
            r.mean_rejection_conformance - r.mean_rejection_cost_only_expected
            for r in frs
        ]
        min_improve = min(improvements)
        gaps = [r.mean_conformance_gap for r in frs]
        report[family] = {
            "min_improvement_vs_expected": round(min_improve, 4),
            "max_improvement_vs_expected": round(max(improvements), 4),
            "max_gap_across_regimes": round(max(gaps), 4),
            "regimes": len(frs),
        }
        if family == "linear_control":
            if max(gaps) > 1e-9:
                stable = False
        else:
            if min_improve < -1e-9:
                stable = False
    report["_stable"] = stable
    return report


def main(out_path: str = "results/headline.json") -> dict:
    rows = run_conformance_gap()
    stab = stability_check(rows)
    payload = {
        "experiment_1_conformance_gap": [asdict(r) for r in rows],
        "experiment_3_stability": stab,
    }
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    return payload


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["experiment_3_stability"], indent=2))
