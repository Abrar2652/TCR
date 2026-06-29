# Formal theory: the conformance gap and its closure

This note states the theory the paper rests on as definitions + propositions +
proofs, replacing the informal "we observe a gap" with "the cost-only objective is
provably precision-blind, and our repair provably closes it." Every claim is tied
to the result file / figure that instantiates it. Notation is kept light; the HTN =
CFG equivalence (Höller et al. 2014) is assumed throughout.

---

## 1. Definitions

**Def 1 (domain, accepted language).** A totally-ordered HTN domain `D` is a CFG;
its *accepted language* `L(D) ⊆ Σ*` is the set of primitive-action sequences (plans)
derivable from the initial task. Plan validity is membership, `π ∈ L(D)` (decided
by `cfg/membership.py`, the differentially-tested trust anchor). A partial-order
method with subtask set `T` and precedence relation (strict partial order) `O ⊆ T×T`
*accepts* a linearization `ℓ` iff `ℓ` is a linear extension of `O`; write `linext(O)`
for the set of linear extensions and `|linext(O)|` for its (exact, subset-DP) count.

**Def 2 (repair, cost, recall).** A flawed domain `D⁻` is the gold domain `G` with
one primitive subtask deleted from some method bodies. A *repair* `R` re-inserts
primitive subtasks (and, in the PO setting, optionally adds precedence constraints),
yielding `D_R`. The *cost* `c(R)` is the number of subtask insertions (the
Lutalo–Bercher / `ACT+` cost model; the `ORD+` variant is treated in the Corollary).
`R` is **target-valid** if the given target plan `π* ∈ L(D_R)`, and
**recall-preserving** if `L(G) ⊆ L(D_R)` (every gold plan stays derivable).

**Def 3 (conformance precision).** For a repair `D_R` evaluated against gold `G`,

> `prec(D_R) = ` fraction of `D_R`'s accepted behavior that is also gold-valid,

operationalized two ways, both = 1 **iff** `L(D_R) ⊆ L(G)` (no over-acceptance):
- **TO (sampled):** escaping-edges precision `etc_P` (Muñoz-Gama & Carmona 2010) over
  length-matched derivations; the gold-pruned control gives `etc_P = 1` exactly.
- **PO (exact, method-local):** `prec = |linext(O)| / |linext(C)|` where `C` is the
  repaired method's precedence relation; `= 1` iff `linext(C) = linext(O)`.

Target-trace repair optimizes **recall only** (Def 2: it requires `π* ∈ L(D_R)` and
nothing about `L(D_R) \ L(G)`). This is a positive-data-only identification problem;
by Gold's theorem (1967) such objectives are prone to over-generalization — the
theoretical seed of everything below.

---

## 2. The cost-only objective is precision-blind

**Proposition 1 (precision-blindness).** *There exist repair instances whose set
`M*` of cost-minimal, target-valid, recall-preserving repairs contains a repair of
precision 1 and a repair of precision < 1. Hence the minimal-cost objective does not
determine precision: an algorithm minimizing only cost may return a worst-precision
member of `M*`.*

*Proof.* Two witnesses.

*(TO — the leak gadget.)* Let `S → Main | Alt`, `Main → pre·G·post`,
`Alt → pre'·G·post'` with `Alt` a different order sharing the compound `G`, and
`G → crit` the deleted action (`CLAUDE.md`, "single most important lesson"). Two
cost-1 target-valid repairs: (i) re-insert `crit` into `G` — recovers the full gold
language, `prec = 1`; (ii) re-insert `crit` into `Main` — makes `π*` derivable but
`Alt` now yields a gold-rejected trace, `prec < 1`. Both have cost 1 and preserve
recall, so `M*` straddles the precision boundary. Witnessed by `results/headline.json`
(control gap 0, ambiguous gap 2/3) and pinned by `tests/test_gap.py`.

*(PO — unordered reinsertion.)* Remove primitive `p` from a method with order `O`;
let `E_p = {(a,b) ∈ O : a = p ∨ b = p}` be the gold edges touching `p`. Re-inserting
`p` with any edge-subset `S ⊆ E_p` costs exactly 1 (ordering constraints are method
attributes, not separately costed under `ACT+`), keeps `π*` derivable (a gold
linearization respects `E_p ⊇ S`), and keeps every gold plan derivable (likewise).
Thus

> `M* = { reinsert p with S : S ⊆ E_p }`,  all cost 1, all recall-preserving,

an explicitly **enumerable** class. Its precision ranges from `prec(S = E_p) = 1`
(full gold order restored) down to `prec(S = ∅) = |linext(O)| / |linext(O \ E_p)| < 1`
whenever `E_p` constrains `p`. So `M*` again straddles the boundary. ∎

This is why we report the cost-only baseline as a *distribution over `M*`* rather
than one tie-break (the `CLAUDE.md` fair-baseline rule), enumerated exactly in
`results/po_indifference.json`: over the full 9-domain corpus (334 methods, 775
primitive-removal instances) the indifference class has **expected precision 0.55
[95% CI 0.535, 0.558]** and **worst 0.23 [0.215, 0.237]**, against **conformance 1.0**
— `prec` spreads across `M*` exactly as Prop 1 predicts (Fig. `fig_cegis`).

**Corollary 1 (cost-model sharpening).** *If ordering additions are themselves
costed (`ORD+`), the unique cost-minimizer of `M*` is `S = ∅` — the worst-precision
repair. If they are free (`ACT+`), the objective is indifferent across all of `M*`.
Either way the minimal-cost objective never prefers a higher-precision repair.*

*Proof.* `|S|` is monotone in added cost under `ORD+`, minimized at `S = ∅`; and
`prec` is non-decreasing in `S` (adding a gold edge can only remove non-gold
linearizations), minimized at `S = ∅`. Under `ACT+`, all `S` have equal cost. ∎

Corollary 1 is exactly why both numbers matter: **0.23** is what a cost-minimizer
*chooses* (`ORD+`); **0.55** is the *expected* precision if it breaks ties blindly
(`ACT+`). Neither is the precision-1 repair that exists in `M*`.

---

## 3. Conformance-aware repair closes the gap (provably, on PO)

The selector (TO) trivially attains the maximum-precision member of `M*` by scoring
`M*` on the negatives; the substantive theorem is the PO algorithm, which constructs
the precision-1 repair without enumerating `M*`.

**Algorithm (CEGIS precedence recovery, `experiments/run_po_cegis.py`).** Start from
the unordered reinsertion `C₀ = O \ E_p`. While some `ℓ ∈ linext(C)` violates a gold
edge `(a,b) ∈ O` (i.e. `ℓ` is gold-rejected), add that edge: `C ← C ∪ {(a,b)}`.

**Proposition 2 (optimality + termination).** *CEGIS (i) only ever adds gold edges,
so it is recall-preserving throughout; (ii) adds exactly the transitive-reduction
gold edges incident to `p`, one per counter-example; (iii) terminates in that many
iterations; and (iv) returns the cardinality-minimum precedence set achieving
`prec = 1`.*

*Proof.*
(i) Every counter-example is a gold-rejected linearization of `C`, so it violates
some gold edge `(a,b) ∈ O`; that edge cannot already be in `C` (a linear extension of
`C` cannot violate an edge of `C`). The added edge is therefore a *missing gold
edge*, `(a,b) ∈ O \ C`. So `C ⊆ O` is invariant, giving `linext(C) ⊇ linext(O) ⊇`
gold plans — recall preserved.
(ii)–(iii) `|O \ C|` strictly decreases each iteration, so the loop runs at most
`|O \ C₀|` times. A transitively-redundant edge `(a,b)` (implied by `(a,c),(c,b) ∈ C`)
is never violated by any `ℓ ∈ linext(C)`, so CEGIS never adds it; it adds only
transitive-reduction edges incident to `p`. (iv) The loop exits only when no
gold-rejected linearization remains, i.e. `linext(C) = linext(O)`, so `prec = 1`; and
any precision-1 repair must enforce every gold edge incident to `p`, whose minimum
generating set is precisely that transitive reduction. Hence CEGIS is
cardinality-minimum. ∎

Matches `results/po_cegis.json`: baseline **0.23 → 1.0**, **1.37 counter-examples =
1.37 missing edges** on average, **100%** of instances reach precision 1, recall 1.0
(only gold edges added). The repair is optimal in the exact sense of Prop 2(iv).

**Remark (the TO/PO reversal — why CEGIS is PO-specific).** On TO, the analogous
counter-example loop does *not* converge to a compact repair: the invalid language is
not finitely generated by precedence constraints, so a finite counter-example set
overfits (each "reject this trace" fact fails to generalize). On PO, each
counter-example *identifies one precedence edge*, which is why CEGIS is exact and
minimal here and not there (empirically confirmed; `scratchpad/cegis_proto.py`). This
reversal is the paper's sharpest structural insight and the reason the PO and TO
contributions are a *selector* and a *constructive algorithm* respectively.

---

## 4. What the theory does and does not give

- **Gives:** the gap is not incidental — Prop 1 + Cor 1 show *every* cost-only
  objective (indifferent or `ORD+`-adversarial) fails precision; Prop 2 shows the PO
  repair is provably optimal. The empirical numbers are then *measurements of a
  proven phenomenon*, not anecdotes.
- **Does not give:** Prop 1's witnesses establish existence (the gap is real and
  closable), not that *every* IPC instance has a gap — the *magnitude* is empirical
  (`po_indifference.json`, `ipc_overgen_*.jsonl`). Precision is defined relative to a
  gold `G` (here the un-fuzzed domain / oracle); the sampled `etc_P` is the practical
  estimator of Def 3 and is shown conservative (`ci_summary.json` sensitivity).
- **Genuinely partial order:** Prop 1's PO witness needs only that `E_p` constrains
  `p`, not that `O` is itself partial — yet the effect is *larger* where gold is
  genuinely partial (`genuine_partial`: expected 0.49, gap 0.71 vs 0.59), confirming
  it is a property of the repair model, not a chain-method artifact.
