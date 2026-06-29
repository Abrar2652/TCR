"""N2 (novel, centerpiece): the over-generalization CLIFF.
Data: results/ipc_overgen_openai-o4-mini-high.jsonl, results/...gpt-oss-120b-high.jsonl
Claim: on real IPC, SOTA minimal-cost repairs admit a length-matched plan language
that is mostly INVALID (median ~0.003 valid) -- a cliff from the gold-pruned
control at 1.0 -- and two independent models land on the same floor."""
import json
import os
import statistics

import figstyle as fs

MODELS = [("openai-o4-mini-high", "o4-mini", fs.C_O4),
          ("openai-gpt-oss-120b-high", "gpt-oss-120b", fs.C_OSS)]

f, ax = fs.fig(3.4, 2.3)
# gold-pruned control reference at 1.0
ax.axhline(1.0, color=fs.C_GOLD, lw=1.5, zorder=4)
fs.label(ax, 0.99, 0.945, "gold-pruned control = 1.0", color=fs.C_GOLD,
         ha="right", va="center", size=7)

LABELPOS = {"o4-mini": (0.30, 0.135), "gpt-oss-120b": (0.30, 0.32)}
for key, name, col in MODELS:
    recs = [json.loads(l) for l in open(os.path.join(fs.RESULTS, f"ipc_overgen_{key}.jsonl"))]
    amb = [x["repair_precision"] for x in recs
           if x.get("repair_precision") is not None and x["ambiguous"]]
    amb.sort(reverse=True)
    n = len(amb)
    xs = [(i + 0.5) / n for i in range(n)]
    ax.scatter(xs, amb, s=15, color=col, zorder=5, alpha=0.95,
               edgecolor="black", linewidth=0.5)
    lx, ly = LABELPOS[name]
    fs.label(ax, lx, ly, name, color=col, ha="left", size=7.2)

# the median annotation (both ~0.003)
fs.label(ax, 0.62, 0.11, "median valid\n0.3%", color="black", size=7, weight="bold")
ax.annotate("", xy=(0.55, 0.01), xytext=(0.62, 0.085),
            arrowprops=dict(arrowstyle="-", lw=0.7, color="black"))

ax.set_xlabel("real IPC repair instances  (ranked, ambiguous)")
ax.set_ylabel("fraction of length-$L$ plans valid")
ax.set_ylim(-0.03, 1.06)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xlim(0, 1)
ax.set_xticks([0, 0.5, 1.0])
ax.set_xticklabels(["best", "median", "worst"])
fs.grid_y(ax)
print(fs.save(f, "fig_overgen_cliff"))
