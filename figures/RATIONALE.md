# Figure rationale

Every figure is driven by a file in `results/` (never mocked) and carries one
message readable in 10 seconds, rewarding a 2-minute look. Typography, palette,
and sizing are fixed by `figstyle.py` (Okabe–Ito, STIX serif + DejaVu Sans,
single-column 3.3in, vector PDF + 400-dpi PNG, black-edged marks, no titles).

We first reproduce the three "obvious" bars (conformance gap, precision gain,
timeline gap) for completeness, then propose six figures that deliver an insight
no table can. Below is the argument for each novel figure: the intuition it
builds, why a table or the obvious bars fail to convey it, and the encoding that
makes it land.

---

## N1 — The *invisibility* slopegraph (the methodological punchline)
**File:** `headline.json` (E1 conformance gap, family × negative-generation regime).
**Claim:** the conformance gap is invisible to target-local negatives and appears
only under gold-structural negatives — and the control never shows a gap.

*Intuition.* The single most counter-intuitive result is that whether you *see*
the gap depends entirely on where your negative examples come from: permuting or
editing the target plan reports gap = 0, while sampling near the gold language's
own structure reveals gap = 0.667. A reader must feel the gap "switch on" as the
negative source moves away from the target.

*Why a table fails.* A 5×4 table of numbers makes the reader hunt for the pattern;
the zeros look like missing data, not a finding. The story is a *trajectory*
across regimes, which a table flattens.

*Encoding.* A slopegraph: x = the four regimes ordered by distance-from-target
(permute → mutate → edit → gold-structural), y = mean gap, one bold line per
family, the `linear_control` line pinned flat at 0 and greyed. The ambiguous
families fan upward only at gold-structural; the control stays on the floor. The
flat control line doubles as the "the evaluator isn't manufacturing failures"
proof — both halves of the methodological point in one frame.

## N2 — The over-generalization *cliff* (the empirical centerpiece)
**Files:** `ipc_overgen_openai-o4-mini-high.jsonl`, `…gpt-oss-120b-high.jsonl`.
**Claim:** on real IPC, SOTA minimal-cost repairs admit a length-matched language
that is only ~10% valid (median 0.003), versus the gold-pruned control at 1.0.

*Intuition.* The published o4-mini / gpt-oss repairs *do* restore the target plan,
but among all correct-length plans they now admit, almost none are valid. The
reader should see a cliff from the gold reference at 1.0 down to a floor of points
near zero.

*Why a table fails.* "Mean precision 0.10" reads as "pretty good." The shape —
a heavy mass at ~0 with a long thin tail, two independent models landing on the
same floor, and a control glued to 1.0 — is the persuasive part, and only a
distribution shows it.

*Encoding.* Per-instance precision as rank-ordered dots for both models (shared
floor), with the gold-pruned control drawn as a solid reference line at y = 1.0
and direct-labeled. A second, faint reference at the mean. Two models on one
floor = robustness without a legend lookup.

## N3 — The indifference-set *spread* (geometry of the repair space)
**File:** `selector_comparison.json` (cost-only worst/expected vs conformance, by
family × regime, all at fitness = 1.0).
**Claim:** at a single insertion cost, the target-valid repairs span a precision
range that the cost-only objective is blind to; our selector takes the top.

*Intuition.* "Underspecified" becomes physical: the minimum-cost repairs are a set,
not a point, and they disagree on precision. Cost-only draws somewhere in that
set (its expected value); we always grab the ceiling.

*Why a table fails.* Three precision columns (worst / expected / conformance) ask
the reader to mentally compute the spread per row. Drawn, the spread *is* the
figure — the height of each interval is exactly the precision the incumbent
leaves on the table.

*Encoding.* For each ambiguous family, a vertical interval from cost-only-worst to
conformance (= ceiling), the cost-only-expected marked as a hollow tick, our pick
as a filled cap at the top. All share fitness = 1.0, so the x-axis is the family
and the vertical extent is the unrecoverable-by-cost precision. Control family
collapses to a point on the 1.0 line.

## N4 — CEGIS recovery and the TO↔PO reversal (the method + the twist)
**File:** `po_cegis.json` (baseline vs CEGIS precision and counter-examples used,
per partial-order domain).
**Claim:** counter-example-guided conformance repair lifts precision 0.26 → 1.00
using ~1.4 counter-examples (= the number of missing precedence edges, optimal) —
and it works on PO precisely where it provably fails on TO.

*Intuition.* The same idea (let negatives guide the repair) is useless in one
regime and optimal in the other, because on PO each counter-example pins exactly
one missing ordering constraint. The reader should see a short, near-vertical
climb to the gold ceiling, annotated by how few counter-examples it cost — and a
TO marker sitting inert at the bottom-left to mark the contrast.

*Why a table fails.* The punchline is a *contrast* (TO fails, PO succeeds) plus an
*efficiency* (CEs ≈ missing edges). A table reports two numbers; the figure makes
"few counter-examples, full recovery, only in PO" a single gestalt.

*Encoding.* A dumbbell per PO domain from baseline precision to 1.0, the connector
labeled with the mean counter-example count; a single TO annotation (CEGIS gives
no lift, the reordering gap is 0 there) anchored at the contrast corner.

## N5 — Over-acceptance *compounds* with plan length (closing the domain-level gap)
**File:** `po_fulldomain.json` (+ a per-derivation dump for the curve).
**Claim:** the per-method over-acceptance (~0.27) multiplies across a derivation,
so domain-level precision decays with plan length — to ~6% valid on 13-action
UM-Translog plans — computed exactly with no membership solver.

*Intuition.* A local 0.27 sounds survivable; the figure shows it compounding so a
realistic plan is almost entirely invalid. The decay-with-length curve makes the
multiplicative structure visible.

*Why a table fails.* Two domains × two corruption rates is four numbers; the
*mechanism* (precision ≈ per-method-precision^(#methods), hence decaying with
length) is a curve, and the p = 0 control sitting exactly at 1.0 is the proof the
measurement is sound.

*Encoding.* Precision vs plan length, derivations binned by their leaf count, a
band for the spread, two corruption rates as two bold lines, and the p = 0
control as a flat reference at 1.0. Direct-labeled endpoints; the gap between the
curves and 1.0 is the over-acceptance.

## N6 — The leak *mechanism* (a derivation-tree diagram, conformant vs leaky)
**Source:** the `_leak_gadget` structure documented in `CLAUDE.md` /
`data/synthetic.py` — real domain structure, drawn schematically.
**Claim:** the gap has a single concrete cause — a compound shared between two
derivations — and the repair's *placement* of the re-inserted action decides
conformant vs leaky.

*Intuition.* Every quantitative figure measures the gap; this one *explains* it.
Inserting the deleted action into the shared compound recovers the gold language;
inserting it into the target-local method makes the target derivable but lets the
other branch leak a gold-rejected trace. Seeing the two trees side by side makes
the asymmetry obvious and memorable.

*Why a table/bar fails.* No aggregate can show *why* the gap exists; the cause is
structural and local. This is the figure a reviewer recalls when explaining the
paper to a colleague.

*Encoding.* Two minimal derivation trees side by side sharing the same gadget;
the re-inserted action drawn as a filled node at the shared compound (left,
conformant — both branches keep it) versus at the target-local method (right,
leaky — the alt branch is missing it); the leaked, gold-rejected trace printed
under the leaky tree in the incumbent color. Node/edge only, no axes.
