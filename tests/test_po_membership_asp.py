"""Regression tests for the ASP (clingo) PO verifier on its fast envelope.

Validated against the brute-force oracle. The ASP verifier is CORRECT at all sizes
but only fast for small/short instances -- scalable exact PO membership on large
real grammars is the open problem (it needs Schwartz & Wolter's specialised
encoding; see cfg/po_membership_asp.py). Skipped if clingo is not installed.
"""
from __future__ import annotations

import random

import pytest

clingo = pytest.importorskip("clingo")

from tcr.cfg.po_membership import derivable_po_bruteforce  # noqa: E402
from tcr.cfg.po_membership_asp import accepts_po_asp  # noqa: E402
from tcr.core.po_types import PODomain, POMethod  # noqa: E402


def _dom(ms, p, c, init="S"):
    return PODomain(frozenset(p), frozenset(c), tuple(ms), init)


def test_asp_hand_cases():
    cases = [
        (_dom([POMethod("m", "S", ("x", "y"), frozenset())], {"x", "y"}, {"S"}),
         [("x", "y"), ("y", "x"), ("x", "x"), ("x",)]),
        (_dom([POMethod("m", "S", ("x", "y", "z"), frozenset({(0, 2), (1, 2)}))],
              {"x", "y", "z"}, {"S"}),
         [("x", "y", "z"), ("z", "x", "y"), ("x", "z", "y")]),
        (_dom([POMethod.total("m", "S", ("x", "y", "z"))], {"x", "y", "z"}, {"S"}),
         [("x", "y", "z"), ("y", "x", "z")]),
        (_dom([POMethod("ms", "S", ("A", "B"), frozenset({(0, 1)})),
               POMethod("ma", "A", ("a1", "a2"), frozenset()),
               POMethod("mb", "B", ("b",))], {"a1", "a2", "b"}, {"S", "A", "B"}),
         [("a1", "a2", "b"), ("a1", "b", "a2")]),
        # length-overrun (the case that broke the removed SMT encoding)
        (_dom([POMethod("m", "S", ("p0", "p0"), frozenset())], {"p0"}, {"S"}),
         [("p0", "p0"), ("p0", "p0", "p0"), ("p0",)]),
        (_dom([POMethod("ms", "S", ("C0", "p0"), frozenset()),
               POMethod("ms2", "S", ("p0",), frozenset()),
               POMethod("mc", "C0", (), frozenset())], {"p0"}, {"S", "C0"}),
         [("p0",), ("p0", "p0")]),
    ]
    for dom, traces in cases:
        for t in traces:
            assert accepts_po_asp(dom, t) == derivable_po_bruteforce(dom, t, max_len=max(len(t), 1)), (dom, t)


def _small(rng):
    prims = [f"p{i}" for i in range(rng.randint(1, 2))]
    comps = ["S"] + [f"C{i}" for i in range(rng.randint(0, 1))]
    methods, mid = [], 0
    for ci, c in enumerate(comps):
        later = comps[ci + 1:]
        for _ in range(rng.randint(1, 2)):
            k = rng.randint(0, 3)
            choices = prims + later
            subs = tuple(rng.choice(choices) for _ in range(k)) if choices else ()
            perm = list(range(k)); rng.shuffle(perm); rank = {x: r for r, x in enumerate(perm)}
            order = frozenset((i, j) for i in range(k) for j in range(k)
                              if i != j and rank[i] < rank[j] and rng.random() < 0.5)
            methods.append(POMethod(f"m{mid}", c, subs, order)); mid += 1
    return PODomain(frozenset(prims), frozenset(comps), tuple(methods), "S")


@pytest.mark.parametrize("seed", range(20))
def test_asp_matches_oracle_small(seed):
    rng = random.Random(seed)
    dom = _small(rng)
    prims = sorted(dom.primitives)
    for _ in range(3):
        t = tuple(rng.choice(prims) for _ in range(rng.randint(0, 3)))
        assert accepts_po_asp(dom, t) == derivable_po_bruteforce(dom, t, max_len=max(len(t), 1)), (dom, t)
