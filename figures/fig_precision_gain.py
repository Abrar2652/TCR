"""F2 (foundational): precision of conformance selection vs the cost-only objective.
Data: results/selector_comparison.json  ->  regime=gold_structural.
Claim: at equal fitness (recall = 1.0), conformance selection reaches precision 1.0
while the cost-only objective's EXPECTED precision over its own min-cost
indifference set falls short (worst case lower still)."""
import json
import os

import figstyle as fs

ORDER = ["linear_control", "branch_suffix", "shared_setup", "finish_suffix", "nested_phase"]
SHORT = {"linear_control": "control", "branch_suffix": "branch", "shared_setup": "shared",
         "finish_suffix": "finish", "nested_phase": "nested"}

rows = json.load(open(os.path.join(fs.RESULTS, "selector_comparison.json")))["selector_comparison"]
d = {r["family"]: r for r in rows if r["regime"] == "gold_structural"}

f, ax = fs.fig(3.3, 2.25)
# conformance ceiling at 1.0 (our method, = gold)
ax.axhline(1.0, color=fs.C_OURS, lw=1.4, zorder=2)
fs.label(ax, 4.5, 1.0, "ours\n= 1.0", color=fs.C_OURS, ha="left", size=7)
for i, fam in enumerate(ORDER):
    r = d[fam]
    exp, worst = r["precision_cost_only_expected"], r["precision_cost_only_worst"]
    if fam == "linear_control":
        ax.scatter([i], [1.0], s=34, color=fs.C_CTRL, zorder=4, **fs.EDGE)
        continue
    ax.plot([i, i], [worst, exp], color=fs.C_BASE, lw=1.4, zorder=3,
            solid_capstyle="round")
    ax.scatter([i], [exp], s=40, color=fs.C_BASE, zorder=4, **fs.EDGE)
    ax.plot([i], [worst], "_", color="black", ms=9, mew=1.5, zorder=5)
# one compact direct label set on the 'branch' family
fs.label(ax, 1.16, d["branch_suffix"]["precision_cost_only_expected"],
         "cost-only\nexpected", color=fs.C_BASE, ha="left", size=6.6, weight="normal")
fs.label(ax, 1.16, d["branch_suffix"]["precision_cost_only_worst"],
         "worst", color="black", ha="left", size=6.6, weight="normal")
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels([SHORT[f] for f in ORDER])
ax.set_ylabel("repair precision  (fitness = 1.0)")
ax.set_ylim(0.925, 1.012)
ax.set_yticks([0.94, 0.96, 0.98, 1.0])
fs.grid_y(ax)
ax.margins(x=0.07)
print(fs.save(f, "fig_precision_gain"))
