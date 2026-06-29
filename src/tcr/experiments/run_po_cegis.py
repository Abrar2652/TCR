"""Constructive method: counter-example-guided conformance-aware PO repair.

The minimal repair reinserts a removed action UNORDERED, over-accepting invalid
orderings (run_po_ipc_overaccept: precision ~0.46 on real IPC PO domains). We give
a repair that recovers the missing ordering constraints from counter-example
plans (a gold-oracle black-list, in the spirit of Lin & Bercher 2023 / Lin et al.
2025 — but the first *implemented* positive+negative HTN repair):

    start from the unordered repair; while it admits a gold-rejected linearization
    (a counter-example), find a precedence (a<b) that the counter-example violates
    but gold requires, and add it; repeat until no counter-example remains.

Why this is the punchline: on TO-HTN, counter-example-guided repair did NOT help
(the invalid language is combinatorial; one counter-example does not pin a fix).
On PO-HTN it provably does: each counter-example reveals a *specific* missing
precedence constraint, so CEGIS recovers gold ordering (precision 1.0) in at most
#missing-edges queries -- efficient and exact. Measured per method (no full-domain
verifier needed) on the GENUINE IPC-2020 partial-order domains.
"""
from __future__ import annotations

import glob
import itertools
import statistics
from collections import defaultdict

from tcr.experiments.run_po_ipc_overaccept import (
    iter_domain_methods,
    linext_count,
)


def _linexts(k, before):
    succ = [0] * k
    for (i, j) in before:
        succ[i] |= (1 << j)
    out = []
    for perm in itertools.permutations(range(k)):
        pos = {n: p for p, n in enumerate(perm)}
        if all(pos[a] < pos[b] for (a, b) in before):
            out.append(perm)
    return out


def _violated_gold_edge(perm, gold_order):
    """A gold edge (a<b) that perm violates (b before a)."""
    pos = {n: p for p, n in enumerate(perm)}
    for (a, b) in gold_order:
        if pos[a] > pos[b]:
            return (a, b)
    return None


def cegis_recover(k, gold_order, p):
    """Recover ordering for the reinserted primitive p via counter-examples.
    Returns (#counter_examples, #missing_edges, final_precision)."""
    gold = set(gold_order)
    missing = {(a, b) for (a, b) in gold if a == p or b == p}
    current = gold - missing  # unordered repair: p's edges dropped
    n_ce = 0
    while True:
        # counter-example: a linearization current allows but gold rejects
        ce = None
        for perm in _linexts(k, current):
            if _violated_gold_edge(perm, gold) is not None:
                ce = perm
                break
        if ce is None:
            break
        edge = _violated_gold_edge(ce, gold)
        current.add(edge)
        n_ce += 1
    final_prec = linext_count(k, gold) / linext_count(k, current)
    return n_ce, len(missing), final_prec


def run(po_root, max_width=9):
    base, cegis, ces, missing = [], [], [], []
    by_dom = defaultdict(lambda: {"base": [], "cegis": [], "ce": []})
    for dom, subs, is_prim, order in iter_domain_methods(po_root):
        k = len(subs)
        if k > max_width:
            continue
        gold_ext = linext_count(k, order)
        for p in range(k):
            if not is_prim[p]:
                continue
            edges_p = {(a, b) for (a, b) in order if a == p or b == p}
            if not edges_p:
                continue  # p already unordered -> no over-acceptance, skip
            rep_order = set(order) - edges_p
            base_prec = gold_ext / linext_count(k, rep_order)
            n_ce, n_miss, final_prec = cegis_recover(k, order, p)
            base.append(base_prec)
            cegis.append(final_prec)
            ces.append(n_ce)
            missing.append(n_miss)
            by_dom[dom]["base"].append(base_prec)
            by_dom[dom]["cegis"].append(final_prec)
            by_dom[dom]["ce"].append(n_ce)
    rep = {"per_domain": {}, "overall": {}}
    for d, v in by_dom.items():
        if v["base"]:
            rep["per_domain"][d] = {
                "n": len(v["base"]),
                "baseline_precision": round(statistics.mean(v["base"]), 4),
                "cegis_precision": round(statistics.mean(v["cegis"]), 4),
                "mean_counterexamples": round(statistics.mean(v["ce"]), 2),
            }
    if base:
        rep["overall"] = {
            "n": len(base),
            "baseline_precision": round(statistics.mean(base), 4),
            "cegis_precision": round(statistics.mean(cegis), 4),
            "mean_counterexamples_to_recover": round(statistics.mean(ces), 2),
            "mean_missing_edges": round(statistics.mean(missing), 2),
            "frac_reaching_precision_1": round(sum(c >= 0.9999 for c in cegis) / len(cegis), 4),
        }
    return rep


if __name__ == "__main__":
    import json

    rep = run("data/ipc2020-domains/partial-order")
    json.dump(rep, open("results/po_cegis.json", "w"), indent=2)
    print(json.dumps(rep, indent=2))
