"""Data prep for N5: dump per-derivation (plan length, full-domain precision)
from the real PO derivation sampler, so the compounding-with-length curve is
driven by real samples. Writes results/po_fulldomain_raw.json. Real data only:
reuses the exact sampler from tcr.experiments.run_po_fulldomain."""
import json
import os
import random

from tcr.experiments.run_po_fulldomain import _Build, parse_methods

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "data/ipc2020-domains/partial-order"))
OUT = os.path.normpath(os.path.join(HERE, "..", "results", "po_fulldomain_raw.json"))

DOMAIN = "UM-Translog"
ROOTS = ["transport"]


def collect(p_corrupt, n=4000, max_leaves=22, depth=22):
    actions, by_head = parse_methods(f"{ROOT}/{DOMAIN}/domain.hddl")
    rng = random.Random(0)
    pts = []  # (n_leaves, precision)
    from tcr.experiments.run_po_ipc_overaccept import linext_count
    tries = 0
    while len(pts) < n and tries < n * 40:
        tries += 1
        b = _Build(actions, by_head, rng, p_corrupt, max_leaves)
        leaves = b.derive(rng.choice(ROOTS), depth)
        if leaves is None or b.n < 2:
            continue
        g = linext_count(b.n, frozenset(b.gold_edges))
        r = linext_count(b.n, frozenset(b.rep_edges))
        if r == 0:
            continue
        pts.append((b.n, g / r))
    return pts


if __name__ == "__main__":
    out = {"domain": DOMAIN}
    for p in (0.0, 0.3, 0.6):
        out[f"{p}"] = collect(p)
        print(p, "->", len(out[f"{p}"]), "derivations")
    json.dump(out, open(OUT, "w"))
    print("wrote", OUT)
