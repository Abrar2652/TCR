"""Partial-order HTN data types.

A PO method decomposes a compound into a *task network*: a set of subtasks with a
partial order over them (not a sequence). This is the only structural difference
from the totally-ordered ``core.types`` -- a TO method is the special case whose
order is the identity chain 0<1<...<k-1.

We keep these separate from the TO types so the validated TO stack (Earley
membership, pruning, masking, the whole real-IPC study) is untouched; the PO
study builds on top.
"""
from __future__ import annotations

from dataclasses import dataclass

Task = str


@dataclass(frozen=True)
class POMethod:
    """compound -> partially-ordered task network.

    ``order`` is a frozenset of (i, j) meaning subtask at index i must precede
    subtask at index j (indices into ``subtasks``). The relation need not be
    transitively closed; the verifier treats it as a set of precedence
    constraints. An empty ``subtasks`` is an epsilon method.
    """

    mid: str
    head: Task
    subtasks: tuple[Task, ...]
    order: frozenset[tuple[int, int]] = frozenset()

    @staticmethod
    def total(mid: str, head: Task, body: tuple[Task, ...]) -> "POMethod":
        """A totally-ordered method (identity chain) -- the TO special case."""
        order = frozenset((i, i + 1) for i in range(len(body) - 1))
        return POMethod(mid, head, tuple(body), order)


@dataclass(frozen=True)
class PODomain:
    primitives: frozenset[Task]
    compounds: frozenset[Task]
    methods: tuple[POMethod, ...]
    initial: Task

    def methods_for(self, head: Task) -> tuple[POMethod, ...]:
        return tuple(m for m in self.methods if m.head == head)

    def is_primitive(self, t: Task) -> bool:
        return t in self.primitives
