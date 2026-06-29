"""Core data types for HTN domains and their context-free-grammar view.

We deliberately keep these structures small, immutable, and hashable. Every
repair in this project is a *diff* over method bodies, so cheap structural
equality and hashing matter for deduplication and for caching membership
queries.

Terminology bridge (Hoeller et al. 2014; Lutalo & Bercher 2026):
    compound task  <->  non-terminal symbol
    primitive task <->  terminal symbol
    method         <->  production rule  (LHS compound -> RHS sequence)
    initial task   <->  start symbol

This module is intentionally free of any algorithmic logic. Parsing,
corruption, repair, and metrics all live in their own modules so that each
concern can be unit-tested and audited in isolation -- a property reviewers
care about when they ask "how do you know your verifier is correct?".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


# A "task" is just a symbol name. We use a thin newtype-style alias so that
# type checkers and readers can tell primitive from compound at call sites,
# even though at runtime both are plain strings.
Task = str  # a task identifier (compound or primitive)


@dataclass(frozen=True)
class Method:
    """A single decomposition method: compound -> ordered sequence of subtasks.

    For totally-ordered HTN the subtasks form a sequence, which is exactly a
    CFG production right-hand side. ``mid`` is a stable identifier so that a
    repair can refer to "insert action a at position i in method m" without
    ambiguity even if two methods share the same head and body.
    """

    mid: str
    head: Task
    body: tuple[Task, ...]

    def with_body(self, body: Iterable[Task]) -> "Method":
        return Method(self.mid, self.head, tuple(body))

    def insert(self, action: Task, position: int) -> "Method":
        """Return a new method with ``action`` inserted at ``position``.

        Position is clamped to ``[0, len(body)]`` so callers cannot create an
        out-of-range body. This mirrors the atomic correction I[a, m, i] in
        Lutalo & Bercher (2026), 0 <= i <= k.
        """
        pos = max(0, min(position, len(self.body)))
        new_body = self.body[:pos] + (action,) + self.body[pos:]
        return Method(self.mid, self.head, new_body)


@dataclass(frozen=True)
class Domain:
    """A totally-ordered HTN domain == a context-free grammar.

    Attributes
    ----------
    primitives : frozenset[Task]
        Terminal symbols (executable actions).
    compounds : frozenset[Task]
        Non-terminal symbols (abstract tasks).
    methods : tuple[Method, ...]
        Production rules. Order is preserved for reproducibility but is not
        semantically meaningful.
    initial : Task
        The start symbol / initial compound task.
    """

    primitives: frozenset[Task]
    compounds: frozenset[Task]
    methods: tuple[Method, ...]
    initial: Task

    # -- convenience views -------------------------------------------------
    def methods_for(self, head: Task) -> tuple[Method, ...]:
        return tuple(m for m in self.methods if m.head == head)

    def method_by_id(self, mid: str) -> Method:
        for m in self.methods:
            if m.mid == mid:
                return m
        raise KeyError(f"no method with id {mid!r}")

    def is_primitive(self, t: Task) -> bool:
        return t in self.primitives

    def replace_method(self, method: Method) -> "Domain":
        """Return a new domain with the method of the same id replaced."""
        new_methods = tuple(
            method if m.mid == method.mid else m for m in self.methods
        )
        return Domain(self.primitives, self.compounds, new_methods, self.initial)

    def with_methods(self, methods: Iterable[Method]) -> "Domain":
        return Domain(self.primitives, self.compounds, tuple(methods), self.initial)

    def signature(self) -> int:
        """Stable hash of the *semantic* content (methods as a set).

        Two domains with the same productions but different method ordering
        share a signature. Used to deduplicate candidate repairs.
        """
        body_set = frozenset((m.head, m.body) for m in self.methods)
        return hash((self.primitives, self.compounds, body_set, self.initial))


# A plan / trace is a sequence of primitive tasks (a string over the terminal
# alphabet in the CFG view).
Trace = tuple[Task, ...]


@dataclass(frozen=True)
class LabeledTrace:
    """A trace together with its ground-truth label under the gold domain.

    ``positive=True`` means the gold (uncorrupted) domain accepts the trace;
    these are the plans a correct repair must keep derivable. ``positive=False``
    means the gold domain rejects the trace; a precision-preserving repair must
    keep rejecting it. The ``origin`` tag records *how* the trace was produced
    (gold-derivation, reorder-mutation, edit-mutation, ...) so that experiments
    can report results per negative-generation regime -- the robustness check
    that defends against the "cherry-picked negatives" objection.
    """

    trace: Trace
    positive: bool
    origin: str = "unspecified"


@dataclass(frozen=True)
class RepairInstance:
    """One repair problem: a flawed domain plus the evaluation material.

    ``gold`` is retained for evaluation only -- the repair algorithms never
    read it. Keeping it on the instance (rather than threading it separately)
    makes the oracle-labeling of negatives auditable and reproducible.
    """

    name: str
    flawed: Domain
    gold: Domain
    target: Trace  # the positive plan that must become derivable
    deleted_action: Task | None = None  # which action the corruption removed
    metadata: Mapping[str, str] = field(default_factory=dict)
