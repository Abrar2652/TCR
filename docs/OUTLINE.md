# Paper skeleton — TCR (AAAI)

Locks the narrative before prose: section plan, the claim → evidence → figure → CI
map, and the main-vs-appendix split. Theory lives in `THEORY.md`; positioning in
`RELATED_WORK.md` + `FRAMING.md`; numbers in `results/*.json`.

## Thesis (one sentence)
Minimal-cost HTN domain repair — which only requires the target plan to become
derivable — is *precision-blind*: among equal-cost repairs, some restore the intended
behavior and others over-accept invalid task orderings, and the objective cannot tell
them apart; we formalize this **conformance gap**, demonstrate it across the full
IPC-2020 benchmark with two state-of-the-art LLM repair pipelines, and give a
**conformance-aware repair** (a precision-maximizing *selector* for totally-ordered
HTN and a counter-example-guided *precedence-recovery* algorithm for partial-order
HTN) that closes it provably and empirically.

## Draft abstract
> Repairing a flawed HTN planning domain is usually framed as making a target plan
> derivable again at minimum edit cost. We show this objective is underspecified
> along a dimension borrowed from process mining — *precision*: distinct minimal-cost
> repairs that all re-admit the target can differ in how much *invalid* behavior they
> newly accept, and the cost objective is indifferent among them. We formalize this
> conformance gap, prove that minimal-cost target-trace repair cannot avoid it
> (and, when ordering edits are costed, actively prefers the worst-precision repair),
> and measure it on the entire IPC-2020 benchmark: two SOTA LLM repair pipelines
> produce repairs that accept a median 0.3% valid behavior on ambiguous instances,
> and on all nine partial-order domains the cost-only repair reaches only 0.55
> expected precision. We close the gap with a conformance-aware repair that selects
> the precision-maximizing minimal repair (TO) and, for partial order, recovers the
> gold precedence via counter-examples — provably optimal (one constraint per missing
> edge) and reaching precision 1.0 on every method. (≈ tighten to 150 words.)

## Section plan

**1. Introduction.** The repair task; the hidden precision dimension (Fig. 1 =
`fig_overview`, the whole thesis at a glance; leak-gadget intuition + `fig_leak_tree`
in §3); contributions: (C1) formalize the
conformance gap + prove precision-blindness; (C2) import process-mining
precision as an HTN repair-quality metric; (C3) a conformance-aware repair — selector
(TO) + CEGIS precedence recovery (PO) with optimality proof; (C4) first *implemented*
HTN positive+negative repair with a conformance evaluation on IPC-2020.

**2. Background.** HTN = CFG (Höller 2014); plan validity = membership. Conformance
recall/fitness vs precision; escaping-edges `etc_P` (Muñoz-Gama & Carmona 2010). The
minimal-cost target-trace repair setting (Lutalo–Bercher 2026; Lin–Höller–Bercher).
Gold's theorem framing (positive-only ⇒ over-generalization).

**3. The conformance gap (theory).** Defs 1–3, Prop 1 (precision-blindness) + Cor 1
(cost-model sharpening: indifferent vs `ORD+`-adversarial). → `THEORY.md §1–2`.

**4. Conformance-aware repair.** TO: precision-maximizing selection over the
cost-minimal set, with the fair-baseline rule (expected + worst over the indifference
set). PO: CEGIS precedence recovery + Prop 2 (optimal, terminating; mechanism in Fig.
`fig_cegis_loop`, a real Monroe method). The TO/PO reversal remark — why a
constructive algorithm exists for PO, only a selector for TO (Fig. `fig_to_vs_po`).
→ `THEORY.md §3`.

**5. Experiments.**
- 5.1 *Controlled study* (synthetic): gap present in every ambiguous family, exactly
  zero in the linear control — the gap is real and the evaluator is not manufacturing
  it. (Compact; details → appendix.)
- 5.2 *Real TO over-generalization* (IPC-2020 / Zenodo, o4-mini + gpt-oss): repairs
  are a median 0.3% valid at length L on ambiguous instances; cost–precision frontier;
  the honest selector-negative (tie-break gains are negligible → the over-acceptance
  is inherent to minimal cost).
- 5.3 *Real PO over-acceptance + CEGIS* (full 9-domain corpus): indifference-set
  expected/worst vs conformance; CEGIS → 1.0 at 1.37 counter-examples; larger gap on
  genuinely partial-order gold.

**6. Related work.** → `RELATED_WORK.md` (concede negative-examples priority to Lin
2023/2025; differentiate on implemented-HTN + process-mining precision +
disambiguation + principled negatives).

**7. Limitations & conclusion.** → `FRAMING.md` (coverage positioning; conditional vs
unconditional; two-LLM audit; end-to-end PO *system* as the one future-work item;
grounding-invariance).

## Claim → evidence → figure → CI map

| # | Claim (main text) | Result file | Figure | CI / pin |
|---|---|---|---|---|
| Fig 1 | overview: min-cost repair is precision-blind; ours restores gold | `po_indifference.json` (annot.) | `fig_overview` | exp 0.55 / worst 0.23 |
| C1 | min-cost repair is precision-blind (gap exists, control = 0) | `headline.json` | `fig_conformance_gap`, `fig_leak_tree` | `test_gap.py`, I2/I3 |
| C1b | the gap is invisible to target-local negatives, visible only under gold-structural | `headline.json` | `fig_invisibility` | — |
| C2 | conformance selection hits precision 1.0 at equal recall | `selector_comparison.json` | `fig_precision_gain` | branch exp 0.96 → 1.0 |
| C3-TO | real SOTA repairs over-generalize (median 0.3% valid, ambiguous) | `ipc_overgen_*.jsonl`, `ci_summary.json` | `fig_overgen_cliff` | amb 0.10/0.13 [CIs]; uncond 0.21/0.22 |
| C3-TO' | over-acceptance is inherent to min-cost, not a tie-break | `ipc_selector_scaled.jsonl`, `frontier.json` | `fig_frontier` | gains ~0.001 |
| C3-PO | cost-only PO repair: expected 0.55 / worst 0.23 vs conf 1.0 | `po_indifference.json` | `fig_cegis` | [0.535,0.558] / [0.215,0.237] |
| C3-PO' | CEGIS recovers gold ordering optimally (1.37 CE) | `po_cegis.json` | `fig_cegis`, `fig_cegis_loop` | 100% reach 1.0 |
| §4 | reordering gap is PO-specific (TO fixes order by position) | schematic | `fig_to_vs_po` | Prop 2 remark |
| C3-PO'' | gap is larger on genuinely partial-order gold | `po_indifference.json` (`genuine_partial`) | `fig_cegis` (highlighted row) | exp 0.49 [0.44,0.54] |
| C4 | over-acceptance compounds along plan length | `po_fulldomain_raw.json` | `fig_compounding` | p=0/0.3/0.6 |
| audit | binary over-accept rate (consistent metric) | `ci_summary.json` | — | 40% [0.32,0.48] / 48% [0.40,0.56] |
| timeline | the temporal layer agrees; both axes controlled | `timeline_conformance.json` | `fig_timeline_gap` | control 0 |

## Scope decisions (my recommendation — confirm before drafting)
1. **Synthetic study → §5.1 compact + appendix.** It is the *controlled* proof the
   gap is real (control = 0); keep one panel in main text (`fig_conformance_gap`),
   move family details + `fig_invisibility` to appendix. Its gap is a structural 2/3
   by design — say so (FRAMING) and let real data carry magnitude.
2. **Temporal/Allen layer → cut from main paper, one-paragraph extension.** It is a
   second axis but dilutes the precision story; `timeline_conformance.json` + I5/I6
   stay as an appendix/extension note unless a reviewer asks.
3. **Two-LLM audit → keep, state plainly.** o4-mini + gpt-oss are the repairs the
   cached benchmark provides; frame as "two SOTA pipelines," not a model study.
4. **Method framing → diagnosis + theory + PO CEGIS is the contribution;** the TO
   selector is reported honestly as a marginal baseline (its real-data gains are
   negligible — that *is* evidence for the cost-precision tension).

## Pre-draft checklist
- [x] Theory formalized (`THEORY.md`: Def 1–3, Prop 1 + Cor 1, Prop 2)
- [x] Full-corpus PO results + regression guard (`test_po_corpus.py`)
- [x] All claims have a result file + CI (table above)
- [x] 9 figures render from real data (`figures/README.md`)
- [ ] Confirm scope decisions 1–4
- [ ] Draft prose §1–7 against this skeleton
- [ ] Camera-ready: re-run `pytest -q` + regenerate `results/` + figures
