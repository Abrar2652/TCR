"""Membership for partially-ordered HTN domains.

A trace ``t`` (sequence of primitives) is accepted by a PODomain iff ``t`` is a
linear extension of some fully-decomposed primitive task network -- equivalently,
``t`` is a valid solution of the PO-HTN problem (ignoring state, which is
CFG-irrelevant for this repair setting; Lutalo & Bercher 2026). This is
NP-complete in general (Behnke, Höller & Biundo 2015), unlike the TO case which is
in P. We provide:

  * ``accepts_po``        : a backtracking recognizer that consumes the trace
                           left-to-right, decomposing ready compounds and
                           consuming ready primitives (a primitive/compound is
                           READY when all its predecessors in the current network
                           are already consumed). Sound and complete within a step
                           budget; for the small *pruned* PO domains used in the
                           study the budget never binds.
  * ``derivable_po_bruteforce`` : an independent oracle that expands all
                           decompositions up to the trace length and enumerates
                           linear extensions. Used ONLY to differentially test
                           ``accepts_po`` on small grammars -- the same trust-anchor
                           discipline as the TO Earley verifier.

Decomposition semantics (standard): replacing a compound ``c`` by a method's
subtask network inherits ``c``'s order -- everything before ``c`` precedes all of
the method's subtasks, everything after ``c`` follows all of them.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import permutations

from tcr.core.po_types import PODomain, Task


class _BudgetExceeded(Exception):
    pass


@lru_cache(maxsize=4096)
def _nullable(domain: PODomain) -> frozenset:
    """Compounds that can decompose to the empty task network."""
    nullable: set = set()
    changed = True
    while changed:
        changed = False
        for m in domain.methods:
            if m.head in nullable:
                continue
            if all(s in nullable for s in m.subtasks):  # empty subtasks -> True
                nullable.add(m.head)
                changed = True
    return frozenset(nullable)


def accepts_po(domain: PODomain, trace, budget: int = 2_000_000) -> bool:
    prims = domain.primitives
    comps = domain.compounds
    nullable = _nullable(domain)

    for s in trace:
        if s not in prims:
            return False

    counter = [0]
    steps = [0]

    def fresh() -> int:
        counter[0] += 1
        return counter[0]

    def ready(nid, nodes, edges) -> bool:
        return not any(b == nid and a in nodes for (a, b) in edges)

    def rec(nodes: dict, edges: frozenset, i: int) -> bool:
        steps[0] += 1
        if steps[0] > budget:
            raise _BudgetExceeded()
        if i == len(trace):
            # all remaining tasks must vanish: no primitives, every compound nullable
            for sym in nodes.values():
                if sym in prims or sym not in nullable:
                    return False
            return True
        target = trace[i]
        # Option 1: consume a ready primitive labelled target
        for nid, sym in list(nodes.items()):
            if sym == target and sym in prims and ready(nid, nodes, edges):
                nn = dict(nodes)
                del nn[nid]
                ne = frozenset((a, b) for (a, b) in edges if a != nid and b != nid)
                if rec(nn, ne, i + 1):
                    return True
        # Option 2: decompose a ready compound (does not advance i)
        for nid, sym in list(nodes.items()):
            if sym in comps and ready(nid, nodes, edges):
                preds = [a for (a, b) in edges if b == nid and a in nodes]
                succs = [b for (a, b) in edges if a == nid and b in nodes]
                base_edges = [(a, b) for (a, b) in edges if a != nid and b != nid]
                for m in domain.methods_for(sym):
                    nn = dict(nodes)
                    del nn[nid]
                    ids = [fresh() for _ in m.subtasks]
                    for k, st in enumerate(m.subtasks):
                        nn[ids[k]] = st
                    ne = set(base_edges)
                    for k in range(len(ids)):
                        for x in preds:
                            ne.add((x, ids[k]))
                        for y in succs:
                            ne.add((ids[k], y))
                    for (ia, ib) in m.order:
                        ne.add((ids[ia], ids[ib]))
                    if rec(nn, frozenset(ne), i):
                        return True
        return False

    root = fresh()
    import sys
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, 100000))
    try:
        return rec({root: domain.initial}, frozenset(), 0)
    except (_BudgetExceeded, RecursionError):
        # Conservative: a budget/recursion blow-up means we could not *prove*
        # acceptance within bounds. For the small pruned/synthetic PO domains the
        # study uses this never binds; large real domains need the SAT/INDU
        # encoding (see docs/PARTIAL_ORDER_PLAN.md) rather than this backtracker.
        return False
    finally:
        sys.setrecursionlimit(old_limit)


# --------------------------------------------------------------------------
# Brute-force oracle (small grammars only)
# --------------------------------------------------------------------------
def _linexts(nodes: dict, edges: frozenset) -> set:
    """All linear extensions (as label tuples) of a fully-primitive network."""
    ids = list(nodes)
    out: set = set()
    for perm in permutations(ids):
        pos = {nid: p for p, nid in enumerate(perm)}
        if all(pos[a] < pos[b] for (a, b) in edges if a in pos and b in pos):
            out.add(tuple(nodes[nid] for nid in perm))
    return out


def po_language(domain: PODomain, max_len: int, max_networks: int = 200000) -> set:
    """Enumerate the PO language up to ``max_len`` by expanding all decompositions
    (BFS) and collecting linear extensions of fully-primitive networks."""
    prims = domain.primitives
    comps = domain.compounds
    counter = [0]

    def fresh():
        counter[0] += 1
        return counter[0]

    root = fresh()
    start = ({root: domain.initial}, frozenset())
    frontier = [start]
    lang: set = set()
    seen_count = 0
    while frontier and seen_count < max_networks:
        nodes, edges = frontier.pop()
        seen_count += 1
        # prune: already too many primitives
        n_prim = sum(1 for s in nodes.values() if s in prims)
        if n_prim > max_len:
            continue
        comp_ids = [nid for nid, s in nodes.items() if s in comps]
        if not comp_ids:
            for ext in _linexts(nodes, edges):
                if len(ext) <= max_len:
                    lang.add(ext)
            continue
        nid = comp_ids[0]  # expand leftmost compound (all orders explored via methods)
        sym = nodes[nid]
        preds = [a for (a, b) in edges if b == nid and a in nodes]
        succs = [b for (a, b) in edges if a == nid and b in nodes]
        base_edges = [(a, b) for (a, b) in edges if a != nid and b != nid]
        for m in domain.methods_for(sym):
            nn = dict(nodes)
            del nn[nid]
            ids = [fresh() for _ in m.subtasks]
            for k, st in enumerate(m.subtasks):
                nn[ids[k]] = st
            ne = set(base_edges)
            for k in range(len(ids)):
                for x in preds:
                    ne.add((x, ids[k]))
                for y in succs:
                    ne.add((ids[k], y))
            for (ia, ib) in m.order:
                ne.add((ids[ia], ids[ib]))
            if sum(1 for s in nn.values() if s in prims) <= max_len * 2:
                frontier.append((nn, frozenset(ne)))
    return lang


def derivable_po_bruteforce(domain: PODomain, trace, max_len: int | None = None) -> bool:
    L = len(trace) if max_len is None else max_len
    return tuple(trace) in po_language(domain, L)


def po_random_plan(domain: PODomain, rng, max_len: int = 200, max_steps: int = 3000):
    """One random plan: random leftmost-style PO derivation to a primitive network,
    then a random linear extension. Returns None if it exceeds the length bound.

    Used to *sample* the PO language (e.g. for the escaping-edges precision metric);
    not a membership decision, so an occasional None only lowers the sample size.
    """
    prims = domain.primitives
    comps = domain.compounds
    counter = [0]

    def fresh():
        counter[0] += 1
        return counter[0]

    nodes = {fresh(): domain.initial}
    edges: set = set()
    steps = 0
    # expand all compounds (random method choice) into a primitive PO network
    while steps < max_steps:
        steps += 1
        comp_ids = [nid for nid, s in nodes.items() if s in comps]
        if not comp_ids:
            break
        nid = rng.choice(comp_ids)
        sym = nodes[nid]
        ms = domain.methods_for(sym)
        if not ms:
            return None
        m = rng.choice(ms)
        preds = [a for (a, b) in edges if b == nid and a in nodes]
        succs = [b for (a, b) in edges if a == nid and b in nodes]
        edges = {(a, b) for (a, b) in edges if a != nid and b != nid}
        del nodes[nid]
        ids = [fresh() for _ in m.subtasks]
        for k, st in enumerate(m.subtasks):
            nodes[ids[k]] = st
        for k in range(len(ids)):
            for x in preds:
                edges.add((x, ids[k]))
            for y in succs:
                edges.add((ids[k], y))
        for (ia, ib) in m.order:
            edges.add((ids[ia], ids[ib]))
        if sum(1 for s in nodes.values() if s in prims) > max_len:
            return None
    else:
        return None
    # random linear extension of the primitive network
    remaining = dict(nodes)
    out = []
    while remaining:
        avail = [nid for nid in remaining if not any(b == nid and a in remaining for (a, b) in edges)]
        if not avail:
            return None  # cycle (shouldn't happen)
        nid = rng.choice(avail)
        out.append(remaining[nid])
        del remaining[nid]
    return tuple(out)
