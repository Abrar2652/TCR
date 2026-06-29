# Related work and the novelty boundary

This note states plainly what is and is not novel, so reviewers see we are not
overclaiming. Citations are by author/venue; fill bib keys when integrating.

## Closest prior work

- **Lutalo & Bercher (2026), "Automated Repair of Totally-Ordered HTN Domains
  via CFGs with LLM Support."** Repairs missing-action TO-HTN domains by CFG
  repair with optional LLM proposals; success = the target plan becomes
  derivable. This is precisely the *fitness-only* objective we extend. Their own
  future-work mentions allowing multiple valid and invalid plans — which is the
  direction we formalize and measure.
- **Lin, Höller & Bercher (SoCS 2024) and related.** Benchmark construction by
  primitive removal; repair to restore derivability.
- **Lin & Bercher (AAAI 2023), "Was Fixing This Really That Hard?"** Defines a
  repair setting with white-list/black-list plans (positive/negative) for HTN —
  but is a **complexity-theoretic** study (NP-hardness / Σ²ᵖ membership), with no
  implementation or precision metric.
- **Lin, Grastien, Shome & Bercher (AAAI 2025).** Implemented repair using
  positive AND negative examples — but for **classical** planning, not HTN.

## What we do NOT claim

- We do **not** claim to be first to use negative examples in domain repair
  (Lin & Bercher 2023 for HTN at the complexity level; Lin et al. 2025 for
  classical planning with an implementation).
- We do **not** introduce temporal/qualitative reasoning for TO-HTN (it is
  unnecessary there; see PARTIAL_ORDER.md).

## What is novel here

1. **Precision framing for HTN repair.** Importing process-mining precision
   (Muñoz-Gama & Carmona 2010; van der Aalst) to quantify over-acceptance of a
   repaired HTN domain, complementing the fitness-only incumbent objective.
2. **Demonstrating incumbent HTN repair is precision-blind**, and that the gap is
   caused specifically by shared/reused compounds — with a built-in negative
   control showing the effect vanishes without them.
3. **A precision-preserving selector** that improves precision at no cost to
   recall, plus the methodological point that measuring it requires
   gold-structural negatives, not target-permutation negatives.
4. **Grounding underspecification** in Gold's theorem (positive-data-only
   identification overgeneralizes) and CEGIS-style oracle labeling of negatives.
