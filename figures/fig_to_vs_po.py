"""CONTRAST schematic (Sec. 4 reversal): why reordering over-acceptance is a
partial-order phenomenon. In a totally-ordered method the body is a sequence, so a
reinsertion picks a *position* and the order of every action is then fixed -- there
is no ordering to omit, hence no reordering gap. In a partial-order method the body
is a set of subtasks plus *separate* precedence constraints; in HDDL those
constraints are cost-free, so a minimum-cost reinsertion may omit them, leaving the
action unordered and admitting many gold-rejected linearizations.
Purely conceptual (no data plotted). Supports: the TO/PO reversal remark and why
CEGIS (Prop 2) is PO-specific.
"""
import os

import matplotlib.patches as mp
from matplotlib.patches import FancyArrowPatch

import figstyle as fs

f, ax = fs.fig(4.7, 2.15)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.axvline(0.5, color="#cccccc", lw=0.8, zorder=1)


def slot(cx, cy, s, ec=fs.C_CTRL, fc="white", w=0.072, h=0.13):
    ax.add_patch(mp.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle="round,pad=0.004,rounding_size=0.012",
                 linewidth=1.2, edgecolor=ec, facecolor=fc, zorder=4))
    ax.text(cx, cy, s, ha="center", va="center", fontsize=8.5, weight="bold",
            family="DejaVu Sans", color="black", zorder=5)


def pnode(cx, cy, s, ec, dashed=False):
    ax.scatter([cx], [cy], s=270, color="white", edgecolor=ec, linewidth=1.3,
               zorder=4, linestyle=(0, (2, 1.4)) if dashed else "solid")
    ax.text(cx, cy, s, ha="center", va="center", fontsize=8.0, weight="bold",
            family="DejaVu Sans", color="black", zorder=5)


def arr(x0, y0, x1, y1, color="black", lw=1.3, dashed=False):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                 mutation_scale=8, lw=lw, color=color, shrinkA=7, shrinkB=7,
                 linestyle=(0, (2, 1.4)) if dashed else "solid", zorder=3))


# -- LEFT: totally-ordered repair -------------------------------------------
fs.label(ax, 0.25, 0.93, "totally-ordered repair", color=fs.C_OURS, size=7.6)
fs.label(ax, 0.25, 0.85, "insert at a position", color="black", size=6.3, weight="normal")
for x, s in [(0.135, "a"), (0.25, "c"), (0.365, "b")]:
    slot(x, 0.55, s, ec=fs.C_PO if s == "c" else fs.C_CTRL)
# the just-inserted action dropping into its slot
ax.add_patch(FancyArrowPatch((0.25, 0.74), (0.25, 0.63), arrowstyle="-|>",
             mutation_scale=8, lw=1.2, color=fs.C_PO, zorder=3))
fs.label(ax, 0.25, 0.345, "→  a c b", color="black", size=7.0)
fs.label(ax, 0.25, 0.25, "1 ordering", color=fs.C_PO, size=7.0)
fs.label(ax, 0.25, 0.09, "order fixed by the slot — nothing\nto omit  →  no reordering gap",
         color="black", size=5.9, weight="normal")

# -- RIGHT: partial-order repair --------------------------------------------
fs.label(ax, 0.75, 0.93, "partial-order repair", color=fs.C_BASE, size=7.6)
fs.label(ax, 0.75, 0.85, "insert as a subtask (+ optional order)", color="black", size=6.0, weight="normal")
pnode(0.68, 0.49, "a", fs.C_CTRL)
pnode(0.82, 0.49, "b", fs.C_CTRL)
arr(0.68, 0.49, 0.82, 0.49, color="black")          # a < b (kept)
pnode(0.75, 0.68, "c", fs.C_BASE, dashed=True)      # reinserted, free
arr(0.75, 0.68, 0.685, 0.515, color=fs.C_BASE, lw=1.0, dashed=True)   # omitted edges
arr(0.75, 0.68, 0.815, 0.515, color=fs.C_BASE, lw=1.0, dashed=True)
fs.label(ax, 0.75, 0.345, "→  { c a b,  a c b,  a b c }", color="black", size=6.8)
fs.label(ax, 0.75, 0.25, "3 orderings", color=fs.C_BASE, size=7.0)
fs.label(ax, 0.75, 0.09, "precedence is cost-free, so a cheap\nrepair omits it  →  reordering gap",
         color="black", size=5.9, weight="normal")

print(fs.save(f, "fig_to_vs_po"))
