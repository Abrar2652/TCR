# Partial-order HTN: the direction, the de-risk, and the build plan

The TO-HTN study established a strong **over-generalization** diagnosis (minimal-cost
repairs admit ~90% invalid plans of the correct length on real IPC) but showed that
**reordering** over-acceptance is ~0 on TO-HTN — because a TO method body is a rigid
sequence, so inserting an action admits exactly one order. The genuinely large,
structural precision phenomenon lives in **partial-order HTN**, and that is the
direction we are taking. There, the demoted temporal/Allen layer becomes
load-bearing (verification is NP-complete and ordering is first-class).

## Why PO (de-risked, positive)

Controlled brute-force demonstration (`scratchpad/po_derisk.py`, exact linear-
extension membership). A PO method decomposes a task into subtasks with a *partial*
order; the corruption removes an action; a minimal repair re-inserts it but, being
minimal, adds **no ordering constraints**, so the repaired method admits orderings
the gold partial order forbids:

| method width | order density | precision (gold L / repair L) | TO control |
|---|---|---|---|
| 4 | 0.3 | 0.69 | **1.00** |
| 5 | 0.5 | 0.46 | **1.00** |
| 6 | 0.8 | 0.25 | **1.00** |
| 7 | 0.8 | **0.17** | **1.00** |

So reordering over-acceptance is structural and grows with width/order-density in PO,
while it is exactly 0 (precision 1.0) on TO. This is the clean contrast that
motivates the PO paper and makes the temporal machinery necessary rather than
gratuitous.

### Confirmed on GENUINE IPC-2020 partial-order domains (not a proxy)

`experiments/run_po_ipc_overaccept.py` parses the lifted HDDL of the IPC-2020
`partial-order/` track and computes the exact per-method over-acceptance on the
domains' **actual** partial orders (no grounding, no full-domain verifier — the
reordering effect is local to a method). Result (`results/po_ipc_overaccept.json`):

| domain | primitive subtasks | mean local precision | % affected |
|---|---|---|---|
| PCP | 504 | 0.19 | 100% |
| Monroe-Fully-Observable | 85 | 0.35 | 95% |
| Monroe-Partially-Observable | 83 | 0.35 | 95% |
| UM-Translog | 73 | 0.25 | 99% |
| Rover | 14 | 0.27 | 100% |
| Barman-BDI | 11 | 0.25 | 100% |
| Satellite / Transport | 10 / 1 | 0.40 / 0.50 | 100% |
| Woodworking | 3 | 0.28 | 100% |
| **overall (all 9 PO domains)** | **784** | **0.235** | **98.8%** |

(Across the FULL 9-domain PO track — 334 lifted methods. An earlier glob matched
only `<domain>/domain.hddl` and silently dropped Monroe-* and PCP, which use
per-instance `*-domain.hddl` files; `iter_domain_methods` now covers both layouts,
guarded by `tests/test_po_corpus.py`. The minimal unordered repair admits ~4× more
orderings than gold, on ~99% of removable primitives.) The over-acceptance is exactly
"the repair fails to restore gold's ordering on the reinserted action"; methods
whose subtasks are already unordered, or totally ordered, give precision 1.0
(control). Most IPC PO-track methods are *de facto* totally ordered (PO syntax,
total `:ordering`), so the over-acceptance is driven by the PO repair *model*
(cost-free ordering may be omitted), not by gold being locally partial — and it is
*not* a chain-method artifact: on the genuinely partial-order subset (gold itself
has reordering freedom, n=24, both Monroe variants; `po_indifference.json ->
genuine_partial`) the gap is **larger** (cost-only expected 0.49, worst 0.18, gap
0.71 vs 0.59 corpus-wide).

### The constructive method: counter-example-guided conformance repair

`experiments/run_po_cegis.py`, `results/po_cegis.json`. The minimal repair reinserts
a removed action unordered (precision 0.36). A counter-example-guided repair starts
from the unordered repair and, while it admits a gold-rejected linearization, adds
the precedence constraint the counter-example violates:

| | cost-only (worst) | cost-only (fair expected) | **CEGIS conformance repair** |
|---|---|---|---|
| mean precision (all 9 real IPC PO domains, n=775) | 0.23 | 0.55 | **1.00** |
| counter-examples used | — | — | **1.37 (= #missing edges, optimal)** |
| instances reaching precision 1.0 | — | — | **100%** |
| recall (positive plans) | 1.0 | 1.0 | **1.0 (only gold edges added)** |

So CEGIS recovers gold's ordering exactly, at the *minimal* cost (one precedence per
missing edge), preserving recall. **The scientific punchline is the TO-vs-PO
contrast:** counter-example-guided repair did NOT help on TO-HTN (`scratchpad/
cegis_proto.py`: the invalid language is combinatorial, so a finite set of
counter-examples overfits and does not beat blind completion), but on PO-HTN each
counter-example pins a *specific* missing precedence constraint, so CEGIS is exact
and optimal. This is also the first *implemented* positive+negative HTN repair
(Lin & Bercher 2023 = complexity-only; Lin et al. 2025 = classical-only;
Lutalo & Bercher 2026 list multiple invalid plans as future work).

### Full-domain over-acceptance (the per-method effect compounds)

`experiments/run_po_fulldomain.py`, `results/po_fulldomain.json`. Closing the
"need a scalable verifier for a domain-level number" gap *without* one: the
over-acceptance ratio is purely structural, so we sample lifted PO derivations,
build the induced partial order over the primitive leaves, and compute
precision = |linext(gold leaf-poset)| / |linext(repair leaf-poset)| exactly by
subset DP. Control: p_corrupt=0 gives precision exactly 1.0 (no manufactured
over-acceptance). On UM-Translog (mean plan length ≈ 13):

| corruption p | mean full-domain precision | median | % below 0.5 |
|---|---|---|---|
| 0.0 (control) | 1.000 | 1.0 | 0% |
| 0.3 | **0.41** | 0.25 | 65% |
| 0.6 | **0.14** | 0.056 | 92% |

The per-method over-acceptance (≈0.27) **compounds multiplicatively across the
~13-action derivation** to a domain-level 0.41 (p=0.3) and 0.14 (p=0.6, median
~6% valid) — the real-data PO analogue of the TO over-generalization headline,
obtained exactly and without a membership solver.

## Build status

**Done.** `core/po_types.py` (POMethod with order constraints, PODomain) and
`cfg/po_membership.py`: `accepts_po` (backtracking recognizer) + `po_random_plan`
sampler + brute-force oracle. Validated by `tests/test_po_membership.py` (6 hand +
150 differential vs oracle; full suite 401 pass). This is the trusted *small-scale*
verifier — fine for synthetic gadgets, the de-risk, and per-method work.

**The hard part: a SCALABLE exact verifier — attempted three ways.** PO membership
is NP-complete; the backtracker is exponential and does not reach length-15+ real
targets. (1) An SMT (z3) interval encoding: the complete-A-ary-tree layout cannot
represent deep decompositions; a flat-pool/array layout was correct on shallow
cases but did not scale in z3 and had correctness bugs — **removed** rather than
ship wrong answers. (2) An **ASP (clingo) encoding** (`cfg/po_membership_asp.py`):
a clean decomposition-tree encoding with `covers` position-propagation and block-
ordering — **correct (validated 175 cases + `tests/test_po_membership_asp.py`,
including the length-overrun cases the SMT got wrong)** and fast on small/short
instances (Woodworking L=7 in 1.0s), but real length-12+ targets are still too slow
for clingo. **Conclusion: scalable exact PO-HTN membership on real grammars is hard
for all general-purpose tools** (backtracker/z3/clingo) — confirming it needs the
specialised **Schwartz & Wolter (AAAI 2026)** INDU/QCN encoding (`sota_papers/24342-…`,
*polynomial* encoding size, reuses `tcr/temporal/`) or their released tool. The ASP
verifier is the correct, committed reference for small/short instances. INDU caveat:
atomic-network consistency ≠ satisfiability, so completeness needs care.

**Sidestep used for evidence now: the per-method metric** (`experiments/run_po_overaccept.py`,
`results/po_overaccept.json`). The reordering over-acceptance is LOCAL to a method,
so we count linear extensions (subset DP, exact) of gold-method vs unordered-repair-
method across the real IPC method-width distribution — no full-domain verifier
needed. Result: at moderate partial-ordering, minimal-repair local precision ≈
0.39–0.63 with 60–86% of repaired methods affected, domain-concentrated
(Entertainment 0.29, Depots 0.69, Rover 0.60 … vs Blocksworld 0.79); mean repaired-
method width ≈ 3.4. A full domain-level number additionally needs the scalable
verifier or real PO-IPC domains.

## Implementation spec: scalable PO verifier (Schwartz–Wolter, reimplemented)

Read from `sota_papers/24342-…` Algorithms 1–4. Key realization: our validated ASP
verifier (`cfg/po_membership_asp.py`) already implements the *correct* membership
semantics (covers-propagation + block-ordering = "tn_S ⊑ yield(g)"). It is slow only
because it searches an *unbounded* node pool. Their Steps 1–2 fix exactly that by
**bounding occurrences to the solution**, so the highest-leverage build is:

1. **Step 1 — identifier disambiguation (Alg. 1).** For solution trace t, give each
   primitive occurrence a unique id ⟨a⟩_j; for each primitive a, add a dispatcher
   compound c_a, replace a in method bodies with c_a, and add grounding methods
   c_a → ⟨a⟩_j (one per occurrence of a in t). Drop methods producing a primitive
   not in t. (Membership-preserving; Lemma 1.)
2. **Step 2 — occurrence-count duplication (Alg. 2).** Bottom-up #(c) bound per
   compound (depth bound 2·|T_s|·(|C|+1)); duplicate compounds with #(c)>1 into
   c_0 dispatching to copies c_1…c_#(c); drop #(c)=0 compounds. If #(c_I)=0 →
   reject. **This yields a finite, tight set of task-instance "slots" — feed THESE
   exact counts as the node pool to the ASP/SMT encoder instead of a generic
   2n+2|C| pool.** Expected to remove most of clingo's search blow-up.
3. **Step 3 — encoding.** Two routes once Steps 1–2 give bounded slots:
   - **(Pragmatic, lower-risk) tighten the existing ASP encoding** with the exact
     per-occurrence slots + labels, then re-measure scaling. Reuses the validated
     `covers`/block-ordering rules.
   - **(Faithful INDU)** Alg. 4: separator interval S (valid = after S, invalid =
     before S); per-compound temporal-XOR (Def. 7) selecting exactly one of two
     methods; ordering ≺_s → before/meets; **duration constraint (Def. 8)** that
     decouples duration from position via auxiliary D_i (D_i {before=} I_i, D_i
     {meets} D_{i+1}, sequenced to R' with dur=Σ, R' {before=} R). **WARNING:** the
     duration/position decoupling is the subtle part — a naive "parent interval =
     [min,max] of children with length = Σdur" is INCONSISTENT under interleaving
     and is what broke the removed z3-SMT attempt. In a z3 *integer* model, encode
     dur(R)=Σ dur(children) as an explicit integer sum on a SEPARATE duration var,
     NOT as e(R)−s(R), and keep positional containment (during) independent.
   Validate either route against `cfg.po_membership.derivable_po_bruteforce` on the
   150-grammar differential set, then scale-test on real targets.

## Remaining build

2. **PO benchmark.** Either (a) ground IPC-2020 partial-order HTN domains with
   PANDA (`pandaPIengine`, build from GitHub) into the CFG/PO-JSON adapter, or
   (b) construct controlled-PO instances by relaxing the existing TO benchmark's
   method orderings (a tunable order-density knob on real IPC domain structure).
   Start with (b) for speed, add (a) for the camera-ready.

3. **PO repair model.** A repair inserts an action **and** its ordering constraints
   into a method's task network. The incumbent minimal-cost objective inserts the
   action with the fewest constraints → maximal reordering over-acceptance. This is
   the PO analogue of the TO cost-precision tension, but now the gap is large.

4. **Precision metric.** Sample the repaired domain's linearizations at the target
   length; precision = fraction the gold PO domain accepts. The TO escaping-edges
   machinery (`experiments/run_ipc_overgeneralization.py`) transfers directly once a
   PO `accepts` exists; the metrics/selector are order-agnostic.

5. **Method.** Conformance-aware PO repair that restores ordering constraints guided
   by counter-example linearizations (the CEGIS idea, which failed on TO because the
   invalid language was combinatorial, may work on PO where each counter-example
   pins a specific missing precedence constraint — to be tested).

## What carries over unchanged

- Ingestion of the grounded `.sas` (`tcr/data/sas_adapter.py`) — it already parses
  method ordering constraints (currently linearised; keep the raw pairs for PO).
- Pruning (`tcr/repair/prune.py`), masking decode (`tcr/data/masking.py`) for
  auditing any PO LLM repairs.
- The differential-testing discipline and the gold = flawed + reverse(fuzz-ops)
  reconstruction.
