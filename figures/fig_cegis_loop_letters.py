"""PREVIOUS (lettered-node) variant of the CEGIS mechanism schematic, kept for
comparison against the iconified fig_cegis_loop.py. Same real Monroe method
(m_repair_line_with_tree); nodes are lettered S/C/R/W/T with a legend. Counts and
precisions are computed from the real gold order.
"""
import os

from matplotlib.patches import FancyArrowPatch

import figstyle as fs
from tcr.experiments.run_po_ipc_overaccept import linext_count

LET = ["S", "C", "R", "W", "T"]
GOLD = frozenset({(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)})
FIXED = frozenset({(0, 1), (1, 3), (3, 4)})
ER = [(0, 2), (2, 3)]
GLX = linext_count(5, GOLD)

STAGES = [(FIXED, "unordered"), (FIXED | {ER[0]}, "after CE 1"), (GOLD, "after CE 2  = gold")]
CE_NOTE = ["counter-ex:\nR before S", "counter-ex:\nW before R"]

POS = {0: (0.0, 0.82), 1: (-0.052, 0.58), 2: (0.052, 0.58), 3: (0.0, 0.34), 4: (0.0, 0.10)}
CX = [0.17, 0.5, 0.83]

f, ax = fs.fig(5.0, 2.25)
ax.set_xlim(0, 1)
ax.set_ylim(-0.12, 1.05)
ax.axis("off")


def node(cx, i, color, dashed=False):
    x, y = cx + POS[i][0], POS[i][1]
    ax.scatter([x], [y], s=300, color=color, zorder=5, edgecolor="black",
               linewidth=1.1, linestyle=(0, (2, 1.4)) if dashed else "solid")
    ax.text(x, y, LET[i], ha="center", va="center", color="white",
            fontsize=8.5, weight="bold", family="DejaVu Sans", zorder=6)


def edge(cx, a, b, color="black", lw=1.3, dashed=False):
    xa, ya = cx + POS[a][0], POS[a][1]
    xb, yb = cx + POS[b][0], POS[b][1]
    ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>",
                 mutation_scale=8, lw=lw, color=color, shrinkA=8.5, shrinkB=8.5,
                 linestyle=(0, (2, 1.4)) if dashed else "solid", zorder=3))


for s, (edges, title) in enumerate(STAGES):
    cx = CX[s]
    lin = linext_count(5, frozenset(edges))
    prec = GLX / lin
    r_fixed = (0, 2) in edges and (2, 3) in edges
    for (a, b) in edges:
        edge(cx, a, b, color="black")
    for e in ER:
        if e not in edges:
            edge(cx, e[0], e[1], color=fs.C_BASE, lw=1.0, dashed=True)
    for i in range(5):
        node(cx, i, (fs.C_PO if r_fixed else fs.C_BASE) if i == 2 else fs.C_CTRL,
             dashed=(i == 2 and not r_fixed))
    fs.label(ax, cx, 1.0, title, color="black", size=7.4)
    fs.label(ax, cx, -0.03, f"{lin} orderings", color="black", size=6.6, weight="normal")
    fs.label(ax, cx, -0.085, f"precision {prec:.2f}" + ("  = gold" if prec > 0.999 else ""),
             color=fs.C_PO if prec > 0.999 else fs.C_BASE, size=7.2)

for k, (x0, x1) in enumerate([(0.305, 0.36), (0.635, 0.69)]):
    ax.add_patch(FancyArrowPatch((x0, 0.50), (x1, 0.50), arrowstyle="-|>",
                 mutation_scale=10, lw=1.4, color="black", zorder=4))
    fs.label(ax, (x0 + x1) / 2, 0.585, "pin\n1 edge", color="black", size=5.6, weight="normal")
    fs.label(ax, (x0 + x1) / 2, 0.37, CE_NOTE[k], color=fs.C_BASE, size=5.5, weight="normal")

fs.label(ax, 0.5, -0.165,
         "S shut-off   C clear-tree   R remove-wire (deleted)   W string-wire   T turn-on"
         "    —  Monroe m_repair_line_with_tree",
         color="black", size=5.9, weight="normal")

print(fs.save(f, "fig_cegis_loop_letters"))
