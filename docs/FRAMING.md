# Framing, positioning, and honest limits

This note states, plainly, what the experiments do and do not claim, so a reviewer
sees the boundaries up front. All numbers have confidence intervals in
`results/ci_summary.json` (bootstrap for means, Wilson for proportions).

## What we claim vs. the base paper (coverage positioning)
We do **not** beat Lutalo & Bercher (2026) on coverage; their LLM pipeline already
solves ~145/156 instances and we operate *downstream* of whatever produces
target-valid repairs. Our contribution is a **new evaluation axis** — repair
*precision* (over-acceptance) — on which the entire prior literature, including the
two SOTA LLM repairs we audit, is blind and suboptimal. The honest one-liner:
"we do not solve more instances; we show the solved instances are repaired in a way
that admits mostly-invalid behaviour, and give a repair that fixes that."

## Over-generalization: conditional vs. unconditional (read carefully)
The headline "median $0.3\%$ valid at length $L$" is **conditional on
structurally-ambiguous instances** (86–90% of scored instances, both models). We
report both (`ci_summary.json -> overgen`):
- ambiguous: mean precision **0.10** (o4-mini) / **0.13** (gpt-oss), 95% CI
  $[0.05,0.16]$ / $[0.07,0.19]$; median 0.003;
- unconditional (all scored): mean **0.21** / **0.22**, 95% CI $\approx[0.14,0.30]$;
  ~80% of instances below 0.5.
Non-ambiguous instances admit a single length-$L$ plan and are trivially 1.0 — the
real-data analogue of the synthetic control, not a dilution of the claim.

## The over-accept *rate* is metric-dependent (stated)
Binary over-acceptance is 40% (o4-mini) / 48% (gpt-oss) under the negative-set
metric, higher under the stricter length-matched escaping-edges metric. We use the
**escaping-edges precision** as the primary, length-matched measure and report the
binary rate only as a secondary, consistent (negative-set) cross-model number.

## Sampling soundness (the metric is conservative)
Escaping-edges precision is sampled by random length-$L$ derivation. The
sample-size sensitivity (`ci_summary.json`) shows the estimate is stable and, where
it moves, it **decreases** with more samples (e.g. Rover $0.036\!\to\!0.012$ from
$n{=}100\!\to\!800$): a larger budget only makes the over-acceptance look worse, so
the reported numbers are conservative. The gold-pruned control sits at exactly 1.0
under the identical sampler, ruling out a sampler artifact.

## The synthetic conformance gap is a structural constant (by design)
Every leak gadget has one shared compound and three target-valid single-insertion
repairs, exactly one of which (insert into the shared compound) is conformant, so
the synthetic gap is $2/3$ **by construction** — it is a controlled minimal example,
not a measured magnitude. Gap *magnitude* variation is carried by the real data:
the cost-only indifference set spans precision $0.26$–$1.0$ per repair
(`po_indifference.json`) and the IPC over-generalization spreads from $\sim\!1$ to
$\sim\!0$ (`ipc_overgen_*.jsonl`). What varies across synthetic seeds is the
*precision gain* and the *negative-regime visibility*, which is what we report.

## The TO conformance *selector* is a weak method — and that is the point
Scaling the min-cost selector to more real IPC instances gives **negligible** gains
(mean $\approx\!0.001$, max $0.003$; `ipc_selector_scaled.jsonl`), because the
over-generalization is **inherent to the minimum-cost objective**, not a tie-break
among equal-cost repairs. This is consistent with — and evidence for — the
cost-precision tension (`frontier.json`): precision is bought only by restoring
(nearly) all of the gold structure, not by a better tie-break. The method
contribution is therefore the **diagnosis + the cost-precision theory + the
partial-order CEGIS repair** (which *does* recover gold ordering optimally), not the
TO selector, which we report honestly as a marginal baseline.

## The partial-order benchmark is a faithful, enumerated extension (full corpus)
We extend the IPC-2020 corruption protocol (remove a primitive subtask) to the
**entire** partial-order track — all 9 domains, **334 lifted methods** yielding **775
primitive-removal instances** (Barman-BDI, both Monroe variants, PCP, Rover,
Satellite, Transport, UM-Translog, Woodworking). (Monroe and PCP use per-instance `*-domain.hddl` files; an earlier
glob omitted them — `iter_domain_methods` now collects and de-duplicates methods
across both file layouts, and a regression guard pins the corpus size.) Because
ordering constraints are cost-free in HDDL, the minimum-cost repair is genuinely
*indifferent* among reinsertions that add any subset of gold's precedence edges; we
**enumerate that indifference set exactly** (`run_po_indifference.py`) rather than
assume a single behaviour, and report its expected ($0.55$, 95% CI $[0.54,0.56]$)
and worst-case ($0.23$) precision against conformance ($1.0$); CEGIS recovers $1.0$
on every method with $1.37$ counter-examples on average.

**The gap is not a chain-method artifact.** Most IPC partial-order-track methods are
*de facto* totally ordered — they use the partial-order syntax (`:subtasks` +
`:ordering`) but the listed constraints happen to be a total order — so the
over-acceptance arises because the partial-order repair *model* may omit cost-free
ordering constraints, not because gold is locally partial. To rule out that this is
only a chain-method effect, we isolate the **genuinely partial-order** methods
(gold itself has reordering freedom, $n=24$, both Monroe variants,
`po_indifference.json -> genuine_partial`): there the gap is *larger*, not smaller —
cost-only expected **0.49** (95% CI $[0.44,0.54]$), worst **0.18**, mean gap **0.71**
vs. **0.59** corpus-wide. The phenomenon strengthens on real partial orders.

**Why no grounding.** The over-acceptance is a *method-local* property: it is the
ratio of linear extensions of a method's subtask order, which is identical for
every grounding of that lifted method (grounding only replicates each method across
object tuples, leaving its ordering — and hence the ratio — unchanged). So we
report it at the lifted level, where it is computed *exactly* (subset-DP linear-
extension counting), and a PANDA grounding would reproduce the same per-method
numbers at higher cost. The one thing grounding *would* enable — running an actual
PO planner/repair tool end-to-end on grounded problems — is the genuine remaining
item: we run the **CEGIS recovery algorithm** (which provably reaches gold ordering)
but characterize the cost-only baseline by its enumerated indifference set rather
than by one external planner's output. An end-to-end PO repair *system* is future
work; the structural claim does not depend on it.
