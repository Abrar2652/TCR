"""Pipeline tests: corruption non-triviality, candidate validity, negative
soundness, metric correctness, and the core scientific invariants.
"""
from __future__ import annotations

import random

import pytest

from tcr.cfg.membership import accepts
from tcr.data.synthetic import FAMILIES, generate, generate_suite
from tcr.htn.corrupt import build_instances, corrupt_single, delete_action_everywhere
from tcr.metrics.conformance import gap_over_repairs, score
from tcr.negatives.generate import REGIMES, generate_negatives, gold_positive_traces
from tcr.repair.candidates import Repair, target_valid_repairs
from tcr.repair.selector import select_conformance, select_cost_only


# -- corruption ---------------------------------------------------------------
@pytest.mark.parametrize("family", FAMILIES)
def test_corruption_is_nontrivial(family):
    gen = generate(family, seed=1)
    inst = corrupt_single(gen)
    if inst is None:
        pytest.skip("corruption trivial for this family/seed")
    # gold accepts target, flawed does not -- the defining property
    assert accepts(inst.gold, inst.target)
    assert not accepts(inst.flawed, inst.target)


def test_delete_action_removes_all_occurrences():
    gen = generate("linear_control", seed=3)
    flawed = delete_action_everywhere(gen.domain, gen.critical_action)
    for m in flawed.methods:
        assert gen.critical_action not in m.body


# -- candidate repairs --------------------------------------------------------
@pytest.mark.parametrize("family", FAMILIES)
def test_target_valid_repairs_actually_valid(family):
    gen = generate(family, seed=2)
    inst = corrupt_single(gen)
    if inst is None:
        pytest.skip("trivial")
    repairs = target_valid_repairs(inst)
    assert repairs, "expected at least one target-valid repair"
    for r in repairs:
        assert accepts(r.apply(inst.flawed), inst.target)


def test_reinserting_at_gold_position_recovers_target():
    # sanity: the original (gold) domain accepts the target after we delete and
    # there exists at least one insertion that restores it
    gen = generate("branch_suffix", seed=5)
    inst = corrupt_single(gen)
    assert inst is not None
    repairs = target_valid_repairs(inst)
    assert any(accepts(r.apply(inst.flawed), inst.target) for r in repairs)


# -- negatives ----------------------------------------------------------------
@pytest.mark.parametrize("regime", REGIMES)
def test_negatives_are_gold_rejected(regime):
    gen = generate("nested_phase", seed=4)
    inst = corrupt_single(gen)
    if inst is None:
        pytest.skip("trivial")
    negs = generate_negatives(inst.gold, inst.target, regime, seed=11, n=16)
    # every generated negative MUST be rejected by the gold domain -- this is the
    # defensible-by-construction guarantee
    for lt in negs:
        assert lt.positive is False
        assert not accepts(inst.gold, lt.trace)


def test_positive_target_is_gold_accepted():
    gen = generate("shared_setup", seed=6)
    inst = corrupt_single(gen)
    assert inst is not None
    pos = gold_positive_traces(inst.gold, inst.target)
    for lt in pos:
        assert lt.positive
        assert accepts(inst.gold, lt.trace)


# -- metrics ------------------------------------------------------------------
def test_score_bounds():
    gen = generate("branch_suffix", seed=8)
    inst = corrupt_single(gen)
    assert inst is not None
    negs = generate_negatives(inst.gold, inst.target, "permute_oracle", seed=1, n=16)
    pos = gold_positive_traces(inst.gold, inst.target)
    labeled = pos + negs
    repairs = target_valid_repairs(inst)
    for r in repairs:
        s = score(r.apply(inst.flawed), labeled)
        assert 0.0 <= s.fitness <= 1.0
        assert 0.0 <= s.rejection <= 1.0
        # every target-valid repair must have fitness 1 on the target
        assert s.fitness == 1.0


# -- core scientific invariants ----------------------------------------------
def test_linear_control_has_zero_gap():
    """The negative control: ambiguity-free family must show no conformance gap.

    If this ever fails, the evaluator is manufacturing spurious failures and no
    result is trustworthy. This is the single most important sanity test in the
    project.
    """
    suite = generate_suite(n_per_family=20, base_seed=7)
    instances = [i for i in build_instances(suite) if i.metadata["family"] == "linear_control"]
    assert instances, "expected linear_control instances"
    for inst in instances:
        repairs = target_valid_repairs(inst)
        if not repairs:
            continue
        for regime in REGIMES:
            negs = generate_negatives(inst.gold, inst.target, regime, seed=2, n=24)
            labeled = gold_positive_traces(inst.gold, inst.target) + negs
            report = gap_over_repairs(inst.flawed, repairs, labeled)
            assert report.conformance_gap == 0.0, (inst.name, regime, report)


def test_conformance_selector_never_worse_than_cost_only():
    """Ours must dominate the incumbent on rejection at equal fitness."""
    suite = generate_suite(n_per_family=20, base_seed=7)
    for inst in build_instances(suite):
        repairs = target_valid_repairs(inst)
        if len(repairs) < 2:
            continue
        for regime in REGIMES:
            negs = generate_negatives(inst.gold, inst.target, regime, seed=3, n=24)
            labeled = gold_positive_traces(inst.gold, inst.target) + negs
            sc = select_cost_only(inst.flawed, repairs, labeled)
            scf = select_conformance(inst.flawed, repairs, labeled)
            assert scf.score.fitness == 1.0
            assert scf.score.rejection >= sc.score.rejection - 1e-12


def test_repair_apply_is_order_independent_for_distinct_methods():
    gen = generate("nested_phase", seed=9)
    inst = corrupt_single(gen)
    assert inst is not None
    act = inst.deleted_action
    r1 = Repair(((act, "m_main", 0), (act, "m_alt", 1)))
    r2 = Repair(((act, "m_alt", 1), (act, "m_main", 0)))
    assert r1.apply(inst.flawed).signature() == r2.apply(inst.flawed).signature()
