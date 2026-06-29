"""Corruption protocol: delete a primitive action from a method body.

This mirrors the benchmark construction of Lin, Hoeller & Bercher (SoCS 2024)
and Lutalo & Bercher (2026): the flawed domain is produced by removing primitive
tasks from method bodies, after which the target plan is no longer derivable.

We expose a *deterministic, single-deletion* corruption (delete one chosen
critical action) for the controlled synthetic study, and a *probabilistic*
corruption (each primitive occurrence removed with probability p) that matches
the 30%-removal protocol of the IPC-derived benchmark for the adapter path.

A corruption is only kept if it is *non-trivial*: the target plan must actually
become non-derivable in the flawed domain. Trivial corruptions (where the plan
is still derivable) are filtered out, exactly as Lutalo & Bercher reduce 167 ->
156 instances. This filtering is enforced here so no downstream code has to.
"""
from __future__ import annotations

import random

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, Method, RepairInstance, Trace
from tcr.data.synthetic import GeneratedDomain


def delete_action_everywhere(domain: Domain, action: str) -> Domain:
    """Remove every occurrence of ``action`` from all method bodies."""
    new_methods = tuple(
        m.with_body(tuple(s for s in m.body if s != action)) for m in domain.methods
    )
    return Domain(domain.primitives, domain.compounds, new_methods, domain.initial)


def corrupt_single(gen: GeneratedDomain) -> RepairInstance | None:
    """Delete the critical action; return an instance iff corruption is non-trivial."""
    flawed = delete_action_everywhere(gen.domain, gen.critical_action)
    if accepts(flawed, gen.target):
        return None  # trivial: plan still derivable, discard
    if not accepts(gen.domain, gen.target):
        return None  # malformed gold (should not happen) -- discard defensively
    name = f"{gen.family}/{gen.critical_action}"
    return RepairInstance(
        name=name,
        flawed=flawed,
        gold=gen.domain,
        target=gen.target,
        deleted_action=gen.critical_action,
        metadata={"family": gen.family},
    )


def corrupt_probabilistic(
    domain: Domain, target: Trace, p: float, rng: random.Random
) -> Domain:
    """Remove each primitive occurrence in each method body with probability p."""
    new_methods = []
    for m in domain.methods:
        kept = tuple(
            s for s in m.body if not (s in domain.primitives and rng.random() < p)
        )
        new_methods.append(Method(m.mid, m.head, kept))
    return Domain(domain.primitives, domain.compounds, tuple(new_methods), domain.initial)


def build_instances(suite: list[GeneratedDomain]) -> list[RepairInstance]:
    out: list[RepairInstance] = []
    for gen in suite:
        inst = corrupt_single(gen)
        if inst is not None:
            out.append(inst)
    return out
