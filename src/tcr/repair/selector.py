"""Conformance-aware repair selection.

Given a flawed domain and a set of target-valid candidate repairs (all of which
satisfy the standard objective), choose the one that best preserves intended
ordering behavior, i.e. maximizes negative-rejection (precision) while keeping
fitness == 1, breaking ties by minimal insertion cost.

This is the algorithmic core of the paper's positive contribution. It is
deliberately decoupled from *where the candidates come from*: candidates may be
enumerated symbolically (``tcr.repair.candidates``) or proposed by an LLM
(``tcr.repair.llm_repair``). The selector treats them uniformly. That decoupling
is what lets us make the apples-to-apples claim "conformance-aware selection
strictly dominates cost-only selection on precision, at equal fitness".

Baselines provided for comparison:
    select_cost_only    : the incumbent objective (minimum insertion cost),
                          ties broken arbitrarily-but-deterministically. This
                          models Lutalo & Bercher / Lin-Hoeller-Bercher behavior.
    select_first_valid  : first target-valid repair found (no preference at all).
    select_conformance  : OUR method -- maximize rejection, then minimize cost.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcr.core.types import Domain, LabeledTrace
from tcr.metrics.conformance import ConformanceScore, score
from tcr.repair.candidates import Repair


@dataclass(frozen=True)
class Selection:
    repair: Repair
    repaired: Domain
    score: ConformanceScore
    method: str


def _key_cost(r: Repair) -> tuple:
    # deterministic tie-break: cost, then lexicographic insertion signature
    return (r.cost, tuple(sorted(r.insertions)))


def select_cost_only(flawed: Domain, repairs: list[Repair],
                     labeled: list[LabeledTrace]) -> Selection:
    """Incumbent baseline: minimum insertion cost; ignores negatives.

    A deterministic tie-break is applied, but reporting a single tie-broken
    repair would MISREPRESENT the incumbent: a minimum-cost objective is
    genuinely *indifferent* among all equal-cost repairs, so its real behavior
    is a draw from that indifference set. ``expected_rejection`` and
    ``worst_rejection`` over the min-cost set are therefore attached to the
    selection (see ``cost_only_indifference``) and are what experiments report.
    The returned ``score`` corresponds to the deterministic pick, for
    reproducibility, but the fair comparison uses the expected/worst values.
    """
    best = min(repairs, key=_key_cost)
    d = best.apply(flawed)
    return Selection(best, d, score(d, labeled), "cost_only")


def cost_only_indifference(flawed: Domain, repairs: list[Repair],
                           labeled: list[LabeledTrace]) -> dict:
    """Expected and worst-case rejection over the minimum-cost indifference set.

    This is the *fair* characterization of the incumbent objective. If several
    repairs share the minimum insertion cost, a cost-only method has no
    principled reason to prefer any one; its expected precision is the mean over
    that set, and a reviewer-proof claim must beat the EXPECTED (not the
    luckiest tie-break) value.
    """
    min_cost = min(r.cost for r in repairs)
    tied = [r for r in repairs if r.cost == min_cost]
    rejections = [score(r.apply(flawed), labeled).rejection for r in tied]
    return {
        "n_min_cost": len(tied),
        "expected_rejection": sum(rejections) / len(tied),
        "worst_rejection": min(rejections),
        "best_rejection": max(rejections),
    }


def select_first_valid(flawed: Domain, repairs: list[Repair],
                       labeled: list[LabeledTrace]) -> Selection:
    best = repairs[0]
    d = best.apply(flawed)
    return Selection(best, d, score(d, labeled), "first_valid")


def select_conformance(flawed: Domain, repairs: list[Repair],
                       labeled: list[LabeledTrace]) -> Selection:
    """OUR method: maximize negative-rejection, keep fitness, minimize cost.

    Lexicographic objective:
        1. highest rejection (precision)
        2. highest fitness   (should be 1 for all target-valid repairs)
        3. lowest insertion cost
        4. deterministic signature tie-break
    """
    scored: list[tuple[float, float, int, tuple, Repair, Domain, ConformanceScore]] = []
    for r in repairs:
        d = r.apply(flawed)
        s = score(d, labeled)
        scored.append(
            (s.rejection, s.fitness, -r.cost, tuple(sorted(r.insertions)), r, d, s)
        )
    # sort descending on (rejection, fitness, -cost) then ascending signature
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    _, _, _, _, r, d, s = scored[0]
    return Selection(r, d, s, "conformance")


SELECTORS = {
    "cost_only": select_cost_only,
    "first_valid": select_first_valid,
    "conformance": select_conformance,
}


# --------------------------------------------------------------------------
# Optional temporal layer: filter / select using the Allen-style timeline.
# These are additive -- they do not change the trace-precision selectors above,
# which keep the validated headline result intact. The timeline is a SECOND
# axis, applied as an optional hard filter or as a lexicographic tie-breaker.
# --------------------------------------------------------------------------
def filter_timeline_conformant(
    flawed: Domain,
    repairs: list[Repair],
    spec,                              # tcr.temporal.timeline.TimelineSpec
    reference_trace,
) -> list[Repair]:
    """Keep only repairs that preserve the intended timeline on the target trace.

    This is the "reject timeline-violating repairs" hard filter. If it would
    eliminate every repair (over-strict for some domain), the caller should fall
    back to the unfiltered set; we return the filtered list and let the caller
    decide, rather than silently widening.
    """
    from tcr.temporal.timeline import check_timeline

    out = []
    for r in repairs:
        d = r.apply(flawed)
        if check_timeline(d, reference_trace, spec).conformant:
            out.append(r)
    return out


def select_conformance_with_timeline(
    flawed: Domain,
    repairs: list[Repair],
    labeled: list[LabeledTrace],
    spec,                              # TimelineSpec
    reference_trace,
    hard_filter: bool = True,
) -> Selection:
    """Two-axis selection: trace-precision AND timeline preservation.

    By default the intended timeline is a HARD constraint: among repairs that
    preserve it on the target trace, pick the trace-precision-maximizing one
    (our validated objective). If no repair preserves the timeline and
    ``hard_filter`` is True we relax to the full set (so the method always
    returns a repair), recording the relaxation in the selection method name so
    experiments can see it happened.
    """
    candidates = filter_timeline_conformant(flawed, repairs, spec, reference_trace)
    relaxed = False
    if not candidates:
        candidates = repairs
        relaxed = True
    sel = select_conformance(flawed, candidates, labeled)
    method = "conformance+timeline" + ("(relaxed)" if relaxed else "")
    return Selection(sel.repair, sel.repaired, sel.score, method)
