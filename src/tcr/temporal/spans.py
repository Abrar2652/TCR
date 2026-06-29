"""Recover the derivation tree (and hence compound-task spans) for a trace.

The CYK recognizer in ``tcr.cfg.membership`` answers *whether* a trace is
derivable. To talk about a *timeline* we need *where* each compound task sits in
the trace -- its interval. This module produces, for a derivable trace, the set
of compound-task occurrences each annotated with the half-open span
``[start, end)`` of trace positions it covers.

Why spans come from the hierarchy (not from action durations)
-------------------------------------------------------------
In an HTN derivation every compound task expands to a contiguous block of
primitive actions (for totally-ordered HTN). That block IS the task's interval
on the timeline -- no external duration data is needed, and the interval is
exactly "the stretch of the plan that this abstract task is responsible for".
Reading Allen relations off these spans therefore measures whether a repaired
domain preserves the *intended decomposition timeline*, which is the object the
gold domain specifies.

Ambiguity
---------
A trace may have several derivations. We extract spans from a single derivation
chosen deterministically (leftmost, lowest-method-id), which is sufficient for
the gold domain whose intended timeline we read off, and we expose
``all_derivation_spans`` for callers that need to reason over every parse. The
timeline-conformance metric uses the gold derivation as the reference, so the
choice is well-defined.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcr.core.types import Domain, Task, Trace


@dataclass(frozen=True)
class Span:
    """A compound-task occurrence covering trace positions [start, end)."""

    task: Task
    start: int
    end: int  # exclusive
    method_id: str  # the method used to expand this occurrence

    @property
    def length(self) -> int:
        return self.end - self.start

    def __repr__(self) -> str:  # compact, test-friendly
        return f"Span({self.task}[{self.start}:{self.end}] via {self.method_id})"


def _parse(domain: Domain, trace: Trace) -> list[Span] | None:
    """Return compound spans for one leftmost derivation, or None if not derivable.

    Recursive descent with memoized backtracking: ``solve(symbol, i)`` returns the
    list of (end_index, spans) ways ``symbol`` can derive trace[i:end]. We take
    the first success deterministically (methods tried in domain order, which the
    generators keep stable), giving a canonical derivation.
    """
    n = len(trace)
    memo: dict[tuple[Task, int], list[tuple[int, tuple[Span, ...]]]] = {}

    def solve(symbol: Task, i: int) -> list[tuple[int, tuple[Span, ...]]]:
        if symbol in domain.primitives:
            if i < n and trace[i] == symbol:
                return [(i + 1, ())]
            return []
        key = (symbol, i)
        if key in memo:
            return memo[key]
        results: list[tuple[int, tuple[Span, ...]]] = []
        for m in domain.methods_for(symbol):
            # derive the body sequentially from position i
            partials: list[tuple[int, tuple[Span, ...]]] = [(i, ())]
            for sub in m.body:
                nxt: list[tuple[int, tuple[Span, ...]]] = []
                for pos, acc in partials:
                    for end, spans in solve(sub, pos):
                        nxt.append((end, acc + spans))
                partials = nxt
                if not partials:
                    break
            for end, spans in partials:
                # record this compound occurrence's own span [i, end)
                own = Span(symbol, i, end, m.mid)
                results.append((end, spans + (own,)))
        memo[key] = results
        return results

    for end, spans in solve(domain.initial, 0):
        if end == n:
            # sort spans by (start, -length) for a stable, outer-first ordering
            ordered = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
            return ordered
    return None


def compound_spans(domain: Domain, trace: Trace) -> list[Span] | None:
    """Public API: compound-task spans for the canonical derivation of ``trace``.

    Returns None if the trace is not derivable (the temporal layer then has
    nothing to check -- hierarchical validity is a precondition, enforced by the
    stack/CYK checker first).
    """
    return _parse(domain, trace)


def all_derivation_spans(
    domain: Domain, trace: Trace, limit: int = 64
) -> list[list[Span]]:
    """Every derivation's spans (bounded), for callers reasoning over all parses."""
    n = len(trace)
    memo: dict[tuple[Task, int], list[tuple[int, tuple[Span, ...]]]] = {}

    def solve(symbol: Task, i: int) -> list[tuple[int, tuple[Span, ...]]]:
        if symbol in domain.primitives:
            return [(i + 1, ())] if (i < n and trace[i] == symbol) else []
        key = (symbol, i)
        if key in memo:
            return memo[key]
        results: list[tuple[int, tuple[Span, ...]]] = []
        for m in domain.methods_for(symbol):
            partials: list[tuple[int, tuple[Span, ...]]] = [(i, ())]
            for sub in m.body:
                nxt = []
                for pos, acc in partials:
                    for end, spans in solve(sub, pos):
                        nxt.append((end, acc + spans))
                partials = nxt
                if not partials:
                    break
            for end, spans in partials:
                results.append((end, spans + (Span(symbol, i, end, m.mid),)))
        memo[key] = results[:limit]
        return memo[key]

    out = []
    for end, spans in solve(domain.initial, 0):
        if end == n:
            out.append(sorted(spans, key=lambda s: (s.start, -(s.end - s.start))))
            if len(out) >= limit:
                break
    return out
