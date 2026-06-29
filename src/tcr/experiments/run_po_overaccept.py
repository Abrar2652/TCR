"""PO over-acceptance on real IPC method structure, measured exactly per method.

The reordering over-acceptance of a minimal repair is LOCAL: reinserting an action
into a partially-ordered method without its ordering constraints lets that one
method admit extra linear extensions. We count them exactly (subset DP) for the
gold method vs the unordered-repair method, sweeping how partially-ordered the gold
is, across the real IPC method-width distribution.

   local precision = |linext(gold method)| / |linext(unordered-repair method)|

This is the mechanism-level evidence and needs no full-domain PO verifier (which is
NP-complete; the backtracker `cfg.po_membership` is the small-scale reference and
`cfg.po_membership_smt` the validated-but-not-yet-scalable SMT encoding). A full
domain-level number additionally needs a scalable verifier or real PO-IPC domains.
"""
from __future__ import annotations

import csv
import json
import random
import statistics
from collections import defaultdict
from functools import lru_cache

from tcr.data.sas_adapter import load_instance, parse_fuzz_ops
from tcr.repair.prune import prune_for_plan

VERIFIED = "manual from_cfg verified"


def linext_count(k: int, before: set) -> int:
    """Number of linear extensions of a poset on {0..k-1}; before = {(i,j): i<j}."""
    succ = [0] * k
    for (i, j) in before:
        succ[i] |= (1 << j)

    @lru_cache(maxsize=None)
    def dp(S: int) -> int:
        if S == 0:
            return 1
        tot = 0
        for m in range(k):
            if (S >> m) & 1 and not (succ[m] & S):
                tot += dp(S ^ (1 << m))
        return tot

    return dp((1 << k) - 1)


def _relaxed_chain(k: int, drop: float, rng) -> set:
    return {(i, i + 1) for i in range(k - 1) if rng.random() > drop}


def run(root, csv_path, out_path, drops=(0.0, 0.3, 0.6, 0.9), max_inst=80, gold_cap=4000):
    rows = [r for r in csv.DictReader(open(csv_path)) if r["status"] == VERIFIED]
    rows = [r for r in rows if r["methods"] and int(r["methods"]) < gold_cap]
    rows.sort(key=lambda r: int(r["methods"]))
    rows = rows[:max_inst]

    report = {"drops": {}, "per_domain_at_0.6": {}, "n_instances": len(rows)}
    for drop in drops:
        local, widths, affected = [], [], 0
        by_dom = defaultdict(list)
        for r in rows:
            path = r["path"]
            dom = path.split("/")[0]
            try:
                inst = load_instance(f"{root}/{path}")
                pg = prune_for_plan(inst.gold, inst.target)
            except Exception:  # noqa: BLE001
                continue
            rmv = {f"t{t}" for (_, _, t) in parse_fuzz_ops(f"{root}/{path}/fuzz-ops")}
            for m in pg.methods:
                k = len(m.body)
                if k < 2:
                    continue
                rmidx = {i for i, s in enumerate(m.body) if s in rmv}
                if not rmidx:
                    continue
                base = _relaxed_chain(k, drop, random.Random(hash((path, m.mid)) % 99999))
                g = linext_count(k, base)
                rep = base - {(i, j) for (i, j) in base if i in rmidx or j in rmidx}
                rcount = linext_count(k, rep)
                if rcount == 0:
                    continue
                prec = g / rcount
                local.append(prec)
                widths.append(k)
                by_dom[dom].append(prec)
                if prec < 0.9999:
                    affected += 1
        if local:
            report["drops"][str(drop)] = {
                "n_repaired_methods": len(local),
                "mean_local_precision": round(statistics.mean(local), 4),
                "frac_affected": round(affected / len(local), 4),
                "mean_width": round(statistics.mean(widths), 2),
            }
            if abs(drop - 0.6) < 1e-9:
                report["per_domain_at_0.6"] = {
                    d: {"mean": round(statistics.mean(v), 4), "n": len(v)}
                    for d, v in sorted(by_dom.items())
                }
    json.dump(report, open(out_path, "w"), indent=2)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    base = "data/zenodo_lutalo"
    run(
        root=f"{base}/socs2024-evaluation/results",
        csv_path=f"{base}/zenodo/data/raw/results_openai.csv",
        out_path="results/po_overaccept.json",
    )
