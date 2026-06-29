# Extending to partially-ordered HTN

The shipped study is totally-ordered (TO) HTN, where plan verification is
CFG membership (polynomial, CYK) and "conformance" means preserving the linear
order. This is the cleanest setting to isolate the precision phenomenon. Partial
order (PO) is the natural and higher-impact extension; this note records what
changes so nobody silently reuses TO machinery where it is unsound.

## What changes

1. **Verification is harder.** PO-HTN plan verification is NP-complete in general
   (Behnke, Höller & Biundo 2015). `tcr/cfg/membership.py` (CYK) is TO-only and
   MUST NOT be used for PO domains. A PO verifier needs either a SAT/ASP encoding
   or the qualitative-temporal encoding of Schwartz & Wolter (AAAI 2026), which
   represents method orderings as an INDU/Allen qualitative constraint network
   and checks consistency.

2. **Conformance becomes richer.** In TO, an invalid trace is a wrong
   linearization. In PO, the gold domain accepts a *set* of linearizations (a
   partial order's linear extensions); precision means accepting exactly that set
   and no more. The negative-generation regimes generalize: `gold_structural`
   should sample linear extensions of gold method orderings and then apply
   order-violating edits that cross a real precedence constraint.

3. **Temporal machinery is justified only here.** For TO, durations and
   qualitative temporal relations add nothing a CFG check needs, and reaching for
   INDU/QCN on TO invites a "complexity for its own sake" objection. Reserve the
   temporal-reasoning apparatus for PO, where (a) verification genuinely needs it
   and (b) duration/qualitative constraints can express conformance that
   SAT-only or parsing baselines cannot.

## Suggested implementation path

- Add `cfg/po_membership.py` with a SAT/ASP or QCN-based acceptance check; keep
  the `accepts(domain, trace)` signature so metrics/selector are unchanged.
- Add `data/synthetic_po.py` with PO leak gadgets (a shared compound whose
  internal ordering is unconstrained, so a repair can over- or under-constrain).
- Generalize `negatives/generate.py::gold_structural` to enumerate gold linear
  extensions before editing.
- Keep the TO control family; add a PO control with a fully-ordered gold so its
  gap is still zero.

The metrics (`fitness`, `rejection`, `conformance_gap`) and the selector are
order-agnostic and need no change once a PO `accepts` exists.
