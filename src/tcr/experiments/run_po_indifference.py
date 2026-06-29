"""PO run-benchmark: the cost-only objective's indifference set on real IPC
partial-order domains, characterized EXACTLY (not assumed).

In HDDL an ordering constraint is separate from a subtask, so reinserting a
removed primitive costs one insertion regardless of which ordering constraints
accompany it. The minimum-cost repair is therefore genuinely INDIFFERENT among
every recall-preserving reinsertion -- i.e. every repair that adds some subset of
gold's precedence edges touching the action (all such repairs keep the target and
all other gold plans derivable, at identical insertion cost). We enumerate that
indifference set per method and report, exactly as the TO study does
(`cost_only_indifference`):

    expected precision  = mean over the indifference set   (the fair baseline)
    worst precision     = the unordered reinsertion        (the leaky corner)
    conformance         = 1.0                               (full gold order)
    gap                 = fraction of the set that over-accepts

This replaces "assume the repair inserts unordered" with a measured distribution
over real repairs, and yields a bootstrap CI over methods. Exact (subset-DP
linear-extension counting); no membership solver, no assumed behaviour.
"""
from __future__ import annotations

import glob
import json
import os
import random
import statistics
from collections import defaultdict

from tcr.experiments.run_po_ipc_overaccept import (
    iter_domain_methods,
    linext_count,
)


def _bootstrap_ci(values, stat=statistics.mean, n=2000, seed=0):
    if not values:
        return (None, None)
    rng = random.Random(seed)
    k = len(values)
    boots = []
    for _ in range(n):
        sample = [values[rng.randrange(k)] for _ in range(k)]
        boots.append(stat(sample))
    boots.sort()
    return (round(boots[int(0.025 * n)], 4), round(boots[int(0.975 * n)], 4))


def _indiff_unit(k, order, gold_lx, p):
    """Cost-only indifference set for reinserting subtask p: add any subset of p's
    gold precedence edges. Returns (expected, worst, best, gap) or None."""
    Ep = [(a, b) for (a, b) in order if a == p or b == p]
    if not Ep:
        return None
    base = frozenset(e for e in order if e not in Ep)
    precs = []
    for mask in range(1 << len(Ep)):
        S = [Ep[i] for i in range(len(Ep)) if (mask >> i) & 1]
        precs.append(gold_lx / linext_count(k, base | frozenset(S)))
    if max(precs) - min(precs) < 1e-9:
        return None
    return (statistics.mean(precs), min(precs), max(precs),
            sum(pp < 0.9999 for pp in precs) / len(precs), len(Ep))


def run(po_root, max_width=14):
    # two evaluation modes:
    #  units          = the benchmark protocol (remove a PRIMITIVE subtask)
    #  genuine_units  = remove ANY subtask of a method whose GOLD already has
    #                   reordering freedom (gold_lx>1) -- genuinely partial order
    units, genuine_units = [], []
    for dom, subs, is_prim, order in iter_domain_methods(po_root):
        k = len(subs)
        if k > max_width:
            continue
        gold_lx = linext_count(k, order)
        for p in range(k):
            u = _indiff_unit(k, order, gold_lx, p)
            if u is None:
                continue
            exp, wor, best, gap, ke = u
            rec = dict(domain=dom, k=ke, gold_partial=bool(gold_lx > 1),
                       expected=exp, worst=wor, best=best, gap=gap)
            if is_prim[p]:
                units.append(rec)
            if gold_lx > 1:
                genuine_units.append(rec)
    if not units:
        return {}
    exp = [u["expected"] for u in units]
    wor = [u["worst"] for u in units]
    rep = {
        "n_methods": len(units),
        "n_gold_partial": sum(u["gold_partial"] for u in units),
        "cost_only_expected": round(statistics.mean(exp), 4),
        "cost_only_expected_ci95": _bootstrap_ci(exp),
        "cost_only_worst": round(statistics.mean(wor), 4),
        "cost_only_worst_ci95": _bootstrap_ci(wor),
        "conformance": 1.0,
        "mean_gap_over_indifference_set": round(statistics.mean(u["gap"] for u in units), 4),
        "frac_methods_with_gap": round(sum(u["gap"] > 0 for u in units) / len(units), 4),
        "per_domain": {},
    }
    bydom = defaultdict(list)
    for u in units:
        bydom[u["domain"]].append(u)
    for d, us in sorted(bydom.items()):
        rep["per_domain"][d] = {
            "n": len(us),
            "cost_only_expected": round(statistics.mean(u["expected"] for u in us), 4),
            "cost_only_worst": round(statistics.mean(u["worst"] for u in us), 4),
            "mean_gap": round(statistics.mean(u["gap"] for u in us), 4),
        }
    # genuinely partial-order subset: remove ANY subtask of a method whose gold
    # already has reordering freedom (closes "your gap is only on chain methods")
    if genuine_units:
        gexp = [u["expected"] for u in genuine_units]
        gwor = [u["worst"] for u in genuine_units]
        rep["genuine_partial"] = {
            "n_units": len(genuine_units),
            "n_domains": len({u["domain"] for u in genuine_units}),
            "domains": sorted({u["domain"] for u in genuine_units}),
            "cost_only_expected": round(statistics.mean(gexp), 4),
            "cost_only_expected_ci95": _bootstrap_ci(gexp),
            "cost_only_worst": round(statistics.mean(gwor), 4),
            "cost_only_worst_ci95": _bootstrap_ci(gwor),
            "conformance": 1.0,
            "mean_gap_over_indifference_set": round(statistics.mean(u["gap"] for u in genuine_units), 4),
            "frac_units_with_gap": round(sum(u["gap"] > 0 for u in genuine_units) / len(genuine_units), 4),
        }
    return rep


if __name__ == "__main__":
    out = run("data/ipc2020-domains/partial-order")
    json.dump(out, open("results/po_indifference.json", "w"), indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "per_domain"}, indent=2))
    print("per_domain:", json.dumps(out["per_domain"], indent=2))
