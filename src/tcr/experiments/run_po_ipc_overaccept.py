"""PO over-acceptance on GENUINE IPC-2020 partial-order domains (lifted HDDL).

Earlier PO over-acceptance used real method *widths* but constructed (relax-TO)
orders. Here we use the **actual partial orders** of the IPC-2020 partial-order
track. The reordering over-acceptance is local to a method, and a method's partial
order is already present in the lifted HDDL, so no grounding and no scalable
full-domain verifier are needed: we count linear extensions (subset DP, exact).

Model: the corruption removes a primitive subtask; the minimal repair reinserts it
without its ordering constraints. For each primitive subtask p in a method with
order O:

    local precision(p) = |linext(O)| / |linext(O minus all edges touching p)|

precision < 1 means reinserting p unordered admits orderings the gold method
forbids -- real reordering over-acceptance. Methods that are totally ordered or
where p is already unconstrained contribute precision 1.0 (the control).
"""
from __future__ import annotations

import glob
import re
import statistics
from collections import defaultdict
from functools import lru_cache


# -- HDDL parsing -------------------------------------------------------------
def _blocks(text: str, key: str):
    """Yield balanced-paren blocks starting with ``(key``."""
    i = 0
    while True:
        j = text.find("(" + key, i)
        if j < 0:
            return
        depth = 0
        k = j
        while k < len(text):
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        yield text[j:k + 1]
        i = k + 1


def _subblock(mtext: str, key: str):
    j = mtext.find(key)
    if j < 0:
        return None
    j = mtext.find("(", j)
    if j < 0:
        return None
    depth = 0
    k = j
    while k < len(mtext):
        if mtext[k] == "(":
            depth += 1
        elif mtext[k] == ")":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return mtext[j:k + 1]


def iter_domain_methods(po_root: str):
    """Yield (domain, subs, is_prim, order) over the WHOLE partial-order corpus.

    Handles both layouts: a single `<domain>/domain.hddl` (Barman, Rover,
    Satellite, Transport, UM-Translog, Woodworking) AND per-instance
    `<domain>/*-domain.hddl` files (Monroe-*, PCP). Methods are deduped by
    (subs, is_prim, order) signature within each domain so the recurring lifted
    methods across Monroe/PCP instance files are counted once.
    """
    for dom_dir in sorted(glob.glob(f"{po_root}/*/")):
        dom = dom_dir.rstrip("/").split("/")[-1]
        files = sorted(glob.glob(f"{dom_dir}*domain.hddl"))
        seen = set()
        for f in files:
            for subs, is_prim, order in parse_domain(f):
                key = (subs, is_prim, order)
                if key in seen:
                    continue
                seen.add(key)
                yield dom, subs, is_prim, order


def parse_domain(path: str):
    text = open(path).read()
    actions = set(re.findall(r"\(:action\s+([A-Za-z0-9_-]+)", text))
    methods = []
    for m in _blocks(text, ":method"):
        ordered = ":ordered-subtasks" in m
        sb = _subblock(m, ":ordered-subtasks") or _subblock(m, ":subtasks")
        if sb is None:
            continue
        # subtasks: labeled form (taskN (taskname ...))  OR unlabeled (taskname ...)
        subs = []  # list of (label, taskname)
        for st in re.finditer(r"\((task\d+)\s+\(([\w-]+)", sb):
            subs.append((st.group(1), st.group(2)))
        if not subs:
            # ordered/unlabeled form: (taskname args ...); skip the (and wrapper
            for st in re.finditer(r"\(([\w-]+)", sb):
                if st.group(1) != "and":
                    subs.append((f"task{len(subs)}", st.group(1)))
        if len(subs) < 2:
            continue
        label_idx = {lab: i for i, (lab, _) in enumerate(subs)}
        if ordered:
            order = {(i, i + 1) for i in range(len(subs) - 1)}
        else:
            ob = _subblock(m, ":ordering")
            order = set()
            for a, b in re.findall(r"\(<\s*([\w-]+)\s+([\w-]+)\)", ob or ""):
                if a in label_idx and b in label_idx:
                    order.add((label_idx[a], label_idx[b]))
        is_prim = [tn in actions for (_, tn) in subs]
        methods.append((tuple(t for _, t in subs), tuple(is_prim), frozenset(order)))
    return methods


# -- exact linear-extension counting -----------------------------------------
def linext_count(k: int, before: frozenset) -> int:
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


# -- experiment ---------------------------------------------------------------
def run(po_root: str):
    report = {"per_domain": {}, "overall": {}}
    all_prec = []
    all_affected = 0
    all_count = 0
    bydom = defaultdict(lambda: {"precs": [], "affected": 0, "widths": []})
    for dom, subs, is_prim, order in iter_domain_methods(po_root):
        k = len(subs)
        if k > 18:
            continue  # subset DP guard
        gold = linext_count(k, order)
        for p in range(k):
            if not is_prim[p]:
                continue
            rep_order = frozenset((i, j) for (i, j) in order if i != p and j != p)
            rep = linext_count(k, rep_order)
            if rep == 0:
                continue
            prec = gold / rep
            bydom[dom]["precs"].append(prec)
            bydom[dom]["widths"].append(k)
            if prec < 0.9999:
                bydom[dom]["affected"] += 1
    for dom in sorted(bydom):
        precs = bydom[dom]["precs"]
        affected = bydom[dom]["affected"]
        widths = bydom[dom]["widths"]
        if precs:
            report["per_domain"][dom] = {
                "n_primitive_subtasks": len(precs),
                "mean_local_precision": round(statistics.mean(precs), 4),
                "frac_affected": round(affected / len(precs), 4),
                "mean_method_width": round(statistics.mean(widths), 2),
            }
            all_prec.extend(precs)
            all_affected += affected
            all_count += len(precs)
    if all_count:
        report["overall"] = {
            "n_primitive_subtasks": all_count,
            "mean_local_precision": round(statistics.mean(all_prec), 4),
            "frac_affected": round(all_affected / all_count, 4),
        }
    return report


if __name__ == "__main__":
    import json

    rep = run("data/ipc2020-domains/partial-order")
    json.dump(rep, open("results/po_ipc_overaccept.json", "w"), indent=2)
    print(json.dumps(rep, indent=2))
