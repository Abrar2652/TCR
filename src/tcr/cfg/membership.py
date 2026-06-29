"""Exact membership checking for the CFG view of a TO-HTN domain.

A trace ``pi`` is *derivable* in a domain ``D`` iff, viewing D as a CFG with the
initial compound task as start symbol, ``pi`` is in the language L(D). For
totally-ordered HTN this membership test is exactly HTN plan verification and is
decidable in polynomial time (it is in P; Hoeller et al. 2014).

We use a general CYK recognizer that does not require the grammar to be
pre-converted to Chomsky Normal Form by the caller. Instead we:

  1. Eliminate epsilon productions (methods with empty bodies),
  2. Eliminate unit productions (A -> B),
  3. Binarize long right-hand sides,
  4. Run standard CYK.

This is the textbook construction (Hopcroft, Motwani & Ullman). We implement it
ourselves rather than depending on a parser library so that the verifier has no
hidden behavior a reviewer would have to trust -- every accept/reject decision
is traceable to these ~150 lines.

Correctness is pinned down by an independent, exponential-time brute-force
derivation enumerator in ``tests`` (used only on tiny grammars), so the fast CYK
path is differentially tested against a method that is "obviously correct".
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from itertools import product
from typing import Iterable

from tcr.core.types import Domain, Task, Trace

EPSILON = ()  # empty body marker


class _NormalizedGrammar:
    """Grammar in a CYK-ready form: binary + terminal productions, no units."""

    def __init__(self, domain: Domain) -> None:
        self.start = domain.initial
        self.terminals = set(domain.primitives)
        # binary[A] = set of (B, C) with A -> B C ; term[A] = set of terminals a with A -> a
        self.binary: dict[Task, set[tuple[Task, Task]]] = defaultdict(set)
        self.term: dict[Task, set[Task]] = defaultdict(set)
        self.start_derives_epsilon = False
        self._build(domain)

    # -- normalization pipeline -------------------------------------------
    def _build(self, domain: Domain) -> None:
        productions: list[tuple[Task, tuple[Task, ...]]] = [
            (m.head, m.body) for m in domain.methods
        ]
        nullable = self._nullable_symbols(productions, domain)
        self.start_derives_epsilon = self.start in nullable
        productions = self._eliminate_epsilon(productions, nullable)
        productions = self._eliminate_units(productions, domain)
        self._binarize(productions, domain)

    def _nullable_symbols(self, productions, domain) -> set[Task]:
        nullable: set[Task] = set()
        changed = True
        while changed:
            changed = False
            for head, body in productions:
                if head in nullable:
                    continue
                if all(sym in nullable for sym in body):  # includes empty body
                    nullable.add(head)
                    changed = True
        return nullable

    def _eliminate_epsilon(self, productions, nullable):
        out: set[tuple[Task, tuple[Task, ...]]] = set()
        for head, body in productions:
            # generate all versions with any subset of nullable occurrences dropped
            nullable_positions = [i for i, s in enumerate(body) if s in nullable]
            for mask in product([True, False], repeat=len(nullable_positions)):
                drop = {pos for pos, keep in zip(nullable_positions, mask) if not keep}
                new_body = tuple(s for i, s in enumerate(body) if i not in drop)
                if new_body:  # never re-introduce epsilon (handled separately)
                    out.add((head, new_body))
        return list(out)

    def _eliminate_units(self, productions, domain):
        non_unit = [(h, b) for h, b in productions if not (len(b) == 1 and b[0] in domain.compounds)]
        # unit pairs (A, B) meaning A =>* B by unit productions
        unit_pairs: set[tuple[Task, Task]] = {(s, s) for s in domain.compounds}
        changed = True
        direct = [(h, b[0]) for h, b in productions if len(b) == 1 and b[0] in domain.compounds]
        while changed:
            changed = False
            for a, b in list(unit_pairs):
                for h, t in direct:
                    if h == b and (a, t) not in unit_pairs:
                        unit_pairs.add((a, t))
                        changed = True
        out: set[tuple[Task, tuple[Task, ...]]] = set()
        for a, b in unit_pairs:
            for h, body in non_unit:
                if h == b:
                    out.add((a, body))
        return list(out)

    def _binarize(self, productions, domain):
        counter = 0
        # In Chomsky Normal Form, a binary rule's RHS must be two NON-TERMINALS.
        # Any terminal appearing in a body of length >= 2 must be replaced by a
        # dummy non-terminal T_a with the unit-terminal rule T_a -> a. Without
        # this step the CYK table (which only stores non-terminals) can never
        # match a terminal sitting inside a binary rule -- the exact bug the
        # differential test caught on S -> a S.
        term_wrap: dict[Task, Task] = {}

        def wrap(sym: Task) -> Task:
            if sym not in self.terminals:
                return sym
            if sym not in term_wrap:
                w = f"__T_{sym}"
                term_wrap[sym] = w
                self.term[w].add(sym)
            return term_wrap[sym]

        for head, body in productions:
            if len(body) == 1:
                (sym,) = body
                if sym in self.terminals:
                    self.term[head].add(sym)
                # unit prods already eliminated; a single compound shouldn't occur
            elif len(body) == 2:
                self.binary[head].add((wrap(body[0]), wrap(body[1])))
            else:
                # left-decompose A -> X1 X2 ... Xk into binary chain with fresh symbols
                prev = head
                syms = [wrap(s) for s in body]
                while len(syms) > 2:
                    fresh = f"__BIN{counter}"
                    counter += 1
                    self.binary[prev].add((syms[0], fresh))
                    prev = fresh
                    syms = syms[1:]
                self.binary[prev].add((syms[0], syms[1]))


@lru_cache(maxsize=4096)
def _normalize(domain: Domain) -> _NormalizedGrammar:
    return _NormalizedGrammar(domain)


class _EarleyGrammar:
    """Grammar prepared for Earley recognition: productions by head, terminal
    set, and the nullable nonterminals (those deriving the empty string).

    Earley is used instead of CYK because converting a real grounded TO-HTN
    grammar to Chomsky Normal Form requires epsilon elimination that is
    *exponential* in the number of nullable symbols inside a single method body
    (every subset of nullable occurrences spawns a production). Recursive IPC
    domains (e.g. Transport) routinely have many nullable compounds in one body
    and the CNF blowup makes membership intractable. Earley handles epsilon,
    unit productions, and recursion directly in O(n^3 * |G|) with no exponential
    preprocessing, and -- crucially -- is held to the *same* differential test
    against the brute-force oracle, so the trust anchor is unchanged.
    """

    def __init__(self, domain: Domain) -> None:
        self.start = domain.initial
        self.terminals = frozenset(domain.primitives)
        prods: dict[Task, list[tuple[Task, ...]]] = defaultdict(list)
        for m in domain.methods:
            prods[m.head].append(m.body)
        self.prods = prods
        self.nullable = self._nullable(prods)

    @staticmethod
    def _nullable(prods) -> frozenset:
        nullable: set = set()
        changed = True
        while changed:
            changed = False
            for head, bodies in prods.items():
                if head in nullable:
                    continue
                for body in bodies:
                    if all(s in nullable for s in body):  # empty body -> True
                        nullable.add(head)
                        changed = True
                        break
        return frozenset(nullable)


@lru_cache(maxsize=8192)
def _earley(domain: Domain) -> _EarleyGrammar:
    return _EarleyGrammar(domain)


def accepts(domain: Domain, trace: Trace) -> bool:
    """Return True iff ``trace`` is derivable from ``domain.initial``.

    Implemented with an Earley recognizer (Aycock & Horspool nullable handling).
    Empty trace is accepted iff the start symbol is nullable.
    """
    g = _earley(domain)
    # Unknown terminals can never be derived; reject early.
    for sym in trace:
        if sym not in g.terminals:
            return False

    n = len(trace)
    if n == 0:
        return g.start in g.nullable

    prods = g.prods
    terminals = g.terminals
    nullable = g.nullable

    # chart[i] = set of Earley items (head, body, dot, origin); worklist drives
    # processing so items added during a position are also processed.
    charts: list[set] = [set() for _ in range(n + 1)]
    work: list[list] = [[] for _ in range(n + 1)]

    def add(i: int, item) -> None:
        if item not in charts[i]:
            charts[i].add(item)
            work[i].append(item)

    for body in prods.get(g.start, ()):  # seed start productions
        add(0, (g.start, body, 0, 0))

    for i in range(n + 1):
        wl = work[i]
        k = 0
        while k < len(wl):
            head, body, dot, origin = wl[k]
            k += 1
            if dot < len(body):
                sym = body[dot]
                if sym in terminals:
                    if i < n and trace[i] == sym:  # scan
                        add(i + 1, (head, body, dot + 1, origin))
                else:  # predict
                    for b2 in prods.get(sym, ()):
                        add(i, (sym, b2, 0, i))
                    if sym in nullable:  # Aycock-Horspool: skip nullable
                        add(i, (head, body, dot + 1, origin))
            else:  # complete
                for (h2, b2, d2, o2) in list(charts[origin]):
                    if d2 < len(b2) and b2[d2] == head:
                        add(i, (h2, b2, d2 + 1, o2))

    for (head, body, dot, origin) in charts[n]:
        if origin == 0 and dot == len(body) and head == g.start:
            return True
    return False


def language_sample(
    domain: Domain, max_len: int, limit: int = 5000, max_work: int = 50000
) -> set[Trace]:
    """Enumerate (a bounded sample of) traces in L(domain) up to ``max_len``.

    Used for evaluation and for building gold-structural negatives. This is a
    breadth-first leftmost-derivation expansion. Recursive grammars have an
    unbounded sentential-form frontier, so in addition to the ``limit`` on
    finished strings we impose a hard ``max_work`` cap on expansions; the routine
    therefore always terminates and returns whatever sample it gathered. It is
    NOT used inside any repair algorithm or membership decision, so a partial
    sample only affects how many negatives we surface, never soundness.
    """
    import heapq

    results: set[Trace] = set()
    seen: set[tuple[Task, ...]] = set()
    # best-first by sentential-form length: prefer forms closest to all-terminal,
    # so complete strings are found quickly even when the grammar is recursive
    # (a FIFO queue gets stuck expanding a leftmost recursive nonterminal).
    counter = 0
    heap: list = [(1, 0, (domain.initial,))]
    work = 0
    while heap and len(results) < limit and work < max_work:
        work += 1
        _, _, seq = heapq.heappop(heap)
        if seq in seen:
            continue
        seen.add(seq)
        idx = next((i for i, s in enumerate(seq) if s in domain.compounds), None)
        if idx is None:
            if len(seq) <= max_len:
                results.add(tuple(seq))
            continue
        if len([s for s in seq if s in domain.primitives]) > max_len:
            continue  # prune: already too many terminals
        for m in domain.methods_for(seq[idx]):
            new_seq = seq[:idx] + m.body + seq[idx + 1 :]
            if len(new_seq) <= max_len * 3 and new_seq not in seen:
                counter += 1
                heapq.heappush(heap, (len(new_seq), counter, new_seq))
    return results
