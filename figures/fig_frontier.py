"""N3 (novel): the cost-precision frontier -- minimal-cost repair sits at the
low-precision corner and precision is bought only by restoring (nearly) all of the
gold structure. Real IPC instances.
Data: results/frontier.json (precision vs insertion cost as gold is restored).
Claim: cost and precision are in fundamental tension; the cost-only objective (and
hence all prior work) optimizes the one axis that leaves precision near its floor."""
import json
import os

import figstyle as fs

data = json.load(open(os.path.join(fs.RESULTS, "frontier.json")))
# keep instances that actually trace a frontier (full > minimal)
frs = [d for d in data if d["full_cost"] > d["minimal_cost"]]
frs.sort(key=lambda d: d["full_cost"] - d["minimal_cost"], reverse=True)
LAB = {"Rover-GTOHP/p02/plan-1": "Rover p02", "Rover-GTOHP/p01/plan-1": "Rover p01",
       "Transport/pfile04/plan-1": "Transport"}
COL = {"Rover-GTOHP/p02/plan-1": fs.OKABE["blue"], "Rover-GTOHP/p01/plan-1": fs.OKABE["skyblue"],
       "Transport/pfile04/plan-1": fs.OKABE["purple"]}

f, ax = fs.fig(3.4, 2.35)
ax.axhline(1.0, color=fs.C_GOLD, lw=0.9, ls=(0, (3, 2)), zorder=2)

for d in frs[:3]:
    pts = sorted(d["points"])
    xs = [c for c, _ in pts]
    ys = [p for _, p in pts]
    col = COL.get(d["path"], fs.OKABE["grey"])
    ln, = ax.plot(xs, ys, "-", color=col, lw=1.5, zorder=4)
    fs.boldline(ln)
    # minimal-cost end (cost-only stops here): vermillion ring
    ax.scatter([xs[0]], [ys[0]], s=46, color=fs.C_BASE, zorder=6, **fs.EDGE)
    # full restoration end: gold/green
    ax.scatter([xs[-1]], [ys[-1]], s=46, color=fs.C_PO, zorder=6, **fs.EDGE)
    fs.label(ax, xs[-1] + 0.4, ys[-1], LAB.get(d["path"], d["path"]), color=col,
             ha="left", size=6.8, weight="normal")

# message annotations
hero = frs[0]
x0, y0 = sorted(hero["points"])[0]
fs.label(ax, x0 + 0.2, y0 - 0.02, "minimal-cost repair\n(cost-only stops here)",
         color=fs.C_BASE, ha="left", va="top", size=6.8, weight="normal")
fs.label(ax, sorted(hero["points"])[-1][0], 1.0, "gold recovery", color=fs.C_PO,
         ha="right", va="bottom", size=6.8, weight="normal", dy=0.015)

ax.set_xlabel("insertion cost  (actions restored toward gold)")
ax.set_ylabel("repair precision")
ax.set_ylim(-0.04, 1.10)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xlim(0, max(d["full_cost"] for d in frs) + 3.5)
fs.grid_y(ax)
print(fs.save(f, "fig_frontier"))
