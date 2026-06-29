"""Restricted Allen-style interval relations over compound-task spans.

We compute the qualitative temporal relation between two intervals
``A = [a0, a1)`` and ``B = [b0, b1)`` on the trace timeline. We implement the
subset called out by the project spec -- before, meets, during, starts,
finishes, equals, plus overlaps -- together with their converses, which is what
"A before B" / "A during B" / "A overlaps B" / "A starts B" / "A finishes B"
require.

Reachability in TOTALLY-ORDERED HTN (important, stated rather than hidden)
-------------------------------------------------------------------------
In a totally-ordered HTN derivation, any two compound spans are either DISJOINT
(one strictly before the other, possibly meeting) or NESTED (one inside the
other, possibly sharing a boundary). They can never be *staggered*. Therefore,
over TO-HTN derivations only these relations can ever occur:

    before / after, meets / met_by, during / contains,
    starts / started_by, finishes / finished_by, equals

The genuine ``overlaps`` / ``overlapped_by`` relation (intervals that cross
without nesting) is UNREACHABLE in TO-HTN. It is implemented here and becomes
reachable only once partial-order HTN is added (see docs/PARTIAL_ORDER.md),
where two compounds may interleave. The timeline checker asserts this invariant
in tests, so an ``overlaps`` appearing on TO data would signal a span-extraction
bug, not a real timeline.

Intervals are half-open integer ranges over trace positions; we treat them as
proper intervals (length >= 1). A compound that emits a single primitive has
length 1 and is a degenerate-but-valid interval.
"""
from __future__ import annotations

from enum import Enum


class Allen(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    DURING = "during"
    CONTAINS = "contains"
    STARTS = "starts"
    STARTED_BY = "started_by"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    EQUALS = "equals"


# Relations that can actually arise between compound spans in a totally-ordered
# HTN derivation (see module docstring).
TO_REACHABLE = frozenset({
    Allen.BEFORE, Allen.AFTER, Allen.MEETS, Allen.MET_BY,
    Allen.DURING, Allen.CONTAINS, Allen.STARTS, Allen.STARTED_BY,
    Allen.FINISHES, Allen.FINISHED_BY, Allen.EQUALS,
})

_CONVERSE = {
    Allen.BEFORE: Allen.AFTER, Allen.AFTER: Allen.BEFORE,
    Allen.MEETS: Allen.MET_BY, Allen.MET_BY: Allen.MEETS,
    Allen.OVERLAPS: Allen.OVERLAPPED_BY, Allen.OVERLAPPED_BY: Allen.OVERLAPS,
    Allen.DURING: Allen.CONTAINS, Allen.CONTAINS: Allen.DURING,
    Allen.STARTS: Allen.STARTED_BY, Allen.STARTED_BY: Allen.STARTS,
    Allen.FINISHES: Allen.FINISHED_BY, Allen.FINISHED_BY: Allen.FINISHES,
    Allen.EQUALS: Allen.EQUALS,
}


def converse(rel: Allen) -> Allen:
    return _CONVERSE[rel]


def relate(a0: int, a1: int, b0: int, b1: int) -> Allen:
    """Return the Allen relation of interval A=[a0,a1) to B=[b0,b1).

    Both intervals must be proper (a0 < a1, b0 < b1); empty spans (a compound
    that emits no primitive, which can happen under a flawed/repaired domain) are
    not Allen intervals and must be screened out by the caller -- see
    ``tcr.temporal.timeline`` which reports an empty span as its own anomaly
    rather than forcing it through this function.
    """
    if not (a0 < a1 and b0 < b1):
        raise ValueError(f"improper interval: A=[{a0},{a1}) B=[{b0},{b1})")

    if a0 == b0 and a1 == b1:
        return Allen.EQUALS
    # equal start
    if a0 == b0:
        return Allen.STARTS if a1 < b1 else Allen.STARTED_BY
    # equal end
    if a1 == b1:
        return Allen.FINISHES if a0 > b0 else Allen.FINISHED_BY
    # strictly before / meets
    if a1 <= b0:
        return Allen.MEETS if a1 == b0 else Allen.BEFORE
    if b1 <= a0:
        return Allen.MET_BY if b1 == a0 else Allen.AFTER
    # nesting
    if a0 > b0 and a1 < b1:
        return Allen.DURING
    if a0 < b0 and a1 > b1:
        return Allen.CONTAINS
    # remaining staggered cases are genuine overlaps
    if a0 < b0 < a1 < b1:
        return Allen.OVERLAPS
    if b0 < a0 < b1 < a1:
        return Allen.OVERLAPPED_BY
    # should be unreachable
    raise AssertionError(
        f"uncovered Allen case A=[{a0},{a1}) B=[{b0},{b1})"
    )
