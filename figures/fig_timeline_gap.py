"""F3 (foundational): the second (Allen-timeline) verification layer reports the
same gap structure as the first (trace) layer.
Data: results/timeline_conformance.json and results/headline.json (gold_structural).
Claim: an independent temporal layer flags the same ambiguous families and leaves
the control at zero -- two orthogonal axes, both controlled."""
import json
import os

import figstyle as fs

ORDER = ["linear_control", "branch_suffix", "shared_setup", "finish_suffix", "nested_phase"]
SHORT = {"linear_control": "control", "branch_suffix": "branch", "shared_setup": "shared",
         "finish_suffix": "finish", "nested_phase": "nested"}

tl = {r["family"]: r["mean_timeline_gap"]
      for r in json.load(open(os.path.join(fs.RESULTS, "timeline_conformance.json")))["timeline_conformance"]}
tr = {r["family"]: r["mean_conformance_gap"]
      for r in json.load(open(os.path.join(fs.RESULTS, "headline.json")))["experiment_1_conformance_gap"]
      if r["regime"] == "gold_structural"}

f, ax = fs.fig(3.3, 2.15)
w = 0.36
for i, fam in enumerate(ORDER):
    ax.bar(i - w / 2, tr[fam], width=w, color=fs.C_BASE, zorder=3, **fs.EDGE)
    ax.bar(i + w / 2, tl[fam], width=w, color=fs.OKABE["purple"], zorder=3, **fs.EDGE)
# direct legend via labels on the first ambiguous family
fs.label(ax, 1 - w / 2, tr["branch_suffix"] + 0.035, "trace\nlayer", color=fs.C_BASE, size=6.6, weight="normal")
fs.label(ax, 1 + w / 2 + 0.06, tl["branch_suffix"] + 0.035, "timeline\nlayer", color=fs.OKABE["purple"], size=6.6, weight="normal", ha="left")
fs.label(ax, 0, 0.06, "0", color="black", size=7)
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels([SHORT[f] for f in ORDER])
ax.set_ylabel("gap (each layer)")
ax.set_ylim(0, 0.86)
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
fs.grid_y(ax)
ax.margins(x=0.04)
print(fs.save(f, "fig_timeline_gap"))
