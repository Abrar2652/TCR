"""Data prep for N3: the cost-precision frontier of a real IPC repair instance.
Starting from a minimum-cost target-valid repair, greedily restore the removed
actions toward gold and record (insertion cost, length-L precision) at each step.
Real data only (reuses the audited TO pipeline). Writes results/frontier.json."""
import json
import os
import random

from tcr.cfg.membership import accepts
from tcr.core.types import Domain
from tcr.data.sas_adapter import load_instance, parse_fuzz_ops
from tcr.repair.prune import prune_for_plan
from tcr.experiments.run_ipc_overgeneralization import _precision_len

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "data/zenodo_lutalo/socs2024-evaluation/results"))
OUT = os.path.normpath(os.path.join(HERE, "..", "results", "frontier.json"))
PATHS = ["Rover-GTOHP/p01/plan-1","Satellite-GTOHP/p01/plan-2","Blocksworld-GTOHP/p01/plan-2","Transport/pfile04/plan-1","Rover-GTOHP/p02/plan-1"]


def removed_by_method(path):
    d = {}
    for m, i, t in parse_fuzz_ops(f"{ROOT}/{path}/fuzz-ops"):
        d.setdefault(f"m{m}", []).append((i, f"t{t}"))
    return d


def insert(domain, mid, action, pos):
    m = domain.method_by_id(mid)
    nb = m.body[:pos] + (action,) + m.body[pos:]
    from tcr.core.types import Method
    return domain.replace_method(Method(mid, m.head, nb))


def _prec(domain, inst, L):
    p, _, _ = _precision_len(domain, inst.gold, L, seed=1, n=240)
    return p if p is not None else 0.0


def frontier(path):
    inst = load_instance(f"{ROOT}/{path}")
    pf = prune_for_plan(inst.flawed, inst.target)
    L = len(inst.target)
    rbm = removed_by_method(path)
    mids = {m.mid for m in pf.methods}
    cand = []  # gold-restoring insertions in pruned scope
    for mid, lst in rbm.items():
        if mid in mids:
            for pos, act in sorted(lst):
                cand.append((mid, act, min(pos, len(pf.method_by_id(mid).body))))
    # build the fully-restored (gold on pruned scope) domain
    def build(active):
        cur = pf
        for i, (mid, act, pos) in enumerate(cand):
            if active[i]:
                cur = insert(cur, mid, act, pos)
        return cur
    active = [True] * len(cand)
    full = build(active)
    full_cost = len(cand)
    pts = [(full_cost, _prec(full, inst, L))]  # gold end ~ 1.0
    # greedily REMOVE insertions while the target stays derivable -> shrink to minimal
    rng = random.Random(0)
    order = list(range(len(cand)))
    rng.shuffle(order)
    cost = full_cost
    for i in order:
        active[i] = False
        cur = build(active)
        if accepts(cur, inst.target):
            cost -= 1
            pts.append((cost, _prec(cur, inst, L)))
        else:
            active[i] = True  # needed for target-validity; keep it
    pts.sort()
    return dict(path=path, L=L, minimal_cost=pts[0][0], full_cost=full_cost,
                points=pts)


if __name__ == "__main__":
    out = []
    for p in PATHS:
        try:
            out.append(frontier(p))
            print(p, "ok:", out[-1]["minimal_cost"], "->", out[-1]["full_cost"],
                  "prec", round(out[-1]["points"][0][1], 3), "->", round(out[-1]["points"][-1][1], 3))
        except Exception as e:
            print(p, "ERR", type(e).__name__, str(e)[:60])
    json.dump(out, open(OUT, "w"), indent=1)
    print("wrote", OUT)
