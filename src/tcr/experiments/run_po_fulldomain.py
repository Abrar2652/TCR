"""Full-domain PO over-acceptance on genuine IPC PO domains, WITHOUT a membership
solver. The over-acceptance ratio is purely structural, so we sample derivations
from the lifted PO domain, build the induced partial order over the primitive
leaves, and compute precision = |linext(gold leaf-poset)| / |linext(repair
leaf-poset)| exactly via subset DP. This shows how the per-method over-acceptance
*compounds* across a multi-method derivation.

Corruption model (matches the benchmark): each method instance, with probability
``p_corrupt``, has one primitive subtask reinserted UNORDERED by the minimal
repair -> its ordering edges are dropped from that node. Gold keeps all edges.
"""
from __future__ import annotations

import glob
import random
import re
import statistics
from collections import defaultdict

from tcr.experiments.run_po_cegis import _linexts  # not used; kept for parity
from tcr.experiments.run_po_ipc_overaccept import _blocks, _subblock, linext_count


def parse_methods(path):
    """Return (actions, methods_by_head): head -> list of (sub_names, is_prim, order)."""
    text = open(path).read()
    actions = set(re.findall(r"\(:action\s+([\w-]+)", text))
    by_head = defaultdict(list)
    for m in _blocks(text, ":method"):
        hm = re.search(r":task\s*\(([\w-]+)", m)
        if not hm:
            continue
        head = hm.group(1)
        ordered = ":ordered-subtasks" in m
        sb = _subblock(m, ":ordered-subtasks") or _subblock(m, ":subtasks")
        if sb is None:
            continue
        subs = []
        for st in re.finditer(r"\((task\d+)\s+\(([\w-]+)", sb):
            subs.append((st.group(1), st.group(2)))
        if not subs:
            for st in re.finditer(r"\(([\w-]+)", sb):
                if st.group(1) != "and":
                    subs.append((f"task{len(subs)}", st.group(1)))
        if len(subs) < 1:
            continue
        label_idx = {lab: i for i, (lab, _) in enumerate(subs)}
        if ordered:
            order = {(i, i + 1) for i in range(len(subs) - 1)}
        else:
            ob = _subblock(m, ":ordering")
            order = set()
            for a, b in re.findall(r"\(<\s*([\w-]+)\s+([\w-]+)\)", ob or ""):
                if a in label_idx and b in label_idx:
                    order.add((label_idx[a], label_idx[b]))
        names = tuple(t for _, t in subs)
        is_prim = tuple(t in actions for t in names)
        by_head[head].append((names, is_prim, frozenset(order)))
    return actions, by_head


def _closure(n, edges):
    reach = {i: set() for i in range(n)}
    for a, b in edges:
        reach[a].add(b)
    for k in range(n):
        for i in range(n):
            if k in reach[i]:
                reach[i] |= reach[k]
    return reach


class _Build:
    def __init__(self, actions, by_head, rng, p_corrupt, max_leaves):
        self.actions = actions
        self.by_head = by_head
        self.rng = rng
        self.p = p_corrupt
        self.max_leaves = max_leaves
        self.gold_edges = set()
        self.rep_edges = set()
        self.n = 0  # leaf counter

    def derive(self, task, depth):
        """Return list of leaf indices produced by `task`, or None if it blows up."""
        if task in self.actions:
            idx = self.n
            self.n += 1
            if self.n > self.max_leaves:
                return None
            return [idx]
        ms = self.by_head.get(task)
        if not ms or depth <= 0:
            return None  # cannot decompose / too deep
        # prefer non-recursive-looking methods as depth shrinks: just pick random
        names, is_prim, order = self.rng.choice(ms)
        # corruption: maybe drop one primitive subtask's edges in this instance
        drop_idx = None
        if self.rng.random() < self.p:
            prim_positions = [i for i, pr in enumerate(is_prim) if pr]
            if prim_positions:
                drop_idx = self.rng.choice(prim_positions)
        child_leaves = []
        for sub in names:
            ls = self.derive(sub, depth - 1)
            if ls is None:
                return None
            child_leaves.append(ls)
        k = len(names)
        reach = _closure(k, order)
        for i in range(k):
            for j in reach[i]:
                for u in child_leaves[i]:
                    for v in child_leaves[j]:
                        self.gold_edges.add((u, v))
                        if i != drop_idx and j != drop_idx:
                            self.rep_edges.add((u, v))
        return [x for ls in child_leaves for x in ls]


def sample_precision(actions, by_head, root, p_corrupt, rng, max_leaves=15, depth=14):
    b = _Build(actions, by_head, rng, p_corrupt, max_leaves)
    leaves = b.derive(root, depth)
    if leaves is None or b.n < 2:
        return None
    n = b.n
    g = linext_count(n, frozenset(b.gold_edges))
    r = linext_count(n, frozenset(b.rep_edges))
    if r == 0:
        return None
    return g / r, n


def run(po_root, roots_by_domain, p_corrupt=0.3, n_samples=400):
    rep = {"p_corrupt": p_corrupt, "per_domain": {}}
    for f in sorted(glob.glob(f"{po_root}/*/domain.hddl")):
        dom = f.split("/")[-2]
        if dom not in roots_by_domain:
            continue
        actions, by_head = parse_methods(f)
        precs = []
        sizes = []
        rng = random.Random(0)
        tries = 0
        while len(precs) < n_samples and tries < n_samples * 40:
            tries += 1
            root = rng.choice(roots_by_domain[dom])
            out = sample_precision(actions, by_head, root, p_corrupt, rng)
            if out is not None:
                precs.append(out[0])
                sizes.append(out[1])
        if precs:
            rep["per_domain"][dom] = {
                "n_derivations": len(precs),
                "mean_fulldomain_precision": round(statistics.mean(precs), 4),
                "median": round(statistics.median(precs), 4),
                "frac_below_0.5": round(sum(p < 0.5 for p in precs) / len(precs), 4),
                "mean_plan_length": round(statistics.mean(sizes), 1),
            }
    return rep


if __name__ == "__main__":
    import json

    roots = {
        "UM-Translog": ["transport"],
        "Satellite": ["do_mission", "do_turn", "activate_target"],
        "Woodworking": ["do-grind", "process"],
    }
    out = {}
    for p in (0.3, 0.6):
        out[str(p)] = run("data/ipc2020-domains/partial-order", roots, p_corrupt=p)
    json.dump(out, open("results/po_fulldomain.json", "w"), indent=2)
    print(json.dumps(out, indent=2))
