"""N1 (novel): the conformance gap is INVISIBLE to target-local negatives and
appears only under gold-structural negatives -- while the control stays at zero.
Data: results/headline.json -> experiment_1_conformance_gap (family x regime).
Claim: whether you see the gap depends entirely on where negatives come from
(the methodological punchline); and the ambiguity-free control never shows one."""
import json
import os

import figstyle as fs

# regimes ordered by distance-from-target (target-local -> gold-structural)
REGS = ["permute_oracle", "mutate_guaranteed", "edit_neighborhood", "gold_structural"]
RLAB = ["permute\ntarget", "mutate\ntarget", "edit\nneighborhood", "gold\nstructure"]
AMB = ["branch_suffix", "shared_setup", "finish_suffix", "nested_phase"]

rows = json.load(open(os.path.join(fs.RESULTS, "headline.json")))["experiment_1_conformance_gap"]
gap = {(r["family"], r["regime"]): r["mean_conformance_gap"] for r in rows}

f, ax = fs.fig(3.4, 2.35)
xs = list(range(len(REGS)))
# ambiguous families: bold rising lines that converge at gold-structural
for fam in AMB:
    ys = [gap[(fam, rg)] for rg in REGS]
    ln, = ax.plot(xs, ys, "-", color=fs.C_BASE, lw=1.5, zorder=4)
    fs.boldline(ln)
    ax.scatter(xs, ys, s=20, color=fs.C_BASE, zorder=5, **fs.EDGE)
# control: flat at zero
yc = [gap[("linear_control", rg)] for rg in REGS]
lnc, = ax.plot(xs, yc, "-", color=fs.C_CTRL, lw=1.3, zorder=3)
ax.scatter(xs, yc, s=18, color=fs.C_CTRL, zorder=4, **fs.EDGE)

# direct labels
fs.label(ax, 3.0, 0.667, "4 ambiguous\nfamilies", color=fs.C_BASE, ha="right", dx=-0.06, size=7.2)
fs.label(ax, 2.92, 0.0, "control = 0", color=fs.C_CTRL, ha="right", size=7, weight="normal")
fs.label(ax, 0.5, 0.40, "invisible to\ntarget-local\nnegatives", color="black", size=7.4, weight="bold")

ax.set_xticks(xs)
ax.set_xticklabels(RLAB)
ax.set_ylabel("conformance gap")
ax.set_xlabel("negatives drawn closer to the gold language  " + r"$\rightarrow$")
ax.set_ylim(-0.03, 0.74)
ax.set_yticks([0, 0.2, 0.4, 0.6])
fs.grid_y(ax)
ax.margins(x=0.04)
print(fs.save(f, "fig_invisibility"))
