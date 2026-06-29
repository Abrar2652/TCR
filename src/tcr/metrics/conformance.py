"""Conformance metrics for repaired HTN domains.

The intellectual move of the paper, made precise here. Process mining (van der
Aalst; Munoz-Gama & Carmona, BPM 2010) evaluates a model against observed
behavior along two axes:

    fitness / recall   : does the model still ACCEPT the behavior it should?
    precision          : does the model REFRAIN from accepting behavior it
                         should not?

Target-trace-only repair (Lutalo & Bercher 2026; Lin, Hoeller & Bercher 2024)
optimizes fitness alone. A repair that makes the target derivable but also
admits invalid reordered traces has perfect fitness and poor precision. We make
that quantitative.

Definitions (sample-based, log-relative -- the principled choice given that an
exact global "never over-accepts" guarantee is uncomputable for context-free
languages; see survey by Bercher, Sreedharan & Vallati, IJCAI 2025):

    P+ = set of positive (must-accept) traces
    P- = set of negative (must-reject) traces

    fitness(D)      = |{t in P+ : D accepts t}|      / |P+|
    rejection(D)    = |{t in P- : D rejects t}|      / |P-|     (== precision proxy)
    conformant(D)   = fitness(D) == 1 and rejection(D) == 1

A repair is TARGET-VALID if it accepts the single target trace (fitness over the
target alone is 1). Among target-valid repairs, the CONFORMANCE GAP is the
fraction that are NOT fully conformant -- i.e. that over-accept at least one
negative. A gap > 0 demonstrates underspecification: the target-trace objective
does not determine the rejection behavior.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, LabeledTrace


@dataclass(frozen=True)
class ConformanceScore:
    fitness: float          # recall over positive traces
    rejection: float        # precision proxy: fraction of negatives correctly rejected
    n_positive: int
    n_negative: int

    @property
    def conformant(self) -> bool:
        return self.fitness >= 1.0 and self.rejection >= 1.0

    @property
    def f1(self) -> float:
        if self.fitness + self.rejection == 0:
            return 0.0
        return 2 * self.fitness * self.rejection / (self.fitness + self.rejection)


def score(domain: Domain, labeled: list[LabeledTrace]) -> ConformanceScore:
    pos = [lt for lt in labeled if lt.positive]
    neg = [lt for lt in labeled if not lt.positive]
    fit = (
        sum(accepts(domain, lt.trace) for lt in pos) / len(pos) if pos else 1.0
    )
    rej = (
        sum(not accepts(domain, lt.trace) for lt in neg) / len(neg) if neg else 1.0
    )
    return ConformanceScore(fit, rej, len(pos), len(neg))


@dataclass(frozen=True)
class GapReport:
    n_target_valid: int          # repairs that make the target derivable
    n_conformant: int            # of those, how many also reject all negatives
    conformance_gap: float       # fraction of target-valid repairs that over-accept
    mean_rejection: float        # average negative-rejection over target-valid repairs
    best_rejection: float        # best achievable rejection among target-valid repairs


def gap_over_repairs(
    flawed: Domain,
    repairs: list,                # list[tcr.repair.candidates.Repair]
    labeled: list[LabeledTrace],
) -> GapReport:
    """Quantify the conformance gap over a set of target-valid repairs."""
    if not repairs:
        return GapReport(0, 0, 0.0, 0.0, 0.0)
    rejections: list[float] = []
    conformant = 0
    for r in repairs:
        d = r.apply(flawed)
        s = score(d, labeled)
        rejections.append(s.rejection)
        if s.conformant:
            conformant += 1
    n = len(repairs)
    gap = 1.0 - conformant / n
    return GapReport(
        n_target_valid=n,
        n_conformant=conformant,
        conformance_gap=gap,
        mean_rejection=sum(rejections) / n,
        best_rejection=max(rejections),
    )
