"""Pin the canonical conformance-leak gadget.

This test encodes, as an executable specification, the exact scientific claim of
the project on the smallest possible example. If it ever breaks, the central
phenomenon (or the code that measures it) has changed and must be re-examined
before any results are trusted.
"""
from __future__ import annotations

from tcr.cfg.membership import accepts, language_sample
from tcr.core.types import Domain, Method, RepairInstance
from tcr.htn.corrupt import delete_action_everywhere
from tcr.metrics.conformance import gap_over_repairs, score
from tcr.negatives.generate import generate_negatives, gold_positive_traces
from tcr.repair.candidates import target_valid_repairs
from tcr.repair.selector import cost_only_indifference, select_conformance


def _leak_domain():
    methods = (
        Method("m_s1", "S", ("Main",)),
        Method("m_s2", "S", ("Alt",)),
        Method("m_main", "Main", ("a", "G", "b")),
        Method("m_alt", "Alt", ("b", "G", "a")),
        Method("m_g", "G", ("crit",)),
    )
    return Domain(
        frozenset({"a", "b", "crit"}),
        frozenset({"S", "Main", "Alt", "G"}),
        methods,
        "S",
    )


def test_gold_language_is_two_orderings():
    gold = _leak_domain()
    lang = set(language_sample(gold, 5, limit=50))
    assert lang == {("a", "crit", "b"), ("b", "crit", "a")}


def test_three_target_valid_repairs_two_leak():
    gold = _leak_domain()
    target = ("a", "crit", "b")
    flawed = delete_action_everywhere(gold, "crit")
    assert not accepts(flawed, target)
    inst = RepairInstance("leak", flawed, gold, target, "crit", {"family": "leak"})
    repairs = target_valid_repairs(inst)
    assert len(repairs) == 3

    # exactly one repair (insertion into the shared G) recovers the full gold
    # language; the other two leak by admitting a gold-rejected trace
    conformant = 0
    for r in repairs:
        d = r.apply(flawed)
        lang = set(language_sample(d, 5, limit=50))
        if lang == {("a", "crit", "b"), ("b", "crit", "a")}:
            conformant += 1
    assert conformant == 1


def test_gap_is_two_thirds_and_selector_closes_it():
    gold = _leak_domain()
    target = ("a", "crit", "b")
    flawed = delete_action_everywhere(gold, "crit")
    inst = RepairInstance("leak", flawed, gold, target, "crit", {"family": "leak"})
    repairs = target_valid_repairs(inst)
    negs = generate_negatives(gold, target, "gold_structural", seed=0, n=64)
    labeled = gold_positive_traces(gold, target) + negs
    report = gap_over_repairs(flawed, repairs, labeled)
    assert abs(report.conformance_gap - 2 / 3) < 1e-9

    # our selector achieves perfect rejection; cost-only expected is strictly worse
    scf = select_conformance(flawed, repairs, labeled)
    indiff = cost_only_indifference(flawed, repairs, labeled)
    assert scf.score.rejection == 1.0
    assert indiff["expected_rejection"] < 1.0
    assert scf.score.rejection > indiff["expected_rejection"]
