"""Timeline-conformance metric: the temporal analogue of trace-precision.

``tcr.metrics.conformance`` scores a repaired domain on whether it accepts/rejects
the right *traces*. This module scores a repaired domain on whether it preserves
the intended *timeline* (Allen relations among compound spans), giving a second,
independent conformance axis.

Two quantities, mirroring fitness/precision:

    timeline_fitness   : over the POSITIVE traces the repair should accept, the
                         fraction on which the intended timeline is preserved.
                         (A repair that derives the target but mangles the
                         compound timeline scores < 1 here even though trace
                         fitness is 1 -- the temporal layer's whole point.)

    timeline_precision : over the NEGATIVE traces, the fraction the repair keeps
                         out OF THE INTENDED TIMELINE. A negative trace is
                         timeline-rejected if the repaired domain either does not
                         derive it or derives it with a timeline violation. This
                         rewards repairs that don't smuggle in invalid orderings
                         even at the temporal-relation level.

The headline number is ``timeline_conformant`` = (timeline_fitness == 1 and
timeline_precision == 1): the repair preserves the intended timeline on
everything it should and admits no negative timeline.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcr.core.types import Domain, LabeledTrace
from tcr.temporal.timeline import TimelineSpec, check_timeline


@dataclass(frozen=True)
class TimelineScore:
    timeline_fitness: float
    timeline_precision: float
    n_positive: int
    n_negative: int

    @property
    def timeline_conformant(self) -> bool:
        return self.timeline_fitness >= 1.0 and self.timeline_precision >= 1.0


def score_timeline(
    domain: Domain, labeled: list[LabeledTrace], spec: TimelineSpec
) -> TimelineScore:
    pos = [lt for lt in labeled if lt.positive]
    neg = [lt for lt in labeled if not lt.positive]

    def preserves(trace) -> bool:
        return check_timeline(domain, trace, spec).conformant

    # positives: timeline must be preserved (and trace must remain derivable)
    fit = sum(preserves(lt.trace) for lt in pos) / len(pos) if pos else 1.0
    # negatives: timeline-rejected == not derivable OR derived-with-violation
    def timeline_rejects(trace) -> bool:
        rep = check_timeline(domain, trace, spec)
        return (not rep.derivable) or (len(rep.violations) > 0)

    prec = sum(timeline_rejects(lt.trace) for lt in neg) / len(neg) if neg else 1.0
    return TimelineScore(fit, prec, len(pos), len(neg))
