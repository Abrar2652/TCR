"""Tests for the Allen-style temporal layer.

Covers: the interval algebra (every relation + converse symmetry), the
totally-ordered reachability invariant (overlaps never occurs on TO-HTN spans),
span extraction correctness, timeline extraction from gold, and the end-to-end
ability to distinguish a timeline-preserving repair from a timeline-breaking one.
"""
from __future__ import annotations

import random

import pytest

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, Method, RepairInstance
from tcr.data.synthetic import FAMILIES, generate
from tcr.htn.corrupt import corrupt_single, delete_action_everywhere
from tcr.repair.candidates import target_valid_repairs
from tcr.temporal.allen import Allen, TO_REACHABLE, converse, relate
from tcr.temporal.spans import compound_spans
from tcr.temporal.timeline import check_timeline, extract_timeline


# -- Allen algebra ------------------------------------------------------------
def test_relate_basic_cases():
    assert relate(0, 2, 3, 5) == Allen.BEFORE
    assert relate(3, 5, 0, 2) == Allen.AFTER
    assert relate(0, 2, 2, 4) == Allen.MEETS
    assert relate(2, 4, 0, 2) == Allen.MET_BY
    assert relate(1, 2, 0, 3) == Allen.DURING
    assert relate(0, 3, 1, 2) == Allen.CONTAINS
    assert relate(0, 1, 0, 3) == Allen.STARTS
    assert relate(0, 3, 0, 1) == Allen.STARTED_BY
    assert relate(2, 3, 0, 3) == Allen.FINISHES
    assert relate(0, 3, 2, 3) == Allen.FINISHED_BY
    assert relate(0, 3, 0, 3) == Allen.EQUALS
    assert relate(0, 3, 2, 5) == Allen.OVERLAPS
    assert relate(2, 5, 0, 3) == Allen.OVERLAPPED_BY


def test_converse_symmetry():
    # relate(A,B) must be the converse of relate(B,A) for all proper intervals
    rng = random.Random(0)
    for _ in range(2000):
        a0 = rng.randint(0, 6); a1 = a0 + rng.randint(1, 4)
        b0 = rng.randint(0, 6); b1 = b0 + rng.randint(1, 4)
        r_ab = relate(a0, a1, b0, b1)
        r_ba = relate(b0, b1, a0, a1)
        assert r_ab == converse(r_ba)


def test_improper_interval_raises():
    with pytest.raises(ValueError):
        relate(2, 2, 0, 3)


# -- span extraction ----------------------------------------------------------
def test_compound_spans_nesting():
    # S -> A B ; A -> a ; B -> b c  on trace (a,b,c)
    dom = Domain(
        frozenset({"a", "b", "c"}),
        frozenset({"S", "A", "B"}),
        (Method("m0", "S", ("A", "B")), Method("m1", "A", ("a",)),
         Method("m2", "B", ("b", "c"))),
        "S",
    )
    spans = compound_spans(dom, ("a", "b", "c"))
    by_task = {s.task: (s.start, s.end) for s in spans}
    assert by_task["S"] == (0, 3)
    assert by_task["A"] == (0, 1)
    assert by_task["B"] == (1, 3)


def test_compound_spans_none_when_not_derivable():
    dom = Domain(frozenset({"a"}), frozenset({"S"}), (Method("m0", "S", ("a",)),), "S")
    assert compound_spans(dom, ("a", "a")) is None


# -- TO reachability invariant ------------------------------------------------
@pytest.mark.parametrize("family", FAMILIES)
def test_no_overlaps_in_totally_ordered_domains(family):
    """The headline temporal invariant: TO-HTN spans never produce `overlaps`.

    If this fails, either span extraction is wrong or a domain is not actually
    totally ordered. Every pairwise relation among compound spans of a gold
    derivation must be in TO_REACHABLE (i.e. not overlaps/overlapped_by).
    """
    gen = generate(family, seed=2)
    spans = compound_spans(gen.domain, gen.target)
    assert spans is not None
    for i in range(len(spans)):
        for j in range(len(spans)):
            if i == j:
                continue
            a, b = spans[i], spans[j]
            if a.length == 0 or b.length == 0:
                continue
            rel = relate(a.start, a.end, b.start, b.end)
            assert rel in TO_REACHABLE, (family, a, b, rel)
            assert rel not in (Allen.OVERLAPS, Allen.OVERLAPPED_BY)


# -- timeline extraction + check ---------------------------------------------
def _leak_domain():
    methods = (
        Method("m_s1", "S", ("Main",)),
        Method("m_s2", "S", ("Alt",)),
        Method("m_main", "Main", ("a", "G", "b")),
        Method("m_alt", "Alt", ("b", "G", "a")),
        Method("m_g", "G", ("crit",)),
    )
    return Domain(frozenset({"a", "b", "crit"}),
                  frozenset({"S", "Main", "Alt", "G"}), methods, "S")


def test_extract_timeline_reads_during_relation():
    gold = _leak_domain()
    spec = extract_timeline(gold, ("a", "crit", "b"))
    # G sits strictly inside Main and S
    assert spec.constraints[("G", "Main")] == frozenset({Allen.DURING})
    assert spec.constraints[("G", "S")] == frozenset({Allen.DURING})
    assert spec.constraints[("Main", "S")] == frozenset({Allen.EQUALS})


def test_timeline_distinguishes_conformant_from_leaky_repair():
    gold = _leak_domain()
    target = ("a", "crit", "b")
    spec = extract_timeline(gold, target)
    flawed = delete_action_everywhere(gold, "crit")
    inst = RepairInstance("leak", flawed, gold, target, "crit", {"family": "leak"})
    repairs = target_valid_repairs(inst)

    verdicts = []
    for r in repairs:
        d = r.apply(flawed)
        rep = check_timeline(d, target, spec)
        verdicts.append(rep.conformant)
    # exactly one repair (insertion into the shared G) preserves the timeline
    assert sum(verdicts) == 1


def test_timeline_flags_collapsed_task_as_violation():
    # inserting the action outside G leaves G empty -> empty-span anomaly
    gold = _leak_domain()
    target = ("a", "crit", "b")
    spec = extract_timeline(gold, target)
    flawed = delete_action_everywhere(gold, "crit")
    # craft the leaky repair explicitly: insert crit into m_main
    inst = RepairInstance("leak", flawed, gold, target, "crit", {"family": "leak"})
    repairs = target_valid_repairs(inst)
    leaky = [r for r in repairs if r.insertions[0][1] == "m_main"]
    assert leaky
    d = leaky[0].apply(flawed)
    rep = check_timeline(d, target, spec)
    assert not rep.conformant
    assert any(v.observed == "empty-span" for v in rep.violations)


# -- two-layer independence ---------------------------------------------------
@pytest.mark.parametrize("family", ["branch_suffix", "shared_setup", "finish_suffix", "nested_phase"])
def test_timeline_layer_runs_on_all_ambiguous_families(family):
    gen = generate(family, seed=2)
    inst = corrupt_single(gen)
    assert inst is not None
    spec = extract_timeline(inst.gold, inst.target)
    repairs = target_valid_repairs(inst)
    # at least one repair must be timeline-conformant (the gold-equivalent one)
    conformant = 0
    for r in repairs:
        d = r.apply(inst.flawed)
        if check_timeline(d, inst.target, spec).conformant:
            conformant += 1
    assert conformant >= 1
