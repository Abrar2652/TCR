"""FIGURE 1 (overview schematic): the conformance gap in one glance.

A flawed domain (an action was deleted) plus a target plan admits MANY minimal-cost
repairs that all re-derive the target; the cost-only objective is indifferent among
them, so it may pick one that over-accepts invalid orderings, while the
conformance-aware repair restores exactly the gold behaviour. The right-hand "lens"
glyph shows each repair's accepted language as area -- gold (green) vs the
over-accepted region (vermillion) -- so precision reads as the green fraction. Flow
is conceptual; the precision numbers are the REAL measured cost-only baseline
(expected/worst over the enumerated indifference set) and conformance, from
results/po_indifference.json. Supports: C1 (precision-blindness, Prop 1) + C3.
"""
import json
import os

import matplotlib.patches as mp
from matplotlib.patches import Ellipse, FancyArrowPatch

import figstyle as fs

ind = json.load(open(os.path.join(fs.RESULTS, "po_indifference.json")))
P_EXP = ind["cost_only_expected"]     # 0.55  (fair, ACT+ indifferent)
P_WORST = ind["cost_only_worst"]      # 0.23  (ORD+ cost-minimizer)

f, ax = fs.fig(4.05, 2.3)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

VLIGHT = "#F3D5C4"   # light vermillion fill (over-accepted region)
GLIGHT = "#BFE6D8"   # light green fill (gold)


def box(cx, cy, w, h, ec, lw=1.2, fc="white"):
    ax.add_patch(mp.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle="round,pad=0.006,rounding_size=0.02",
                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3))


def arrow(x0, y0, x1, y1, color="black", lw=1.3):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9,
                 lw=lw, color=color, shrinkA=0, shrinkB=0, zorder=2))


def mono(x, y, s, color="black", size=6.6, ha="center", weight="normal"):
    return ax.text(x, y, s, color=color, ha=ha, va="center", fontsize=size,
                   family="serif", weight=weight, zorder=6)


def lens(cx, cy, over):
    """accepted-language region: green = gold; vermillion halo = over-accepted."""
    if over:
        ax.add_patch(Ellipse((cx, cy), 0.085, 0.20, facecolor=VLIGHT,
                     edgecolor=fs.C_BASE, lw=1.2, zorder=4))
        ax.add_patch(Ellipse((cx, cy - 0.018), 0.044, 0.082, facecolor=GLIGHT,
                     edgecolor=fs.C_PO, lw=1.1, zorder=5))
    else:
        ax.add_patch(Ellipse((cx, cy), 0.085, 0.20, facecolor=GLIGHT,
                     edgecolor=fs.C_PO, lw=1.2, zorder=4))


# -- input: flawed domain + target ------------------------------------------
ICX, ICY, IW, IH = 0.135, 0.5, 0.235, 0.43
box(ICX, ICY, IW, IH, fs.C_CTRL)
fs.label(ax, ICX, ICY + 0.17, "flawed domain", color="black", size=6.9)
mono(ICX, ICY + 0.06, r"gold:  $C \to a\, c\, b$", size=6.6)
mono(ICX - 0.082, ICY - 0.035, r"flawed:  $C \to a$", ha="left", size=6.6)
# the deleted action = an empty dashed slot (no strike-through tangle)
ax.add_patch(mp.FancyBboxPatch((ICX + 0.028, ICY - 0.062), 0.034, 0.052,
             boxstyle="round,pad=0.002,rounding_size=0.008", linewidth=0.9,
             edgecolor=fs.C_BASE, facecolor="white", linestyle=(0, (2, 1.5)), zorder=5))
mono(ICX + 0.086, ICY - 0.035, r"$b$", ha="center", size=6.6)
fs.label(ax, ICX, ICY - 0.135, "(c deleted)", color=fs.C_BASE, size=5.9, weight="normal")
mono(ICX, ICY - 0.305, r"target  $\pi^{*}=a\,c\,b$", size=6.9, weight="bold")

# -- fork --------------------------------------------------------------------
arrow(ICX + IW / 2, ICY, 0.325, ICY, lw=1.3)
ax.plot([0.325, 0.325], [0.25, 0.75], color="black", lw=1.3, zorder=2)
arrow(0.325, 0.75, 0.40, 0.75)
arrow(0.325, 0.25, 0.40, 0.25)
fs.label(ax, 0.378, 0.52, "minimal-cost\nrepairs", color="black", size=5.9, weight="normal")

# -- cost-only repair (top) --------------------------------------------------
TCX, TCY, BW, BH = 0.605, 0.75, 0.40, 0.30
box(TCX, TCY, BW, BH, fs.C_BASE)
fs.label(ax, TCX, TCY + 0.105, "cost-only repair", color=fs.C_BASE, size=6.9)
mono(TCX, TCY + 0.022, r"reinsert $c$ unordered", size=6.3)
mono(TCX, TCY - 0.05, r"accepts $\{\,a c b,\ a b c,\ c a b,\dots\}$", size=6.2)
fs.label(ax, TCX, TCY - 0.115, "re-admits π*  ✓   over-accepts ✗", color="black", size=5.8, weight="normal")

# -- conformance-aware repair (bottom) ---------------------------------------
BCX, BCY = 0.605, 0.25
box(BCX, BCY, BW, BH, fs.C_PO)
fs.label(ax, BCX, BCY + 0.105, "conformance-aware  (ours)", color=fs.C_PO, size=6.9)
mono(BCX, BCY + 0.022, r"reinsert $c$ with $a \prec c \prec b$", size=6.3)
mono(BCX, BCY - 0.05, r"accepts $\{\,a c b\,\}$ = gold", size=6.2)
fs.label(ax, BCX, BCY - 0.115, "re-admits π*  ✓   rejects leaks ✓", color="black", size=5.8, weight="normal")

# -- lens (accepted-language region) + real precision numbers ----------------
arrow(TCX + BW / 2, TCY, 0.852, TCY, lw=1.0)
arrow(BCX + BW / 2, BCY, 0.852, BCY, lw=1.0)
lens(0.905, TCY, over=True)
lens(0.905, BCY, over=False)
fs.label(ax, 0.905, TCY - 0.155, f"{P_WORST:.2f}–{P_EXP:.2f}", color=fs.C_BASE, size=7.0)
fs.label(ax, 0.905, BCY - 0.155, "1.00", color=fs.C_PO, size=7.0)
fs.label(ax, 0.905, 0.5, "precision", color="black", size=6.0, weight="normal")
fs.label(ax, 0.905, 0.45, "= green / total", color="#666666", size=5.2, weight="normal")

f.subplots_adjust(left=0.004, right=0.996, top=0.998, bottom=0.002)
print(fs.save(f, "fig_overview"))
