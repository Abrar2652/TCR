"""MECHANISM schematic for Prop 2: counter-example-guided precedence recovery,
drawn with intuitive task ICONS so each step reads at a glance.

Real genuinely-partial-order method -- Monroe-Fully-Observable
`m_repair_line_with_tree`: shut_off_power < {clear_tree, remove_wire} < string_wire <
turn_on_power (gold has reordering freedom, |linext|=2; method-precondition
pseudo-subtask omitted for clarity). Deleting `remove_wire` and reinserting it
unordered over-accepts (e.g. removing a wire BEFORE the power is off); two
counter-examples each pin exactly one missing precedence edge, recovering the gold
order -- optimal (Prop 2). Linearization counts and precisions are COMPUTED from the
real order. Supports: C3-PO' (CEGIS optimal, one edge per counter-example).
"""
import math
import os

from matplotlib.patches import FancyArrowPatch, Polygon

import figstyle as fs
from tcr.experiments.run_po_ipc_overaccept import linext_count

# S=0 shut-off, C=1 clear-tree, R=2 remove-wire (deleted), W=3 string-wire, T=4 turn-on
GOLD = frozenset({(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)})   # the diamond
FIXED = frozenset({(0, 1), (1, 3), (3, 4)})                  # edges not touching R
ER = [(0, 2), (2, 3)]                                        # R's gold edges (CEGIS adds these)
GLX = linext_count(5, GOLD)                                  # = 2

STAGES = [(FIXED, "unordered"), (FIXED | {ER[0]}, "after CE 1"), (GOLD, "after CE 2  = gold")]
CE_NOTE = ["counter-ex:\nwire before\npower-off", "counter-ex:\nstring before\nremove"]

POS = {0: (0.0, 0.82), 1: (-0.060, 0.57), 2: (0.060, 0.57), 3: (0.0, 0.33), 4: (0.0, 0.10)}
CX = [0.17, 0.5, 0.83]

f, ax = fs.fig(5.2, 2.7)
ax.set_xlim(0, 1)
ax.set_ylim(-0.32, 1.08)
ax.axis("off")
UX, UY = 0.019, 0.048   # aspect-corrected icon scale (icons render round/upright)


def L(cx, cy, lx, ly):
    return (cx + lx * UX, cy + ly * UY)


def stroke(cx, cy, pts, color, lw=1.2, closed=False, dashed=False):
    P = [L(cx, cy, x, y) for x, y in pts]
    if closed:
        P = P + [P[0]]
    xs, ys = zip(*P)
    ax.plot(xs, ys, color=color, lw=lw, zorder=6, solid_capstyle="round",
            linestyle=(0, (2, 1.3)) if dashed else "solid")


# -- icons (local coords in [-1,1], drawn at node centre) --------------------
def ic_power_off(cx, cy, color):                         # IEC power symbol
    arc = [(0.72 * math.cos(math.radians(t)), 0.72 * math.sin(math.radians(t)))
           for t in range(110, 431, 12)]
    stroke(cx, cy, arc, color, lw=1.2)
    stroke(cx, cy, [(0, 0.15), (0, 0.95)], color, lw=1.3)


def ic_tree(cx, cy, color):
    stroke(cx, cy, [(-0.12, -0.95), (0.12, -0.95), (0.12, -0.45), (-0.12, -0.45)], color, lw=1.1, closed=True)
    stroke(cx, cy, [(-0.75, -0.45), (0.75, -0.45), (0.0, 0.15)], color, lw=1.1, closed=True)
    stroke(cx, cy, [(-0.55, 0.05), (0.55, 0.05), (0.0, 0.92)], color, lw=1.1, closed=True)


def ic_cut_wire(cx, cy, color):                          # wavy wire with a gap = cut
    left = [(-0.95 + 0.77 * i / 20, 0.32 * math.sin((i / 20) * math.pi * 2.2)) for i in range(21)]
    right = [(0.18 + 0.77 * i / 20, 0.32 * math.sin((1 + i / 20) * math.pi * 2.2)) for i in range(21)]
    stroke(cx, cy, left, color, lw=1.4)
    stroke(cx, cy, right, color, lw=1.4)
    stroke(cx, cy, [(-0.20, 0.22), (-0.10, -0.22)], color, lw=1.0)   # cut ends
    stroke(cx, cy, [(0.10, 0.22), (0.20, -0.22)], color, lw=1.0)


def ic_string_wire(cx, cy, color):                       # two poles + a gently sagging wire
    for px in (-0.72, 0.72):
        stroke(cx, cy, [(px, -0.95), (px, 0.7)], color, lw=1.2)        # pole
        stroke(cx, cy, [(px - 0.22, 0.5), (px + 0.22, 0.5)], color, lw=1.1)  # crossarm
    droop = [(-0.72 + 1.44 * i / 24, 0.62 - 0.42 * (1 - ((i / 24) * 2 - 1) ** 2)) for i in range(25)]
    stroke(cx, cy, droop, color, lw=1.2)


def ic_bolt(cx, cy, color):                              # lightning = power on
    pts = [(0.10, 0.95), (-0.42, 0.05), (-0.05, 0.05), (-0.18, -0.95),
           (0.45, 0.10), (0.08, 0.10)]
    ax.add_patch(Polygon([L(cx, cy, x, y) for x, y in pts], closed=True,
                 facecolor=color, edgecolor="black", linewidth=0.7, zorder=6))


ICON = {0: ic_power_off, 1: ic_tree, 2: ic_cut_wire, 3: ic_string_wire, 4: ic_bolt}
NAME = {0: "shut off\npower", 1: "clear\ntree", 2: "remove\nwire", 3: "string\nwire", 4: "turn on\npower"}


def node(cx, i, color, dashed=False):
    x, y = cx + POS[i][0], POS[i][1]
    ax.scatter([x], [y], s=560, color="white", zorder=4, edgecolor=color,
               linewidth=1.4, linestyle=(0, (2, 1.4)) if dashed else "solid")
    ICON[i](x, y, color)
    return x, y


def edge(cx, a, b, color="black", lw=1.4, dashed=False):
    xa, ya = cx + POS[a][0], POS[a][1]
    xb, yb = cx + POS[b][0], POS[b][1]
    ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>",
                 mutation_scale=8, lw=lw, color=color, shrinkA=13, shrinkB=13,
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
        if i == 2:
            node(cx, 2, fs.C_PO if r_fixed else fs.C_BASE, dashed=not r_fixed)
        else:
            node(cx, i, "#555555")
    fs.label(ax, cx, 1.02, title, color="black", size=7.6)
    fs.label(ax, cx, -0.045, f"{lin} orderings", color="black", size=6.6, weight="normal")
    fs.label(ax, cx, -0.105, f"precision {prec:.2f}" + ("  = gold" if prec > 0.999 else ""),
             color=fs.C_PO if prec > 0.999 else fs.C_BASE, size=7.4)

for k, (x0, x1) in enumerate([(0.305, 0.36), (0.635, 0.69)]):
    ax.add_patch(FancyArrowPatch((x0, 0.47), (x1, 0.47), arrowstyle="-|>",
                 mutation_scale=10, lw=1.4, color="black", zorder=4))
    fs.label(ax, (x0 + x1) / 2, 0.565, "pin\n1 edge", color="black", size=5.7, weight="normal")
    fs.label(ax, (x0 + x1) / 2, 0.345, CE_NOTE[k], color=fs.C_BASE, size=5.3, weight="normal")

# legend strip: icon + name, once (no circle, pushed clear of the precision row)
ax.plot([0.04, 0.96], [-0.155, -0.155], color="#dddddd", lw=0.7, zorder=1)
lx0 = 0.085
for i in range(5):
    x = lx0 + i * 0.188
    col = fs.C_BASE if i == 2 else "#555555"
    ICON[i](x, -0.245, col)
    fs.label(ax, x + 0.045, -0.245, NAME[i], color="black", size=5.1, weight="normal", ha="left")

print(fs.save(f, "fig_cegis_loop"))
