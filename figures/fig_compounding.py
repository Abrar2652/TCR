"""N5 (novel): per-method over-acceptance COMPOUNDS multiplicatively across a
derivation, so full-domain precision decays geometrically with plan length.
Data: results/po_fulldomain_raw.json (per-derivation length+precision, real PO
sampler) and results/po_fulldomain.json. Claim: a survivable local 0.27 becomes
~1% valid on a 22-action plan; the p=0 control stays exactly at 1.0 (sound)."""
import json
import os
import statistics
from collections import defaultdict

import numpy as np

import figstyle as fs

d = json.load(open(os.path.join(fs.RESULTS, "po_fulldomain_raw.json")))


def by_len(p, minn=15):
    bl = defaultdict(list)
    for n, pr in d[str(p)]:
        bl[n].append(pr)
    Ls = sorted(L for L in bl if len(bl[L]) >= minn)
    med = [statistics.median(bl[L]) for L in Ls]
    lo = [np.percentile(bl[L], 25) for L in Ls]
    hi = [np.percentile(bl[L], 75) for L in Ls]
    return Ls, med, lo, hi


f, ax = fs.fig(3.4, 2.35)
ax.set_yscale("log")
# p=0 control: flat at 1.0
ax.axhline(1.0, color=fs.C_GOLD, lw=1.4, zorder=4)
fs.label(ax, 9.2, 1.0, "p = 0 control = 1.0", color=fs.C_GOLD, ha="left", va="bottom", size=7, dy=0.0)

SERIES = [(0.6, fs.C_PO, "30% of actions\nreinserted\nunordered"),
          (0.3, fs.OKABE["skyblue"], "")]
for p, col, lab in SERIES:
    Ls, med, lo, hi = by_len(p)
    if p == 0.6:
        ax.fill_between(Ls, lo, hi, color=col, alpha=0.18, zorder=2, linewidth=0)
    ln, = ax.plot(Ls, med, "-", color=col, lw=1.6, zorder=5)
    fs.boldline(ln)
    ax.scatter(Ls, med, s=12, color=col, zorder=6, edgecolor="black", linewidth=0.45)

# direct labels on the lines
fs.label(ax, 22.4, by_len(0.3)[1][-1], "p = 0.3", color=fs.OKABE["skyblue"], ha="left", size=7.4)
fs.label(ax, 17.4, 0.0145, "p = 0.6", color=fs.C_PO, ha="left", size=7.4)
# the compounding message
fs.label(ax, 14.0, 0.52, "over-acceptance\ncompounds with length", color="black", size=7, weight="bold")

ax.set_xlabel("plan length  (primitive actions in the derivation)")
ax.set_ylabel("full-domain precision")
ax.set_xlim(8.3, 24.2)
ax.set_xticks([9, 12, 15, 18, 21])
ax.set_ylim(0.006, 1.5)
ax.set_yticks([0.01, 0.03, 0.1, 0.3, 1.0])
ax.set_yticklabels(["0.01", "0.03", "0.1", "0.3", "1.0"])
fs.grid_y(ax, which="major")
print(fs.save(f, "fig_compounding"))
