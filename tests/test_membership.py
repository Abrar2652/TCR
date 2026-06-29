"""Differential tests pinning the fast CYK recognizer to a naive oracle.

If these pass, the verifier -- the component every other result depends on -- is
trustworthy. We test on random small grammars and on hand-built edge cases
(epsilon bodies, unit productions, recursion, shared suffixes).
"""
from __future__ import annotations

import random

import pytest

from tcr.cfg.bruteforce import derivable_bruteforce
from tcr.cfg.membership import accepts
from tcr.core.types import Domain, Method


def _random_domain(rng: random.Random) -> Domain:
    primitives = [f"a{i}" for i in range(rng.randint(1, 3))]
    compounds = ["S"] + [f"C{i}" for i in range(rng.randint(0, 2))]
    methods = []
    mid = 0
    for c in compounds:
        for _ in range(rng.randint(1, 2)):
            blen = rng.randint(0, 3)
            body = tuple(rng.choice(primitives + compounds) for _ in range(blen))
            methods.append(Method(f"m{mid}", c, body))
            mid += 1
    return Domain(frozenset(primitives), frozenset(compounds), tuple(methods), "S")


def _random_trace(rng: random.Random, primitives) -> tuple:
    return tuple(rng.choice(primitives) for _ in range(rng.randint(0, 4)))


@pytest.mark.parametrize("seed", range(200))
def test_cyk_matches_bruteforce(seed):
    rng = random.Random(seed)
    dom = _random_domain(rng)
    primitives = sorted(dom.primitives)
    for _ in range(8):
        trace = _random_trace(rng, primitives)
        fast = accepts(dom, trace)
        slow = derivable_bruteforce(dom, trace)
        assert fast == slow, (dom, trace, fast, slow)


def test_epsilon_body():
    # S -> A a ; A -> (empty) | a   so S derives "a" and "a a"
    dom = Domain(
        frozenset({"a"}),
        frozenset({"S", "A"}),
        (
            Method("m0", "S", ("A", "a")),
            Method("m1", "A", ()),
            Method("m2", "A", ("a",)),
        ),
        "S",
    )
    assert accepts(dom, ("a",))
    assert accepts(dom, ("a", "a"))
    assert not accepts(dom, ("a", "a", "a", "a"))


def test_unit_production():
    # S -> A ; A -> a
    dom = Domain(
        frozenset({"a"}),
        frozenset({"S", "A"}),
        (Method("m0", "S", ("A",)), Method("m1", "A", ("a",))),
        "S",
    )
    assert accepts(dom, ("a",))
    assert not accepts(dom, ("a", "a"))


def test_recursion_bounded():
    # S -> a S | a   (a+)
    dom = Domain(
        frozenset({"a"}),
        frozenset({"S"}),
        (Method("m0", "S", ("a", "S")), Method("m1", "S", ("a",))),
        "S",
    )
    assert accepts(dom, ("a",))
    assert accepts(dom, ("a", "a", "a"))
    assert not accepts(dom, ())


def test_unknown_symbol_rejected():
    dom = Domain(frozenset({"a"}), frozenset({"S"}), (Method("m0", "S", ("a",)),), "S")
    assert not accepts(dom, ("b",))
