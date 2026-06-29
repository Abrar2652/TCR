"""F1 (foundational): per-family conformance gap under gold-structural negatives.
Data: results/headline.json  ->  experiment_1_conformance_gap, regime=gold_structural.
Claim: the gap appears in every structurally-ambiguous family and is exactly zero
in the ambiguity-free control (the evaluator is not manufacturing failures)."""
import json
import os

import figstyle as fs

REG = "gold_structural"
ORDER = ["linear_control", "branch_suffix", "shared_setup", "finish_suffix", "nested_phase"]
SHORT = {"linear_control": "control", "branch_suffix": "branch", "shared_setup": "shared",
         "finish_suffix": "finish", "nested_phase": "nested"}

rows = json.load(open(os.path.join(fs.RESULTS, "headline.json")))["experiment_1_conformance_gap"]
gap = {r["family"]: r["mean_conformance_gap"] for r in rows if r["regime"] == REG}

f, ax = fs.fig(3.3, 2.05)
xs = range(len(ORDER))
for i, fam in enumerate(ORDER):
    g = gap[fam]
    is_ctrl = fam == "linear_control"
    ax.bar(i, g, width=0.66, color=(fs.C_CTRL if is_ctrl else fs.C_BASE),
           zorder=3, **fs.EDGE)
    fs.label(ax, i, g + 0.03, f"{g:.2f}", color="black")
# control annotation
fs.label(ax, 0, 0.10, "negative\ncontrol", color=fs.C_CTRL, size=6.8, weight="normal")
ax.set_xticks(list(xs))
ax.set_xticklabels([SHORT[f] for f in ORDER])
ax.set_ylabel("conformance gap")
ax.set_ylim(0, 0.8)
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
fs.grid_y(ax)
ax.margins(x=0.04)
print(fs.save(f, "fig_conformance_gap"))
