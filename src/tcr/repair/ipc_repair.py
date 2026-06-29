"""Multi-insertion target-valid repair enumeration for the real IPC benchmark.

The synthetic study assumed a *single* deleted action; the real benchmark
removes many primitive occurrences across many methods (30% fuzzing). The repair
is therefore a multi-insertion: insert plan terminals into (pruned) method bodies
until the target becomes derivable, minimizing the number of insertions -- exactly
the CFG-repair problem the incumbent (Lutalo & Bercher 2026) solves with an LLM
or with optimal symbolic search.

We enumerate the *minimum-cost* target-valid repairs (and optionally the next
cost level) by breadth-first search over single-terminal insertions, deduplicated
by resulting-domain signature and beam-capped for tractability. The insertion
alphabet is restricted to terminals occurring in the target -- matching the
incumbent's masked prompt, which only exposes target terminals -- because
inserting a non-target terminal into a method on the target's derivation can
never help derive the target.

The point of enumerating the *set* of min-cost repairs (not just one) is to
measure the conformance gap: do equal-cost repairs disagree on which reordered /
action-skipping traces they accept? That disagreement is the precision the
incumbent objective leaves unspecified.
"""
from __future__ import annotations

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, Trace
from tcr.repair.candidates import Repair


def _insertion_candidates(domain: Domain, alphabet: tuple[str, ...]):
    """Yield (action, method_id, position) for every single-terminal insertion."""
    for m in domain.methods:
        n = len(m.body) + 1
        for a in alphabet:
            for pos in range(n):
                yield (a, m.mid, pos)


def menu_candidates(domain: Domain, removed_by_method: dict):
    """Yield (action, method_id, position) restricted to the corruption's own
    removed-action menu: insert a removed action only into the method it was
    removed from, at any position. This is the ground-truth-anchored repair
    space -- finite and small -- whose full union recovers the gold language and
    whose strict subsets expose the precision-vs-cost gap of minimal repair.
    """
    mids = {m.mid: m for m in domain.methods}
    for mid, actions in removed_by_method.items():
        m = mids.get(mid)
        if m is None:
            continue
        for a in sorted(set(actions)):
            for pos in range(len(m.body) + 1):
                yield (a, mid, pos)


def enumerate_min_cost_repairs(
    flawed: Domain,
    target: Trace,
    candidates=None,
    max_cost: int = 12,
    beam: int = 600,
    extra_levels: int = 0,
):
    """Return (repairs, cost): target-valid repairs at the minimum insertion cost
    (plus ``extra_levels`` higher cost levels if asked).

    ``candidates`` is a callable ``domain -> iterable[(action, mid, pos)]`` giving
    the legal single insertions; defaults to insert-any-target-terminal-anywhere.
    Pass ``menu_candidates(...)`` (curried) to restrict to the corruption menu.
    ``flawed`` should already be pruned. Returns ([], None) if none within
    ``max_cost``.
    """
    if candidates is None:
        alphabet = tuple(sorted(set(target)))
        candidates = lambda d: _insertion_candidates(d, alphabet)

    frontier: dict[int, Repair] = {flawed.signature(): Repair(())}
    found: list[Repair] = []
    found_cost: int | None = None

    for cost in range(1, max_cost + 1):
        nxt: dict[int, Repair] = {}
        for r in frontier.values():
            base = r.apply(flawed)
            for (a, mid, pos) in candidates(base):
                ins = r.insertions + ((a, mid, pos),)
                cand = Repair(ins)
                d = cand.apply(flawed)
                sig = d.signature()
                if sig in nxt or sig in frontier:
                    continue
                if accepts(d, target):
                    if found_cost is None:
                        found_cost = cost
                    if cost <= (found_cost + extra_levels):
                        found.append(cand)
                else:
                    nxt[sig] = cand
        if found_cost is not None and cost >= found_cost + extra_levels:
            break
        if len(nxt) > beam:
            nxt = dict(sorted(nxt.items())[:beam])
        frontier = nxt
        if not frontier:
            break
    return found, found_cost


def ground_truth_repair(flawed: Domain, removals_by_method: dict, target: Trace) -> Repair:
    """The exact corruption-reversing repair, restricted to methods present in the
    (pruned) flawed domain. Recovers the gold language on the pruned scope.

    ``removals_by_method`` maps method id -> list of (position, action) to
    re-insert (ascending position).
    """
    mids = {m.mid for m in flawed.methods}
    ins: list[tuple[str, str, int]] = []
    for mid, pairs in removals_by_method.items():
        if mid not in mids:
            continue
        for pos, action in sorted(pairs):
            ins.append((action, mid, pos))
    return Repair(tuple(ins))
