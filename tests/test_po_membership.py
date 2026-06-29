"""Differential + unit tests pinning the PO-HTN recognizer to a brute-force oracle.

Same trust-anchor discipline as the TO Earley verifier: if these pass, ``accepts_po``
is trustworthy on the small pruned PO domains the study uses.
"""
from __future__ import annotations

import random

import pytest

from tcr.cfg.po_membership import accepts_po, derivable_po_bruteforce
from tcr.core.po_types import PODomain, POMethod


def _dom(methods, prims, comps, initial="S"):
    return PODomain(frozenset(prims), frozenset(comps), tuple(methods), initial)


# -- hand-built cases ---------------------------------------------------------
def test_unordered_two():
    # S -> {x, y} with no order: both orders valid
    d = _dom([POMethod("m", "S", ("x", "y"), frozenset())], {"x", "y"}, {"S"})
    assert accepts_po(d, ("x", "y"))
    assert accepts_po(d, ("y", "x"))
    assert not accepts_po(d, ("x", "x"))
    assert not accepts_po(d, ("x",))


def test_partial_order_join():
    # S -> {x, y, z} with x<z and y<z : x,y interleave but both before z
    d = _dom([POMethod("m", "S", ("x", "y", "z"), frozenset({(0, 2), (1, 2)}))],
             {"x", "y", "z"}, {"S"})
    assert accepts_po(d, ("x", "y", "z"))
    assert accepts_po(d, ("y", "x", "z"))
    assert not accepts_po(d, ("z", "x", "y"))
    assert not accepts_po(d, ("x", "z", "y"))


def test_total_order_special_case():
    # totally-ordered method: only one linearization
    d = _dom([POMethod.total("m", "S", ("x", "y", "z"))], {"x", "y", "z"}, {"S"})
    assert accepts_po(d, ("x", "y", "z"))
    assert not accepts_po(d, ("y", "x", "z"))


def test_nested_unordered():
    # S -> {A, B} unordered ; A->a ; B->b  =>  ab, ba
    d = _dom([
        POMethod("m_s", "S", ("A", "B"), frozenset()),
        POMethod("m_a", "A", ("a",)),
        POMethod("m_b", "B", ("b",)),
    ], {"a", "b"}, {"S", "A", "B"})
    assert accepts_po(d, ("a", "b"))
    assert accepts_po(d, ("b", "a"))
    assert not accepts_po(d, ("a", "a"))


def test_nested_ordered_blocks_interleave():
    # S -> {A, B} with A<B ; A->{a1,a2} unordered ; B->b
    # A<B means BOTH of A's actions precede b; a1,a2 interleave
    d = _dom([
        POMethod("m_s", "S", ("A", "B"), frozenset({(0, 1)})),
        POMethod("m_a", "A", ("a1", "a2"), frozenset()),
        POMethod("m_b", "B", ("b",)),
    ], {"a1", "a2", "b"}, {"S", "A", "B"})
    assert accepts_po(d, ("a1", "a2", "b"))
    assert accepts_po(d, ("a2", "a1", "b"))
    assert not accepts_po(d, ("a1", "b", "a2"))  # b cannot come before a2 (A<B)


def test_epsilon_method():
    # S -> {A, x} ; A -> (empty) | a
    d = _dom([
        POMethod("m_s", "S", ("A", "x"), frozenset()),
        POMethod("m_a0", "A", (), frozenset()),
        POMethod("m_a1", "A", ("a",), frozenset()),
    ], {"a", "x"}, {"S", "A"})
    assert accepts_po(d, ("x",))            # A -> empty
    assert accepts_po(d, ("a", "x"))
    assert accepts_po(d, ("x", "a"))        # A,x unordered
    assert not accepts_po(d, ("a", "a", "x"))


# -- differential against the brute-force oracle ------------------------------
def _random_po_domain(rng):
    """Random ACYCLIC PO grammar: a compound may only expand to primitives or to
    compounds strictly later in the list, so the language is finite and the
    brute-force oracle terminates. Recursion is covered by the unit tests above
    (epsilon/nesting); here we stress the partial-order semantics."""
    prims = [f"p{i}" for i in range(rng.randint(1, 3))]
    comps = ["S"] + [f"C{i}" for i in range(rng.randint(0, 2))]
    methods = []
    mid = 0
    for ci, c in enumerate(comps):
        later = comps[ci + 1:]
        for _ in range(rng.randint(1, 2)):
            k = rng.randint(0, 3)
            choices = prims + later
            subs = tuple(rng.choice(choices) for _ in range(k)) if choices else ()
            perm = list(range(k))
            rng.shuffle(perm)
            rank = {idx: r for r, idx in enumerate(perm)}
            order = frozenset(
                (i, j) for i in range(k) for j in range(k)
                if i != j and rank[i] < rank[j] and rng.random() < 0.5
            )
            methods.append(POMethod(f"m{mid}", c, subs, order))
            mid += 1
    return PODomain(frozenset(prims), frozenset(comps), tuple(methods), "S")


@pytest.mark.parametrize("seed", range(150))
def test_po_matches_bruteforce(seed):
    rng = random.Random(seed)
    dom = _random_po_domain(rng)
    prims = sorted(dom.primitives)
    for _ in range(6):
        trace = tuple(rng.choice(prims) for _ in range(rng.randint(0, 4)))
        fast = accepts_po(dom, trace, budget=2_000_000)
        slow = derivable_po_bruteforce(dom, trace, max_len=max(len(trace), 1))
        assert fast == slow, (dom, trace, fast, slow)
