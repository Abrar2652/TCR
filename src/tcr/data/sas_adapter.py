"""Ingest the real IPC-2020 HTN benchmark (PANDA grounded ``.sas`` + fuzzer).

This adapter loads the *actual* benchmark used by Lin, Hoeller & Bercher (SoCS
2024) and Lutalo & Bercher (AAAI 2026): grounded totally-ordered HTN instances
in PANDA ``.sas`` format whose method bodies have had primitive subtasks removed
("fuzzed") with 30% probability. Each instance directory ships:

    out-fuzzed.sas   the FLAWED grounded domain (some primitive subtasks removed)
    plan             the target plan (must become derivable after repair)
    fuzz-ops         the ground-truth corruption log: lines ``rm method[m;i;t]``

The single most important property we exploit for the precision study: the
fuzzer only *deletes* primitive subtask occurrences from method bodies; it never
renames or renumbers tasks. Therefore the FLAWED and the reconstructed GOLD
domain live in the *identical* task-id coordinate system, and a trace (sequence
of primitive task ids) is directly comparable between them. The gold domain is
recovered exactly by re-inserting each removed task ``t`` at its original
list-position ``i`` in method ``m`` (ascending ``i``):

    gold method m body  =  flawed body with every removed (i, t) re-inserted at i

We verified against ``fuzzer.cpp``: the position ``i`` in ``rm method[m;i;t]``
indexes the raw subtask list (the order written in the ``.sas``), and for these
totally-ordered instances the subtask-list order equals the execution order
(orderings are the identity chain 0<1<2<...), so list order == CFG body order.

Coordinates
-----------
    primitive task id k  ->  terminal symbol  "t{k}"
    compound  task id k  ->  non-terminal     "t{k}"
    method block index m ->  method id        "m{m}"   (matches fuzz-ops index)
    initial abstract task ->  start symbol

Nothing here depends on the LLM masking used in the prompts; we work in the
clean grounded coordinate system, which is what makes gold/flawed/repair
comparisons sound.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tcr.core.types import Domain, Method, RepairInstance, Trace


@dataclass(frozen=True)
class SASModel:
    """Minimal parsed view of a grounded TO-HTN ``.sas`` file."""

    task_names: tuple[str, ...]          # id -> name
    is_primitive: tuple[bool, ...]       # id -> True if primitive (terminal)
    initial_task: int                    # start compound id
    # method m -> (decomposed_task_id, ordered list of subtask ids)
    methods: tuple[tuple[int, tuple[int, ...]], ...]

    def name_to_id(self) -> dict[str, int]:
        return {n: i for i, n in enumerate(self.task_names)}


# --------------------------------------------------------------------------
# .sas parsing
# --------------------------------------------------------------------------
def _read_blocks(text: str) -> dict[str, list[str]]:
    """Split a ``.sas`` file into its ``;; <Header>`` sections."""
    blocks: dict[str, list[str]] = {}
    cur = None
    for raw in text.splitlines():
        if raw.startswith(";;"):
            cur = raw[2:].strip()
            blocks[cur] = []
        elif cur is not None:
            blocks[cur].append(raw)
    return blocks


def _nonempty(lines: list[str]) -> list[str]:
    return [ln for ln in lines if ln.strip() != ""]


def parse_sas(path: str | Path) -> SASModel:
    text = Path(path).read_text()
    blocks = _read_blocks(text)

    # ---- Tasks (primitive and abstract) ----
    tkey = next(k for k in blocks if k.startswith("Tasks"))
    tlines = _nonempty(blocks[tkey])
    n_tasks = int(tlines[0])
    names: list[str] = []
    isprim: list[bool] = []
    for ln in tlines[1 : 1 + n_tasks]:
        # format: "<isAbstract> <name>"; name has no spaces (grounded)
        flag, name = ln.split(" ", 1)
        isprim.append(flag == "0")
        names.append(name.strip())
    assert len(names) == n_tasks, f"{path}: expected {n_tasks} tasks, got {len(names)}"

    # ---- Initial Abstract Task ----
    ikey = next(k for k in blocks if k.startswith("Initial Abstract Task"))
    initial = int(_nonempty(blocks[ikey])[0])

    # ---- Methods ----
    mkey = next(k for k in blocks if k.startswith("Methods"))
    mlines = _nonempty(blocks[mkey])
    n_methods = int(mlines[0])
    body_lines = mlines[1:]
    methods: list[tuple[int, tuple[int, ...]]] = []
    p = 0
    for _ in range(n_methods):
        # 4 lines: name, decomposed task, subtasks .. -1, orderings .. -1
        _name = body_lines[p]
        dec = int(body_lines[p + 1])
        subs = [int(x) for x in body_lines[p + 2].split()]
        assert subs[-1] == -1, f"{path}: subtask line not -1 terminated: {subs}"
        subs = subs[:-1]
        ords = [int(x) for x in body_lines[p + 3].split()]
        assert ords[-1] == -1
        ords = ords[:-1]
        ordered = _apply_order(subs, ords)
        methods.append((dec, tuple(ordered)))
        p += 4

    return SASModel(tuple(names), tuple(isprim), initial, tuple(methods))


def _apply_order(subs: list[int], ords: list[int]) -> list[int]:
    """Return subtask *ids* in total-order. ``ords`` is flattened (a b) pairs of
    subtask *positions* with a-before-b. For these TO instances the chain is the
    identity (0<1<2<...) so list order already is execution order; we still apply
    the constraints defensively via a topological sort over positions."""
    n = len(subs)
    if n <= 1:
        return list(subs)
    pairs = [(ords[i], ords[i + 1]) for i in range(0, len(ords), 2)]
    # topological order over positions 0..n-1
    succ: dict[int, set[int]] = {i: set() for i in range(n)}
    indeg = {i: 0 for i in range(n)}
    for a, b in pairs:
        if b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1
    # Kahn, tie-break by smallest position id for determinism
    order: list[int] = []
    avail = sorted(i for i in range(n) if indeg[i] == 0)
    while avail:
        i = avail.pop(0)
        order.append(i)
        for j in sorted(succ[i]):
            indeg[j] -= 1
            if indeg[j] == 0:
                avail.append(j)
        avail.sort()
    if len(order) != n:  # cycle / partial order -> fall back to list order
        return list(subs)
    return [subs[pos] for pos in order]


# --------------------------------------------------------------------------
# fuzz-ops parsing + gold reconstruction
# --------------------------------------------------------------------------
_RM_RE = re.compile(r"rm method\[(\d+);(\d+);(\d+)\]")


def parse_fuzz_ops(path: str | Path) -> list[tuple[int, int, int]]:
    """Return the ground-truth removals as (method_index, position, task_id)."""
    out: list[tuple[int, int, int]] = []
    for m in _RM_RE.finditer(Path(path).read_text()):
        out.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def reconstruct_gold_methods(
    flawed: SASModel, removals: list[tuple[int, int, int]]
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """Re-insert removed primitive subtasks to recover the original method bodies.

    For each method, removed (position, task) pairs are applied in ascending
    position so that earlier insertions do not shift the indices of later ones
    (the positions are in original coordinates).
    """
    by_method: dict[int, list[tuple[int, int]]] = {}
    for m, i, t in removals:
        by_method.setdefault(m, []).append((i, t))
    methods = [list(body) for (_, body) in flawed.methods]
    decs = [dec for (dec, _) in flawed.methods]
    for m, ins in by_method.items():
        body = methods[m]
        for i, t in sorted(ins):  # ascending position
            i = min(i, len(body))
            body.insert(i, t)
        methods[m] = body
    return tuple((decs[m], tuple(methods[m])) for m in range(len(methods)))


# --------------------------------------------------------------------------
# SASModel -> tcr Domain
# --------------------------------------------------------------------------
def _to_domain(
    model: SASModel, methods: tuple[tuple[int, tuple[int, ...]], ...]
) -> Domain:
    primitives = frozenset(
        f"t{i}" for i, p in enumerate(model.is_primitive) if p
    )
    compounds = frozenset(
        f"t{i}" for i, p in enumerate(model.is_primitive) if not p
    )
    meths = tuple(
        Method(f"m{m}", f"t{dec}", tuple(f"t{s}" for s in body))
        for m, (dec, body) in enumerate(methods)
    )
    return Domain(primitives, compounds, meths, f"t{model.initial_task}")


def parse_plan(path: str | Path, model: SASModel) -> Trace:
    name2id = model.name_to_id()
    raw = Path(path).read_text().strip()
    steps = [s.strip() for s in raw.split(";") if s.strip()]
    out: list[str] = []
    for s in steps:
        if s not in name2id:
            raise KeyError(f"plan step {s!r} not a known task in {path}")
        out.append(f"t{name2id[s]}")
    return tuple(out)


def load_instance(inst_dir: str | Path, name: str | None = None) -> RepairInstance:
    """Load one benchmark instance directory into a tcr ``RepairInstance``.

    ``flawed`` = out-fuzzed.sas as-is; ``gold`` = flawed + reversed fuzz-ops.
    ``target`` = the plan, as a terminal-id trace. ``deleted_action`` is left
    None because the real corruption removes *many* actions (see metadata
    ``n_removals``); the multi-deletion repair is handled by the experiment.
    """
    d = Path(inst_dir)
    flawed_model = parse_sas(d / "out-fuzzed.sas")
    removals = parse_fuzz_ops(d / "fuzz-ops")
    gold_methods = reconstruct_gold_methods(flawed_model, removals)

    flawed = _to_domain(flawed_model, flawed_model.methods)
    gold = _to_domain(flawed_model, gold_methods)
    target = parse_plan(d / "plan", flawed_model)

    removed_actions = sorted({f"t{t}" for (_, _, t) in removals})
    return RepairInstance(
        name=name or d.name,
        flawed=flawed,
        gold=gold,
        target=target,
        deleted_action=None,
        metadata={
            "family": d.parent.parent.name if d.parent.parent else "ipc",
            "n_removals": str(len(removals)),
            "n_methods_corrupted": str(len({m for (m, _, _) in removals})),
            "plan_len": str(len(target)),
            "source": str(d),
        },
    )
