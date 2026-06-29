"""Independent, deliberately-naive derivation oracle.

This exists ONLY to validate the fast CYK recognizer in
``tcr.cfg.membership``. It performs a depth-bounded leftmost-derivation search
and is exponential, so it is only ever run on tiny grammars inside tests. The
point is epistemic: the fast path should agree with a method whose correctness
is self-evident.
"""
from __future__ import annotations

from functools import lru_cache

from tcr.core.types import Domain, Trace


def derivable_bruteforce(domain: Domain, trace: Trace, max_steps: int = 40) -> bool:
    target = tuple(trace)
    target_len = len(target)

    @lru_cache(maxsize=None)
    def expand(seq: tuple[str, ...], steps: int) -> bool:
        if steps > max_steps:
            return False
        # count primitives; if already exceeds target length, prune
        prims = tuple(s for s in seq if s in domain.primitives)
        if len(prims) > target_len:
            return False
        idx = next((i for i, s in enumerate(seq) if s in domain.compounds), None)
        if idx is None:
            return tuple(seq) == target
        # the primitive prefix before the first compound must match target prefix
        prefix = [s for s in seq[:idx] if s in domain.primitives]
        if tuple(prefix) != target[: len(prefix)]:
            return False
        for m in domain.methods_for(seq[idx]):
            new_seq = seq[:idx] + m.body + seq[idx + 1 :]
            if expand(new_seq, steps + 1):
                return True
        return False

    return expand((domain.initial,), 0)
