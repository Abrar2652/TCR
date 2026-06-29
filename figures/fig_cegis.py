"""N4 (novel): counter-example-guided conformance repair recovers gold ordering on
partial-order HTN, against the FAIR cost-only baseline (expected over the
enumerated indifference set) -- and there is no gap to close on TO.
Data: results/po_indifference.json (cost-only expected + worst over the indifference
set, per domain + the genuinely-partial-order subset) and results/po_cegis.json
(CEGIS precision + mean counter-examples).
Claim: from the fair cost-only baseline (expected 0.55, worst 0.23 over 775 methods)
CEGIS reaches 1.0 with ~1.4 counter-examples (= #missing precedence edges, optimal);
the gap is even larger on genuinely partial-order gold (expected 0.49); on TO there
is no reordering gap at all."""
import json
import os

import figstyle as fs

full = json.load(open(os.path.join(fs.RESULTS, "po_indifference.json")))
ind = full["per_domain"]
gp = full["genuine_partial"]
ceg = json.load(open(os.path.join(fs.RESULTS, "po_cegis.json")))["per_domain"]
doms = sorted(ind, key=lambda k: ind[k]["cost_only_expected"])

f, ax = fs.fig(3.5, 3.45)
ax.axvline(1.0, color=fs.C_GOLD, lw=1.2, zorder=2)

y = 0
yticks, ylabels = [], []
for dom in doms:
    exp = ind[dom]["cost_only_expected"]
    wor = ind[dom]["cost_only_worst"]
    cx = ceg.get(dom, {}).get("mean_counterexamples")
    ax.plot([exp, 1.0], [y, y], color="black", lw=0.9, zorder=3, alpha=0.45)
    ax.plot([wor, exp], [y, y], color=fs.C_BASE, lw=0.9, zorder=3, alpha=0.35, ls=(0, (1.5, 1.2)))
    ax.scatter([wor], [y], s=18, marker="|", color=fs.C_BASE, zorder=4, linewidth=1.2)
    ax.scatter([exp], [y], s=38, color=fs.C_BASE, zorder=5, **fs.EDGE)
    ax.scatter([1.0], [y], s=38, color=fs.C_PO, zorder=5, **fs.EDGE)
    if cx:
        fs.label(ax, (exp + 1.0) / 2, y + 0.36, f"{cx:.1f} cx", color="black", size=6.0, weight="normal")
    yticks.append(y)
    ylabels.append(f"{dom}  (n={ind[dom]['n']})")
    y += 1

# highlighted row: genuinely partial-order gold (gap is LARGER here)
yg = y + 0.4
ax.plot([gp["cost_only_expected"], 1.0], [yg, yg], color="black", lw=1.1, zorder=3, alpha=0.55)
ax.plot([gp["cost_only_worst"], gp["cost_only_expected"]], [yg, yg], color=fs.C_BASE, lw=1.1, zorder=3, alpha=0.45, ls=(0, (1.5, 1.2)))
ax.scatter([gp["cost_only_worst"]], [yg], s=24, marker="|", color=fs.C_BASE, zorder=4, linewidth=1.4)
ax.scatter([gp["cost_only_expected"]], [yg], s=64, color=fs.C_BASE, zorder=6, linewidth=1.3, edgecolor="black")
ax.scatter([1.0], [yg], s=64, color=fs.C_PO, zorder=6, linewidth=1.3, edgecolor="black")
yticks.append(yg)
ylabels.append(f"genuine PO gold  (n={gp['n_units']})")

# TO row: no reordering gap -> single point at 1.0
yt = yg + 1.7
fs.label(ax, 0.34, (yg + yt) / 2 + 0.05, "gap is larger when gold is itself partial",
         color=fs.C_BASE, size=6.2, weight="normal", ha="center")
ax.scatter([1.0], [yt], s=44, marker="s", color=fs.C_CTRL, zorder=5, **fs.EDGE)
yticks.append(yt)
ylabels.append("TO-HTN  (any)")
fs.label(ax, 0.985, yt, "no reordering gap", color=fs.C_CTRL, ha="right", size=6.6, weight="normal")

# method labels (anchored on lowest-expected domain row)
ex0 = ind[doms[0]]["cost_only_expected"]
wo0 = ind[doms[0]]["cost_only_worst"]
fs.label(ax, ex0, -0.95, "cost-only\nexpected", color=fs.C_BASE, size=6.6, weight="normal")
fs.label(ax, wo0, -0.95, "worst", color=fs.C_BASE, size=6.3, weight="normal")
fs.label(ax, 1.0, -0.95, "CEGIS\n= gold", color=fs.C_PO, size=6.6, weight="normal")

ax.set_yticks(yticks)
ax.set_yticklabels(ylabels)
ax.set_ylim(-1.9, yt + 0.7)
ax.set_xlabel("reordering precision")
ax.set_xlim(0.08, 1.06)
ax.set_xticks([0.2, 0.4, 0.6, 0.8, 1.0])
fs.grid_x(ax)
print(fs.save(f, "fig_cegis"))
