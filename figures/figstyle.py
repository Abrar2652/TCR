"""Shared typographic + color system for the conformance-aware HTN repair figures.

One serif/sans pairing, one colorblind-safe palette (Okabe-Ito), single-column
width, vector PDF + high-res PNG, black-edged marks. No titles, no chartjunk.
Every figure script imports this; nothing here reads data.

Design choices (Tufte / Wilke):
  * serif (STIX, Times-like, matches an AAAI/NeurIPS body) for axes + tick labels;
    sans (DejaVu Sans) for direct data labels so they pop against the serif frame.
  * Okabe-Ito palette -- colorblind-safe, print-safe, 8 hues + black.
  * single-column width 3.3in; tight aspect ratios that survive a column.
  * top/right spines removed; ticks outward and short; grid only where a value
    must be read off an axis, and then faint.
  * every point/bar/line carries a black edge so marks read as bold.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# -- Okabe-Ito colorblind-safe palette ---------------------------------------
OKABE = {
    "black": "#000000",
    "orange": "#E69F00",
    "skyblue": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "grey": "#999999",
}
# semantic roles used consistently across figures
C_GOLD = OKABE["black"]          # the gold / ideal reference
C_OURS = OKABE["blue"]           # our conformance-aware method
C_BASE = OKABE["vermillion"]     # the cost-only / minimal-cost incumbent
C_CTRL = OKABE["grey"]           # negative control (no gap by construction)
C_O4 = OKABE["blue"]             # o4-mini
C_OSS = OKABE["orange"]          # gpt-oss-120b
C_PO = OKABE["green"]            # partial-order

EDGE = dict(edgecolor="black", linewidth=0.8)   # apply to scatter/bar marks
OUTLINE = [pe.Stroke(linewidth=2.6, foreground="black"), pe.Normal()]  # bold lines

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))
OUTDIR = os.path.join(HERE, "out")


def setup():
    plt.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 400,
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8.5,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "lines.solid_capstyle": "round",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,   # editable/embeddable text in the PDF
        "ps.fonttype": 42,
    })


# single-column AAAI width ~3.3in; provide tight default aspect
def fig(w=3.3, h=2.2):
    setup()
    f, ax = plt.subplots(figsize=(w, h))
    return f, ax


def grid_y(ax, **kw):
    ax.grid(axis="y", color="#cccccc", linewidth=0.5, **kw)


def grid_x(ax, **kw):
    ax.grid(axis="x", color="#cccccc", linewidth=0.5, **kw)


def sans(ax_or_txt):
    """A sans-serif font dict for direct data labels (pops against serif axes)."""
    return dict(family="DejaVu Sans")


def label(ax, x, y, s, color="black", dx=0.0, dy=0.0, ha="center", va="center",
          size=7.5, weight="bold", halo=True):
    """Direct data label in sans, optionally with a white halo for legibility."""
    t = ax.text(x + dx, y + dy, s, color=color, ha=ha, va=va, fontsize=size,
                family="DejaVu Sans", weight=weight, zorder=10)
    if halo:
        t.set_path_effects([pe.withStroke(linewidth=2.0, foreground="white")])
    return t


def boldline(line):
    """Give a Line2D a black outline so it reads as bold (per spec)."""
    line.set_path_effects(OUTLINE)
    return line


def save(fig, name):
    os.makedirs(OUTDIR, exist_ok=True)
    pdf = os.path.join(OUTDIR, name + ".pdf")
    png = os.path.join(OUTDIR, name + ".png")
    fig.savefig(pdf)
    fig.savefig(png)
    plt.close(fig)
    return pdf, png
