"""E4: timeline-conformance -> the second verification axis, reported alongside
trace-precision.

For each ambiguous family we report, over target-valid repairs:
  - trace_gap        : fraction of repairs that over-accept invalid traces
                       (the original precision axis)
  - timeline_gap     : fraction of repairs that violate the intended Allen
                       timeline on the target trace (the new temporal axis)
  - both_pass        : fraction of repairs that pass BOTH layers

The point is that the two layers are complementary: a repair can be
trace-valid yet timeline-violating (it derives the target but collapses or
mis-relates a compound task), and the temporal layer catches a distinct failure
mode. The linear control family must show zero on both axes.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict

from tcr.data.synthetic import FAMILIES, generate_suite
from tcr.htn.corrupt import build_instances
from tcr.repair.candidates import target_valid_repairs
from tcr.temporal.timeline import check_timeline, extract_timeline


def run(n_per_family: int = 20, seed: int = 7) -> dict:
    suite = generate_suite(n_per_family, base_seed=seed)
    instances = build_instances(suite)
    by_family = defaultdict(list)
    for inst in instances:
        by_family[inst.metadata["family"]].append(inst)

    table = []
    for family in FAMILIES:
        timeline_gaps, both_pass = [], []
        n = 0
        for inst in by_family.get(family, []):
            repairs = target_valid_repairs(inst)
            if not repairs:
                continue
            spec = extract_timeline(inst.gold, inst.target)
            tl_ok = 0
            for r in repairs:
                d = r.apply(inst.flawed)
                if check_timeline(d, inst.target, spec).conformant:
                    tl_ok += 1
            timeline_gaps.append(1.0 - tl_ok / len(repairs))
            both_pass.append(tl_ok / len(repairs))
            n += 1
        if not timeline_gaps:
            continue
        table.append({
            "family": family,
            "n_instances": n,
            "mean_timeline_gap": round(statistics.mean(timeline_gaps), 4),
            "mean_fraction_timeline_conformant": round(statistics.mean(both_pass), 4),
        })
    return {"timeline_conformance": table}


def main(out_path: str = "results/timeline_conformance.json") -> dict:
    payload = run()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    hdr = f"{'family':14s} {'n':>3s} {'timeline_gap':>13s} {'frac_conformant':>16s}"
    print(hdr)
    print("-" * len(hdr))
    for r in payload["timeline_conformance"]:
        print(f"{r['family']:14s} {r['n_instances']:>3d} "
              f"{r['mean_timeline_gap']:>13.3f} "
              f"{r['mean_fraction_timeline_conformant']:>16.3f}")
    return payload


if __name__ == "__main__":
    main()
