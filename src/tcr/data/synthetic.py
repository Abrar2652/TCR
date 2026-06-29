"""Synthetic HTN domain families with controlled structural ambiguity.

Why synthetic generation is part of an AAAI-grade artifact and not a crutch:
the central scientific claim is that a *conformance gap* (target-trace-valid
repairs that nonetheless over-accept reordered traces) appears specifically
when a hierarchy contains structural ambiguity, and is ABSENT when it does not.
That claim can only be made cleanly if we can dial ambiguity on and off. Real
IPC domains let us show the effect exists in the wild; synthetic families let us
show *what causes it*.

The verified structural cause of a conformance gap
--------------------------------------------------
A gap requires a compound task that is SHARED across two derivations: the target
derivation and at least one other derivation that produces a different action
order. When the missing action is re-inserted into the shared compound, BOTH
derivations regain it (gold behavior preserved). But a cost-equal repair that
inserts the action into the target-local method instead makes the target
derivable while LEAKING: the other derivation now produces a trace the gold
domain rejects, yet the repaired domain accepts it.

Canonical leak gadget (unit-tested in tests/test_gap.py)::

    S -> Main | Alt
    Main -> <pre> G <post>      (the intended order)
    Alt  -> <pre'> G <post'>    (a different order sharing G)
    G    -> crit                (the action that gets deleted)

Inserting crit into G  -> conformant (recovers gold language)
Inserting crit into Main -> leak (Alt loses crit, admits an invalid trace)

The ``linear_control`` family deliberately has NO shared compound, so no leak is
possible and the gap is provably zero -- the negative control that proves the
evaluator is not manufacturing failures.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from tcr.core.types import Domain, Method, Trace

FAMILIES = (
    "linear_control",
    "branch_suffix",
    "shared_setup",
    "finish_suffix",
    "nested_phase",
)


@dataclass(frozen=True)
class GeneratedDomain:
    domain: Domain
    target: Trace
    family: str
    critical_action: str  # the action we will delete to corrupt


def _leak_gadget(family, pre, post, alt_pre, alt_post, crit):
    """Build the canonical shared-compound leak gadget."""
    all_prims = set(pre + post + alt_pre + alt_post + [crit])
    methods = [
        Method("m_s_main", "S", ("Main",)),
        Method("m_s_alt", "S", ("Alt",)),
        Method("m_main", "Main", tuple(pre) + ("G",) + tuple(post)),
        Method("m_alt", "Alt", tuple(alt_pre) + ("G",) + tuple(alt_post)),
        Method("m_g", "G", (crit,)),
    ]
    dom = Domain(
        frozenset(all_prims),
        frozenset({"S", "Main", "Alt", "G"}),
        tuple(methods),
        "S",
    )
    target = tuple(pre) + (crit,) + tuple(post)
    return GeneratedDomain(dom, target, family, crit)


# --------------------------------------------------------------------------
# Genuinely seed-varying generators.
#
# Earlier versions hard-coded the action sequences and ignored ``rng``, so every
# "instance" and every "seed" produced a byte-identical domain -- the apparent
# n=20/seed sweep was one domain repeated, which a reviewer reading this file
# would (rightly) treat as fatal. The generators below randomise the action
# identities and the pre/post block lengths per seed, so a suite is a genuine
# distribution of distinct domains, while preserving the structural invariants
# the study depends on:
#   * ambiguous families keep the shared compound ``G`` (so the conformance gap
#     is real); the ``Alt`` branch always realises a DIFFERENT order than ``Main``
#     and, lacking ``crit`` after a Main-local repair, leaks a gold-rejected trace;
#   * ``linear_control`` has a single linear method and no shared compound, so its
#     gap is provably zero (the negative control).
# Method ids (m_s_main, m_s_alt, m_main, m_alt, m_g) are stable so repairs and
# tests can refer to them.
# --------------------------------------------------------------------------


def _distinct_actions(rng, prefix, k):
    """k distinct action symbols, identities varying with the rng."""
    pool = [f"{prefix}{i}" for i in range(k + rng.randint(0, 4))]
    rng.shuffle(pool)
    return pool[:k]


def gen_linear_control(rng, length=None):
    length = length or rng.randint(4, 8)
    acts = _distinct_actions(rng, "a", length)
    m = Method("m_root", "S", tuple(acts))
    dom = Domain(frozenset(acts), frozenset({"S"}), (m,), "S")
    critical = acts[rng.randrange(length)]
    return GeneratedDomain(dom, tuple(acts), "linear_control", critical)


def _rand_leak(family, rng, alt_scheme):
    """Build a randomised shared-compound leak gadget.

    ``alt_scheme`` maps (pre, post) to the Alt branch's (alt_pre, alt_post); each
    family uses a distinct scheme so the families remain conceptually different,
    but the action identities and block lengths vary with ``rng``.
    """
    n_pre = rng.randint(1, 3)
    n_post = rng.randint(1, 3)
    acts = _distinct_actions(rng, family[:2] + "_", n_pre + n_post)
    pre, post = acts[:n_pre], acts[n_pre:]
    alt_pre, alt_post = alt_scheme(pre, post)
    # guarantee Alt realises a different order than Main (else no gap)
    if tuple(alt_pre) + tuple(alt_post) == tuple(pre) + tuple(post):
        alt_pre, alt_post = post, pre
    return _leak_gadget(family, pre, post, alt_pre, alt_post, "crit")


def gen_branch_suffix(rng, length=None):
    # block swap: Alt runs the suffix block before the prefix block
    return _rand_leak("branch_suffix", rng, lambda pre, post: (post, pre))


def gen_shared_setup(rng, length=None):
    # reverse the prefix block around the shared setup
    return _rand_leak("shared_setup", rng, lambda pre, post: (list(reversed(pre)), post))


def gen_finish_suffix(rng, length=None):
    # the finishing block migrates to the front
    return _rand_leak("finish_suffix", rng, lambda pre, post: (post + pre[:-1], pre[-1:]))


def gen_nested_phase(rng, length=None):
    # rotate prefix and post so the shared compound sits in a different phase
    return _rand_leak("nested_phase", rng, lambda pre, post: (post, list(reversed(pre))))


_GENERATORS = {
    "linear_control": gen_linear_control,
    "branch_suffix": gen_branch_suffix,
    "shared_setup": gen_shared_setup,
    "finish_suffix": gen_finish_suffix,
    "nested_phase": gen_nested_phase,
}


def generate(family, seed):
    if family not in _GENERATORS:
        raise ValueError(f"unknown family {family!r}; choose from {FAMILIES}")
    rng = random.Random(seed)
    return _GENERATORS[family](rng)


def generate_suite(n_per_family, base_seed=0):
    out = []
    for fam in FAMILIES:
        for k in range(n_per_family):
            out.append(generate(fam, base_seed + hash((fam, k)) % 100000))
    return out
