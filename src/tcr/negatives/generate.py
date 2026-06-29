"""Principled, defensible-by-construction negative-trace generation.

The single most attackable methods choice in a conformance-repair paper is
"where do the negative (invalid-reordered) traces come from?". Hand-picked
negatives invite the reviewer charge of cherry-picking. We therefore generate
negatives by three independent, citable regimes and report results under each,
so that any conclusion that survives all three cannot be an artifact of one
generation strategy.

Regime 1 -- GOLD-ORACLE PERMUTATION (``permute_oracle``)
    Enumerate permutations of the target trace; keep those the GOLD domain
    rejects. Labeling is by the uncorrupted domain, exactly the membership-query
    oracle role of the teacher in Angluin's L* and the verifier in CEGIS
    (Solar-Lezama). Defensible because the gold domain *defines* validity; no
    human judgement enters.

Regime 2 -- GUARANTEED-INVALID MUTATION (``mutate_guaranteed``)
    Apply Damerau-Levenshtein edit operations (transposition of adjacent
    actions, deletion, substitution) to the target, then KEEP ONLY mutants the
    gold domain rejects. Transfers Raselimo, Taljaard & Fischer (SLE 2019)
    "guaranteed syntax error" mutation to the action-sequence setting.

Regime 3 -- EDIT-NEIGHBORHOOD SAMPLING (``edit_neighborhood``)
    Sample traces within bounded edit distance of the target over the action
    alphabet, gold-labeled. Standard practice in grammatical-inference
    competition design (Abbadingo / Omphalos style positive+negative samples).

All three return only traces the gold domain rejects, so by construction every
negative is genuinely invalid. The ``origin`` tag on each LabeledTrace records
the regime for per-regime reporting.
"""
from __future__ import annotations

import random
from itertools import permutations

from tcr.cfg.membership import accepts
from tcr.core.types import Domain, LabeledTrace, Task, Trace


def _gold_rejects(gold: Domain, trace: Trace) -> bool:
    return not accepts(gold, trace)


def permute_oracle(
    gold: Domain, target: Trace, max_traces: int = 64
) -> list[LabeledTrace]:
    """Regime 1: gold-rejected permutations of the target trace."""
    out: list[LabeledTrace] = []
    seen: set[Trace] = {tuple(target)}
    for perm in permutations(target):
        p = tuple(perm)
        if p in seen:
            continue
        seen.add(p)
        if _gold_rejects(gold, p):
            out.append(LabeledTrace(p, positive=False, origin="permute_oracle"))
        if len(out) >= max_traces:
            break
    return out


def mutate_guaranteed(
    gold: Domain, target: Trace, rng: random.Random, n: int = 32
) -> list[LabeledTrace]:
    """Regime 2: Damerau-Levenshtein mutants kept only if gold rejects them."""
    out: list[LabeledTrace] = []
    seen: set[Trace] = {tuple(target)}
    attempts = 0
    while len(out) < n and attempts < n * 50:
        attempts += 1
        t = list(target)
        op = rng.choice(["transpose", "delete", "substitute", "duplicate"])
        if len(t) < 2 and op == "transpose":
            op = "duplicate"
        if op == "transpose" and len(t) >= 2:
            i = rng.randrange(len(t) - 1)
            t[i], t[i + 1] = t[i + 1], t[i]
        elif op == "delete" and t:
            del t[rng.randrange(len(t))]
        elif op == "substitute" and t:
            alpha = sorted(set(target))
            i = rng.randrange(len(t))
            t[i] = rng.choice(alpha)
        elif op == "duplicate" and t:
            i = rng.randrange(len(t))
            t.insert(i, t[i])
        cand = tuple(t)
        if cand in seen:
            continue
        seen.add(cand)
        if _gold_rejects(gold, cand):
            out.append(LabeledTrace(cand, positive=False, origin="mutate_guaranteed"))
    return out


def edit_neighborhood(
    gold: Domain,
    target: Trace,
    rng: random.Random,
    radius: int = 2,
    n: int = 32,
) -> list[LabeledTrace]:
    """Regime 3: gold-rejected samples within bounded edit distance of target."""
    alpha = sorted(set(target))
    out: list[LabeledTrace] = []
    seen: set[Trace] = {tuple(target)}
    attempts = 0
    while len(out) < n and attempts < n * 60:
        attempts += 1
        t = list(target)
        for _ in range(rng.randint(1, radius)):
            op = rng.choice(["ins", "del", "sub", "swap"])
            if op == "ins":
                t.insert(rng.randrange(len(t) + 1), rng.choice(alpha))
            elif op == "del" and len(t) > 1:
                del t[rng.randrange(len(t))]
            elif op == "sub" and t:
                t[rng.randrange(len(t))] = rng.choice(alpha)
            elif op == "swap" and len(t) >= 2:
                i = rng.randrange(len(t) - 1)
                t[i], t[i + 1] = t[i + 1], t[i]
        cand = tuple(t)
        if cand in seen:
            continue
        seen.add(cand)
        if _gold_rejects(gold, cand):
            out.append(LabeledTrace(cand, positive=False, origin="edit_neighborhood"))
    return out


def gold_positive_traces(gold: Domain, target: Trace, extra: int = 0) -> list[LabeledTrace]:
    """Positive set: the target plus optional other gold-accepted permutations.

    For totally-ordered domains the target is usually the only accepted
    linearization, so ``extra`` gold-accepted permutations are rare but included
    for completeness (and matter for partially-ordered domains).
    """
    out = [LabeledTrace(tuple(target), positive=True, origin="target")]
    if extra:
        added = 0
        for perm in permutations(target):
            p = tuple(perm)
            if p == tuple(target):
                continue
            if accepts(gold, p):
                out.append(LabeledTrace(p, positive=True, origin="gold_accepts"))
                added += 1
                if added >= extra:
                    break
    return out


def gold_structural(
    gold: Domain, target: Trace, rng: random.Random, n: int = 32, max_len: int = 10
) -> list[LabeledTrace]:
    """Regime 4: negatives drawn from the GOLD language's own structure.

    The cross-branch leak that motivates this whole project produces invalid
    traces that are NOT permutations of the target -- they come from the gold
    domain's *other* derivations with an action misplaced or dropped. Permuting
    the target alone cannot surface them. This regime therefore enumerates,
    EXHAUSTIVELY for these bounded domains, every single-edit (adjacent
    transposition or single-symbol deletion) of every gold-accepted trace, and
    keeps those the gold domain rejects.

    Exhaustive enumeration (rather than random sampling) matters: it makes the
    negative set a deterministic function of the GOLD domain alone, independent
    of any candidate repair. That independence is the reviewer-proofing -- we
    cannot be accused of constructing negatives to trip a particular repair,
    because the negatives are fixed before any repair is considered. This is the
    process-mining precision notion made concrete: traces just outside the
    model's intended language.
    """
    from tcr.cfg.membership import language_sample

    out: list[LabeledTrace] = []
    seen: set[Trace] = {tuple(target)}
    gold_lang = sorted(language_sample(gold, max_len, limit=400))
    for t in gold_lang:
        tl = list(t)
        # all adjacent transpositions
        for i in range(len(tl) - 1):
            cand = tuple(tl[:i] + [tl[i + 1], tl[i]] + tl[i + 2 :])
            if cand not in seen:
                seen.add(cand)
                if _gold_rejects(gold, cand):
                    out.append(LabeledTrace(cand, False, "gold_structural"))
        # all single deletions
        for i in range(len(tl)):
            cand = tuple(tl[:i] + tl[i + 1 :])
            if cand and cand not in seen:
                seen.add(cand)
                if _gold_rejects(gold, cand):
                    out.append(LabeledTrace(cand, False, "gold_structural"))
    # if a cap is requested, keep a deterministic prefix
    return out[:n] if n and len(out) > n else out


REGIMES = ("permute_oracle", "mutate_guaranteed", "edit_neighborhood", "gold_structural")


def generate_negatives(
    gold: Domain, target: Trace, regime: str, seed: int, n: int = 32
) -> list[LabeledTrace]:
    rng = random.Random(seed)
    if regime == "permute_oracle":
        return permute_oracle(gold, target, max_traces=n)
    if regime == "mutate_guaranteed":
        return mutate_guaranteed(gold, target, rng, n=n)
    if regime == "edit_neighborhood":
        return edit_neighborhood(gold, target, rng, n=n)
    if regime == "gold_structural":
        return gold_structural(gold, target, rng, n=n)
    raise ValueError(f"unknown regime {regime!r}; choose from {REGIMES}")
