"""The Allen-style temporal layer: extract the intended timeline, then check it.

This is the second verification layer described in the project upgrade. The
first layer (stack/CYK, ``tcr.cfg.membership``) verifies *hierarchical* validity:
is the trace derivable at all. This layer verifies *temporal* validity: does the
repaired domain preserve the intended relations among compound-task intervals.

Pipeline
--------
1. EXTRACT (from gold): parse the gold domain's intended trace into compound
   spans and read off the Allen relation between every pair of compound-task
   *types* that co-occur. This is the intended timeline -- a set of constraints
   of the form ``rel(TaskX, TaskY)``. Because it is read from the gold domain,
   it is specification, not hand-authored opinion (the same oracle principle the
   negative traces use). Manual overrides are supported for relations the gold
   structure underdetermines.

2. CHECK (against a repaired domain on a trace): parse the trace in the repaired
   domain, compute the actual relations between the same compound pairs, and
   report which intended constraints are violated.

A repaired domain is TIMELINE-CONFORMANT on a trace iff every intended relation
that applies to that trace is preserved. This is reported as its own axis,
separate from trace-precision, and can optionally be used as a hard filter on
candidate repairs.

Pairing by task type vs occurrence
-----------------------------------
A compound type may occur multiple times (recursion). We key intended
constraints by unordered type pair and require that for each co-occurring pair
of *occurrences* the observed relation is consistent with the intended relation
for that type pair. When a type pair shows multiple relations in gold (e.g. one
``before`` and one ``contains`` across different occurrences), the intended
constraint for that pair is the SET of relations gold exhibits, and a repair is
conformant if each observed occurrence-relation lies in that set. This keeps the
check sound without over-constraining naturally multi-relational hierarchies.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from tcr.core.types import Domain, Task, Trace
from tcr.temporal.allen import Allen, relate
from tcr.temporal.spans import Span, compound_spans


def _pair_key(x: Task, y: Task) -> tuple[Task, Task]:
    return (x, y) if x <= y else (y, x)


def _relation_for_pair(spans_a: Span, spans_b: Span) -> Allen:
    """Allen relation of occurrence A to B, keyed canonically by task name order.

    We orient the relation so it is reported from the lexicographically-smaller
    task to the larger, so the same unordered pair always yields a comparable
    relation regardless of span ordering.
    """
    if spans_a.task <= spans_b.task:
        return relate(spans_a.start, spans_a.end, spans_b.start, spans_b.end)
    return relate(spans_b.start, spans_b.end, spans_a.start, spans_a.end)


@dataclass(frozen=True)
class TimelineSpec:
    """Intended Allen relations among compound-task types, read from gold.

    ``constraints[(X, Y)]`` (with X <= Y) is the set of Allen relations the gold
    derivation exhibits between occurrences of X and Y. A repair must keep every
    observed occurrence-relation within the corresponding set.
    """

    constraints: dict[tuple[Task, Task], frozenset[Allen]]
    reference_trace: Trace = ()
    overrides: dict[tuple[Task, Task], frozenset[Allen]] = field(default_factory=dict)

    def applicable(self, x: Task, y: Task) -> frozenset[Allen] | None:
        key = _pair_key(x, y)
        if key in self.overrides:
            return self.overrides[key]
        return self.constraints.get(key)


def extract_timeline(
    gold: Domain,
    trace: Trace,
    overrides: dict[tuple[Task, Task], frozenset[Allen]] | None = None,
) -> TimelineSpec:
    """Read the intended timeline (Allen relations) off the gold derivation."""
    spans = compound_spans(gold, trace)
    if spans is None:
        raise ValueError("gold does not derive the reference trace; cannot extract timeline")
    constraints: dict[tuple[Task, Task], set[Allen]] = defaultdict(set)
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            sa, sb = spans[i], spans[j]
            key = _pair_key(sa.task, sb.task)
            constraints[key].add(_relation_for_pair(sa, sb))
    frozen = {k: frozenset(v) for k, v in constraints.items()}
    return TimelineSpec(frozen, tuple(trace), overrides or {})


@dataclass(frozen=True)
class TimelineViolation:
    pair: tuple[Task, Task]
    observed: Allen | str           # an Allen relation, or "empty-span" anomaly
    intended: frozenset[Allen]


@dataclass(frozen=True)
class TimelineReport:
    derivable: bool                 # did the repaired domain derive the trace at all
    n_checked: int                  # number of occurrence-pairs checked
    violations: tuple[TimelineViolation, ...]

    @property
    def conformant(self) -> bool:
        # a trace the repaired domain cannot derive is not a timeline violation
        # here -- hierarchical validity is checked by the stack layer separately;
        # this layer reports conformance only over what is derivable.
        return self.derivable and len(self.violations) == 0


def check_timeline(
    repaired: Domain, trace: Trace, spec: TimelineSpec
) -> TimelineReport:
    """Check whether ``repaired`` preserves the intended timeline on ``trace``."""
    spans = compound_spans(repaired, trace)
    if spans is None:
        return TimelineReport(derivable=False, n_checked=0, violations=())
    violations: list[TimelineViolation] = []
    checked = 0
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            sa, sb = spans[i], spans[j]
            intended = spec.applicable(sa.task, sb.task)
            if intended is None:
                continue  # no intended constraint for this pair
            checked += 1
            # an empty compound span means a task that should cover actions now
            # covers none (it collapsed under the repair) -- a timeline anomaly
            if sa.length == 0 or sb.length == 0:
                violations.append(
                    TimelineViolation(_pair_key(sa.task, sb.task), "empty-span", intended)
                )
                continue
            observed = _relation_for_pair(sa, sb)
            if observed not in intended:
                violations.append(
                    TimelineViolation(_pair_key(sa.task, sb.task), observed, intended)
                )
    return TimelineReport(True, checked, tuple(violations))
