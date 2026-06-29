"""Scalable PO-HTN membership via Answer Set Programming (clingo).

PO-HTN plan verification is NP-complete; clingo's grounder+solver handles the
combinatorial decomposition+linearization search far more robustly than an ad-hoc
SMT encoding. A trace ``t`` is accepted iff there is a decomposition tree of the
initial task whose leaves, read in ``t``'s order, are exactly ``t`` and whose
method ordering constraints are respected.

Encoding (clean monotone-recursion ASP):
  * a pool of decomposition nodes; node 0 is the root (the initial task);
  * each active compound node selects a method and gets one child node per
    subtask (child id > parent id => acyclic; single claim => a tree);
  * each active primitive node is a leaf placed at one trace position with the
    matching action; every position is covered exactly once;
  * ``covers(N,P)`` propagates leaf positions up the tree (monotone recursion);
  * a method ordering ``I before J`` becomes: every position under child I is
    strictly before every position under child J (block ordering -- exactly the
    PO-HTN semantics, since ordered subtasks' yields cannot interleave);
  * the root must cover every position (connectedness).

Held to the brute-force PO oracle on small grammars (see tests). clingo is an
optional dependency (imported locally).
"""
from __future__ import annotations

from functools import lru_cache

from tcr.core.po_types import PODomain
from tcr.cfg.po_membership import _nullable


@lru_cache(maxsize=256)
def _facts(domain: PODomain) -> str:
    prims = sorted(domain.primitives)
    comps = sorted(domain.compounds)
    tid = {t: i for i, t in enumerate(prims + comps)}
    P = len(prims)
    lines = []
    for t in prims:
        lines.append(f"prim({tid[t]}).")
    for c in comps:
        lines.append(f"comp({tid[c]}).")
    lines.append(f"init({tid[domain.initial]}).")
    for mi, m in enumerate(domain.methods):
        lines.append(f"method({mi},{tid[m.head]}).")
        lines.append(f"mlen({mi},{len(m.subtasks)}).")
        for i, sub in enumerate(m.subtasks):
            lines.append(f"bodyat({mi},{i},{tid[sub]}).")
        for (i, j) in m.order:
            lines.append(f"ord({mi},{i},{j}).")
    return "\n".join(lines), tid, P


_RULES = """
node(0..k-1).
{ active(N) } :- node(N).
active(0).
1 { label(N,T) : prim(T) ; label(N,T) : comp(T) } 1 :- active(N).
:- not label(0,IT), init(IT).

% primitive leaves at trace positions
leaf(N) :- active(N), label(N,T), prim(T).
1 { atpos(N,P) : pos(P) } 1 :- leaf(N).
:- atpos(N,P), label(N,T), traceat(P,A), T != A.
:- pos(P), #count{ N : atpos(N,P) } != 1.

% compounds choose a method and one child node per subtask position
comp_node(N) :- active(N), label(N,C), comp(C).
1 { usem(N,M) : method(M,C) } 1 :- comp_node(N), label(N,C).
:- comp_node(N), label(N,C), usem(N,M), method(M,C2), C != C2.
1 { childof(N,I,X) : node(X), X > N } 1 :- comp_node(N), usem(N,M), bodyat(M,I,_).
:- childof(N,I,X), usem(N,M), bodyat(M,I,T), not label(X,T).
:- childof(N,I,X), not active(X).
% a node is claimed by at most one (parent,position) and, if active & non-root, exactly once
:- childof(N1,I1,X), childof(N2,I2,X), (N1,I1) < (N2,I2).
claimed(X) :- childof(_,_,X).
:- active(X), X > 0, not claimed(X).

% covers: positions in a node's subtree (monotone recursion)
covers(N,P) :- atpos(N,P).
covers(N,P) :- childof(N,_,X), covers(X,P).

% method ordering => block ordering of covered positions
:- childof(N,I,XI), childof(N,J,XJ), usem(N,M), ord(M,I,J),
   covers(XI,A), covers(XJ,B), A >= B.

% root covers every position (the leaves form one tree rooted at 0)
:- pos(P), not covers(0,P).
"""


def _solve(domain: PODomain, trace, K: int, timeout_s: float):
    import clingo

    facts, tid, P = _facts(domain)
    n = len(trace)
    prog = [facts, _RULES.replace("k-1", str(K - 1)), f"pos(0..{n - 1})."]
    for p, a in enumerate(trace):
        prog.append(f"traceat({p},{tid[a]}).")

    ctl = clingo.Control(["--warn=none"])
    ctl.add("base", [], "\n".join(prog))
    ctl.ground([("base", [])])
    with ctl.solve(async_=True) as handle:
        done = handle.wait(timeout_s)
        if not done:
            handle.cancel()
            return None  # timed out -> undecided
        res = handle.get()
    if res.satisfiable:
        return True
    if res.unsatisfiable:
        return False
    return None  # unknown


def accepts_po_asp(domain: PODomain, trace, timeout_s: float = 20.0,
                   max_nodes: int = 400):
    """PO membership via clingo. Returns True / False / None (undecided)."""
    trace = tuple(trace)
    for a in trace:
        if a not in domain.primitives:
            return False
    n = len(trace)
    if n == 0:
        return domain.initial in _nullable(domain)
    n_comp = len(domain.compounds)
    # generous node bound: n leaves + internal compound instances; deepen on UNSAT
    safe = min(max_nodes, 2 * n + 2 * n_comp + 6)
    K = min(safe, max(n + n_comp + 4, 12))
    while True:
        res = _solve(domain, trace, K, timeout_s)
        if res is True:
            return True
        if res is None:
            return None
        if K >= safe:
            return False
        K = min(safe, K + max(4, n))
