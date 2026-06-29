"""N6 (novel, mechanism): WHY the conformance gap exists -- a shared compound and
where the re-inserted action lands.
Source: the _leak_gadget documented in CLAUDE.md / tcr/data/synthetic.py (real
domain structure, drawn schematically; gold language = {a crit b, b crit a}).
Claim: inserting the deleted action into the SHARED compound G recovers the gold
language (conformant); inserting it into the target-local method Main makes the
target derivable but lets the Alt branch leak a gold-rejected trace."""
import matplotlib.patches as mp

import figstyle as fs

fs.setup()
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(3.4, 2.25))


def node(ax, xy, txt, kind="comp", fc="white", fcedge="black", tc="black", r=0.082):
    if kind == "comp":
        p = mp.Circle(xy, r, facecolor=fc, edgecolor=fcedge, lw=1.1, zorder=5)
    else:  # action: rounded square
        p = mp.FancyBboxPatch((xy[0] - r, xy[1] - r * 0.8), 2 * r, 1.6 * r,
                              boxstyle="round,pad=0.012,rounding_size=0.02",
                              facecolor=fc, edgecolor=fcedge, lw=1.1, zorder=5)
    ax.add_patch(p)
    ax.text(xy[0], xy[1], txt, ha="center", va="center", fontsize=7.2,
            family="DejaVu Sans", color=tc, zorder=6,
            weight="bold" if fc != "white" else "normal")


def arrow(ax, a, b, color="black", style="-", lw=1.0, r=0.085):
    import numpy as np
    a, b = np.array(a, float), np.array(b, float)
    v = b - a
    L = np.hypot(*v)
    a2 = a + v / L * r
    b2 = b - v / L * r
    ax.annotate("", xy=b2, xytext=a2,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                linestyle=style, shrinkA=0, shrinkB=0), zorder=3)


def panel(ax, conformant):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")   # so Circle patches render as true circles
    ax.axis("off")
    S = (0.5, 0.90)
    Main = (0.27, 0.66)
    Alt = (0.73, 0.66)
    G = (0.5, 0.40)
    crit = (0.5, 0.15)
    node(ax, S, "S")
    node(ax, Main, "Main")
    node(ax, Alt, "Alt")
    arrow(ax, S, Main)
    arrow(ax, S, Alt)
    if conformant:
        # G is shared by both branches; crit inserted INTO G -> both keep it
        node(ax, G, "G")
        arrow(ax, Main, G)
        arrow(ax, Alt, G)
        node(ax, crit, "crit", kind="act", fc=fs.C_PO, tc="white")
        arrow(ax, G, crit, color=fs.C_PO, lw=1.6)
        ax.text(0.5, -0.02, "a crit b  ✓      b crit a  ✓",
                ha="center", fontsize=7, family="DejaVu Sans", color="black")
        fs.label(ax, 0.5, 1.02, "insert into shared G", color=fs.C_PO, size=7.4)
    else:
        # crit inserted into target-local Main; shared G stays empty -> Alt leaks
        node(ax, (0.27, 0.40), "crit", kind="act", fc=fs.C_BASE, tc="white")
        arrow(ax, Main, (0.27, 0.40), color=fs.C_BASE, lw=1.6)
        # empty shared G under Alt
        node(ax, (0.73, 0.40), "G", fc="white", fcedge=fs.C_BASE, tc=fs.C_BASE)
        arrow(ax, Alt, (0.73, 0.40), color=fs.C_BASE, style=(0, (2, 1.6)))
        ax.text(0.73, 0.40 - 0.13, "∅", ha="center", va="center",
                fontsize=9, color=fs.C_BASE)
        ax.text(0.27, 0.15, "a crit b  ✓", ha="center", fontsize=7,
                family="DejaVu Sans", color="black")
        ax.text(0.73, 0.15, "b a  ✗", ha="center", fontsize=7.4,
                family="DejaVu Sans", color=fs.C_BASE, weight="bold")
        ax.text(0.73, 0.025, "leaked", ha="center", fontsize=6.4,
                family="DejaVu Sans", color=fs.C_BASE)
        fs.label(ax, 0.5, 1.02, "insert into target-local Main", color=fs.C_BASE, size=7.4)


panel(axes[0], True)
panel(axes[1], False)
fig.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.06, wspace=0.06)
print(fs.save(fig, "fig_leak_tree"))
