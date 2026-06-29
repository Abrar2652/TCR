"""Enumerate candidate repairs: insert the missing action into method bodies.

A *candidate repair* is an atomic correction I[a, m, i]: insert action ``a`` at
position ``i`` in the body of method ``m`` (Lutalo & Bercher 2026). We enumerate
all such single-insertion repairs across all methods and positions, then keep
those that are *target-valid* (make the target plan derivable again).

The key empirical object of this project lives here: typically MORE THAN ONE
distinct repair is target-valid, and those repairs disagree about which
reordered traces they accept. We expose the full set so that
``tcr.metrics.conformance`` can quantify that disagreement (the conformance
gap), and so that ``tcr.repair.selector`` can choose among them.

We restrict to single-action insertions for the controlled study because the
corruption deletes exactly one action; the IPC adapter path supports
multi-insertion via repeated application (see ``enumerate_k``).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, Method, RepairInstance, Task


@dataclass(frozen=True)
class Repair:
    """A sequence of atomic corrections applied to a flawed domain."""

    insertions: tuple[tuple[str, str, int], ...]  # (action, method_id, position)

    def apply(self, domain: Domain) -> Domain:
        d = domain
        # apply in a deterministic order; positions refer to current body, so we
        # apply per-method left-to-right with position bookkeeping
        by_method: dict[str, list[tuple[str, int]]] = {}
        for action, mid, pos in self.insertions:
            by_method.setdefault(mid, []).append((action, pos))
        for mid, ins in by_method.items():
            method = d.method_by_id(mid)
            # apply higher positions first so earlier inserts don't shift them
            for action, pos in sorted(ins, key=lambda x: -x[1]):
                method = method.insert(action, pos)
            d = d.replace_method(method)
        return d

    @property
    def cost(self) -> int:
        return len(self.insertions)


def candidate_single_insertions(domain: Domain, action: Task) -> list[Repair]:
    """All single insertions of ``action`` into any method at any position."""
    out: list[Repair] = []
    for m in domain.methods:
        for pos in range(len(m.body) + 1):
            out.append(Repair(((action, m.mid, pos),)))
    return out


def target_valid_repairs(
    instance: RepairInstance, action: Task | None = None
) -> list[Repair]:
    """Candidate single-insertion repairs that make the target derivable.

    Deduplicated by the *semantic signature* of the resulting domain, so two
    syntactically different insertions that yield the same language-equivalent
    grammar are counted once.
    """
    act = action or instance.deleted_action
    if act is None:
        raise ValueError("no action to insert; pass action= explicitly")
    seen_sigs: set[int] = set()
    repairs: list[Repair] = []
    for cand in candidate_single_insertions(instance.flawed, act):
        repaired = cand.apply(instance.flawed)
        if accepts(repaired, instance.target):
            sig = repaired.signature()
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                repairs.append(cand)
    return repairs


def enumerate_k(
    instance: RepairInstance, action: Task, k: int, beam: int = 200
) -> list[Repair]:
    """Bounded multi-insertion search (for richer corruptions).

    Greedy/beam over up to ``k`` insertions of the same action. Returns
    target-valid repairs found. Used by the adapter path where corruption may
    remove more than one occurrence.
    """
    frontier: list[Repair] = [Repair(())]
    found: list[Repair] = []
    seen: set[int] = set()
    for _ in range(k):
        nxt: list[Repair] = []
        for r in frontier:
            base = r.apply(instance.flawed)
            for cand in candidate_single_insertions(base, action):
                combined = Repair(r.insertions + cand.insertions)
                repaired = combined.apply(instance.flawed)
                sig = repaired.signature()
                if sig in seen:
                    continue
                seen.add(sig)
                if accepts(repaired, instance.target):
                    found.append(combined)
                else:
                    nxt.append(combined)
        frontier = sorted(nxt, key=lambda x: x.cost)[:beam]
        if not frontier:
            break
    return found
