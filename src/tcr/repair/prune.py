"""Target-relative domain pruning (TDG-style), ported from Lutalo & Bercher (2026).

This is a faithful Python port of ``pruneDomainForPlan`` in the authors' C++
``htn_repair`` tool (``pruner.cpp`` in their Zenodo artifact). It restricts a
(possibly enormous) grounded TO-HTN domain to the sub-domain that can possibly
participate in deriving a *specific* target plan, given the corruption only
removed actions. Pruning is (a) the incumbent pipeline's first stage and (b) the
only way the largest IPC instances (up to ~1.3M grounded methods) become
tractable for exact CYK membership.

Why we reproduce it exactly rather than approximate: the precision question is
"does a target-valid repair of the *pruned* flawed domain over-accept?". To make
that an apples-to-apples comparison with the incumbent, we must prune the way the
incumbent prunes. Any divergence would be a confound a reviewer could exploit.

Pruning conditions (from pruner.cpp), to a fixed point:
  * a method is kept iff every primitive in its (current, flawed) body is in the
    plan AND those primitives form a SUBSEQUENCE of the plan, every compound in
    its body is still active, and its minimal-yield length <= plan length;
  * a compound is kept iff it is reachable from the top task via kept methods and
    has minimal yield <= plan length.

Note the subsequence condition is over a method's *direct* primitive children
(not its full yield), exactly as in the original.
"""
from __future__ import annotations

from tcr.core.types import Domain, Method, Trace

INF = float("inf")


def _is_subsequence(sub: list[str], main: tuple[str, ...]) -> bool:
    i = 0
    for x in main:
        if i < len(sub) and x == sub[i]:
            i += 1
    return i == len(sub)


def prune_for_plan(domain: Domain, plan: Trace) -> Domain:
    """Return the target-relative pruned sub-domain (ids unchanged).

    Unlike the C++ version we do NOT re-index task ids, because the rest of the
    tcr stack keys repairs and negatives on stable string ids and we want gold
    and flawed to stay in the same coordinate system. The language over the
    primitive alphabet is identical to the re-indexed version.
    """
    plan_set = set(plan)
    plan_len = len(plan)
    prims = domain.primitives

    active: set[str] = set(domain.compounds)
    methods = list(domain.methods)

    def is_prim(t: str) -> bool:
        return t in prims

    changed_overall = True
    while changed_overall:
        changed_overall = False

        # head -> list of methods, built once per outer round
        by_head: dict[str, list[Method]] = {}
        for m in methods:
            by_head.setdefault(m.head, []).append(m)

        # --- Step 1: minimal yield length fixpoint ---
        min_len_abs: dict[str, float] = {a: INF for a in active}
        m_minlen: dict[str, float] = {m.mid: INF for m in methods}
        m_usable: dict[str, bool] = {m.mid: True for m in methods}

        changed_inner = True
        while changed_inner:
            changed_inner = False
            for m in methods:
                total = 0.0
                infinite = False
                for st in m.body:
                    if is_prim(st):
                        if st not in plan_set:
                            infinite = True
                            break
                        total += 1
                    else:
                        ml = min_len_abs.get(st, INF)
                        if ml == INF:
                            infinite = True
                            break
                        total += ml
                    if total > plan_len:
                        infinite = True
                        break
                cand = INF if infinite else total
                if m_minlen[m.mid] != cand:
                    m_minlen[m.mid] = cand
                    changed_inner = True
                newu = cand <= plan_len
                if m_usable[m.mid] != newu:
                    m_usable[m.mid] = newu
                    changed_inner = True
            for a in active:
                best = INF
                for m in by_head.get(a, ()):
                    if m_usable[m.mid] and m_minlen[m.mid] < best:
                        best = m_minlen[m.mid]
                if min_len_abs[a] != best:
                    min_len_abs[a] = best
                    changed_inner = True

        # --- Step 2: prune methods ---
        before = len(methods)
        new_methods: list[Method] = []
        for m in methods:
            if m.head not in active:
                continue
            if not m_usable[m.mid]:
                continue
            ok = True
            rhs_prims: list[str] = []
            for st in m.body:
                if is_prim(st):
                    if st not in plan_set:
                        ok = False
                        break
                    rhs_prims.append(st)
                else:
                    if st not in active:
                        ok = False
                        break
            if not ok:
                continue
            if not _is_subsequence(rhs_prims, plan):
                continue
            new_methods.append(m)
        if len(new_methods) < before:
            changed_overall = True
        methods = new_methods

        # --- Step 3: prune abstracts (viability + reachability from top) ---
        before_v = len(active)
        viable: set[str] = set()
        heads_with_rule = {m.head for m in methods}
        for a in active:
            if min_len_abs.get(a, INF) > plan_len:
                continue
            if a in heads_with_rule:
                viable.add(a)
        reachable: set[str] = set()
        if domain.initial in viable:
            stack = [domain.initial]
            reachable.add(domain.initial)
            while stack:
                cur = stack.pop()
                for m in by_head.get(cur, ()):
                    for st in m.body:
                        if (not is_prim(st)) and st in viable and st not in reachable:
                            reachable.add(st)
                            stack.append(st)
        if len(reachable) < before_v:
            changed_overall = True
        active = reachable
        methods = [m for m in methods if m.head in active]

    # --- Step 4: build pruned domain (ids preserved) ---
    kept_prims: set[str] = set(plan)
    for m in methods:
        for st in m.body:
            if is_prim(st):
                kept_prims.add(st)
    return Domain(
        primitives=frozenset(kept_prims),
        compounds=frozenset(active),
        methods=tuple(methods),
        initial=domain.initial,
    )
