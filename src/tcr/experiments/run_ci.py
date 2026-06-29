"""Statistical-rigor pass: bootstrap / Wilson confidence intervals on every
headline number, plus a sample-size sensitivity check for the (sampled)
escaping-edges precision, and the UNCONDITIONAL over-generalization figures
(not just the ambiguous subset). Reads the existing results; writes
results/ci_summary.json."""
from __future__ import annotations

import json
import math
import os
import random
import statistics

R = "results"


def boot_ci(vals, stat=statistics.mean, n=4000, seed=0):
    if not vals:
        return None
    rng = random.Random(seed)
    k = len(vals)
    b = sorted(stat([vals[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return [round(b[int(0.025 * n)], 4), round(b[int(0.975 * n)], 4)]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def overgen(model):
    recs = [json.loads(l) for l in open(f"{R}/ipc_overgen_{model}.jsonl")]
    ok = [x for x in recs if x.get("repair_precision") is not None]
    amb = [x["repair_precision"] for x in ok if x["ambiguous"]]
    allp = [x["repair_precision"] for x in ok]
    return {
        "n_scored": len(ok),
        "n_ambiguous": len(amb),
        "frac_ambiguous": round(len(amb) / len(ok), 4),
        "ambiguous_mean": round(statistics.mean(amb), 4),
        "ambiguous_mean_ci95": boot_ci(amb),
        "ambiguous_median": round(statistics.median(amb), 4),
        "unconditional_mean": round(statistics.mean(allp), 4),
        "unconditional_mean_ci95": boot_ci(allp),
        "unconditional_frac_below_0.5": round(sum(p < 0.5 for p in allp) / len(allp), 4),
    }


def audit(model):
    # use the same (negative-set) audit metric for BOTH models so rates compare
    f = f"{R}/ipc_audit_{model}.jsonl"
    ok = [x for x in (json.loads(l) for l in open(f)) if "over_accepts" in x]
    k = sum(x["over_accepts"] for x in ok)
    return {"metric": "negative-set", "n": len(ok), "over_accept": k,
            "rate": round(k / len(ok), 4), "rate_ci95_wilson": wilson(k, len(ok))}


def sensitivity():
    """Re-measure escaping precision at several sample sizes on a few instances
    to show the metric is stable (not an artifact of n)."""
    from tcr.data.sas_adapter import load_instance
    from tcr.repair.prune import prune_for_plan
    from tcr.data.masking import build_mask, decode_repaired_domain
    from tcr.experiments.run_ipc_overgeneralization import _precision_len
    ROOT = "data/zenodo_lutalo/socs2024-evaluation/results"
    MR = "data/zenodo_lutalo/zenodo/data/model_runs/openai-o4-mini-high"
    paths = ["Depots/p01/plan-1", "Satellite-GTOHP/p01/plan-2", "Rover-GTOHP/p01/plan-1"]
    out = {}
    for path in paths:
        inst = load_instance(f"{ROOT}/{path}")
        pf = prune_for_plan(inst.flawed, inst.target)
        mm = build_mask(pf)
        rep = decode_repaired_domain(pf, mm, open(f"{MR}/{path.replace('/', '_')}/llm_processed.txt").read())
        L = len(inst.target)
        row = {}
        for n in (100, 200, 400, 800):
            vals = [(_precision_len(rep, inst.gold, L, seed=s, n=n)[0] or 0.0) for s in range(5)]
            row[str(n)] = [round(statistics.mean(vals), 4), round(statistics.pstdev(vals), 4)]
        out[path] = row  # {n: [mean_over_5_seeds, sd]}
    return out


if __name__ == "__main__":
    res = {
        "overgen": {m: overgen(f"openai-{m}-high") for m in ["o4-mini", "gpt-oss-120b"]},
        "audit_over_accept": {m: audit(f"openai-{m}-high") for m in ["o4-mini", "gpt-oss-120b"]},
        "po_indifference": json.load(open(f"{R}/po_indifference.json")),
        "escaping_sample_size_sensitivity": sensitivity(),
    }
    json.dump(res, open(f"{R}/ci_summary.json", "w"), indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "po_indifference"}, indent=2))
