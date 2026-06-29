# Real IPC-2020 results: the conformance gap in the wild

This note records the real-benchmark study that complements the synthetic
controlled experiments. It evaluates the *precision* (over-acceptance) axis on
the exact IPC-2020 HTN repair benchmark used by Lutalo & Bercher (AAAI 2026) and
Lin, Höller & Bercher (SoCS 2024), and audits the authors' own published LLM
repairs.

## Data pipeline (all validated)

- **Ingestion** (`tcr/data/sas_adapter.py`): parse PANDA grounded `out-fuzzed.sas`
  (flawed) + `plan` (target). **Gold = flawed + reverse(`fuzz-ops`)** — re-insert
  each removed primitive `t` at its original list position in method `m`. Gold and
  flawed share the identical task-id coordinate system, so traces are directly
  comparable. Verified across all 193 instances: gold derives the target, flawed
  does not (non-trivial) / does (trivial), matching the authors' labels with **0
  anomalies**; task/method counts match their C++ parser exactly.
- **Pruning** (`tcr/repair/prune.py`): faithful port of their target-relative TDG
  pruning. Reproduces their masked CFG **exactly** (e.g. Depots/p01: 12 terminals,
  22 non-terminals, 40 rules). Makes the 1.3M-method tail (Hiking p16) tractable.
- **Masking decode** (`tcr/data/masking.py`): reproduces their `to_cfg.txt`
  byte-for-byte on rules (8/8 instances, all domains), so their masked LLM repairs
  decode unambiguously to our grounded domain. Sanity: every decoded repair
  re-derives the target, and our insertion counts equal their CSV
  `terminal_insertions`.
- **Verifier**: membership is an Earley recognizer (`tcr/cfg/membership.py`),
  replacing CYK whose CNF epsilon-elimination was exponential in nullable symbols
  per body (it hung on recursive domains such as Transport). Held to the same
  differential oracle (245 tests pass).

The real benchmark is **multi-deletion** (e.g. Depots/p01 removes 35 actions
across 28 methods, target length 15); minimal repairs fix only the target-path
methods (median `terminal_insertions` = 5), leaving the rest of the hierarchy
under-repaired — the structural setting in which over-acceptance arises.

## E1 — the conformance gap exists in the incumbent's repair space

The repair space matters. The **menu** space (re-insert only the actually-removed
actions into their own methods) is gold-biased and shows gap 0 (every min-cost
repair is precise). The **general insert-anywhere** space — the one the LLM and
the optimal symbolic encoder actually search — does not:

- Woodworking/03--p02-part2/plan-2: cost 2, **17 distinct min-cost target-valid
  repairs, 41% of them over-accept** a gold-rejected trace.

So the minimum-insertion objective is genuinely underspecified on real data.

## E2 — the centerpiece: minimal-cost repairs over-generalize massively

The right precision metric is the process-mining **escaping-edges precision** over
the repaired domain's *own* length-matched language (Muñoz-Gama & Carmona 2010):
randomly derive plans of the **target length L** from a domain and report the
fraction the gold domain accepts. (A naive over-all-lengths version is biased by
trivially-too-short traces; restricting to length L removes that artifact. An
earlier negative-set precision read ≈0.99 because it was diluted by easy negatives.)

Fairness control: the ideal target-scope domain (gold pruned to the target) scores
**precision 1.000 (min 1.000)** under the *same* sampler — so neither the sampler
nor pruning manufactures invalidity. Labeling validated pruned-gold == full-gold.

| domain set | o4-mini repair precision | gpt-oss repair precision |
|---|---|---|
| gold-pruned (control) | **1.000** | **1.000** |
| all scored instances | 0.21 | 0.22 |
| **ambiguous instances** | **0.10** (median 0.003) | **0.13** (median 0.003) |

So on structurally-ambiguous IPC domains, **~90% (often ~99%) of the correct-length
plans the SOTA repairs admit are invalid**. 70/76 (o4-mini) and 67/77 (gpt-oss)
ambiguous instances have precision < 0.5. **Domain-concentrated** exactly where the
theory predicts (Rover/Satellite/Blocksworld/Depots ≈0.02–0.12; Childsnack,
Entertainment, Hiking trivially 1.0 — the real-data analogue of the synthetic
`linear_control` control). Robust across two independent SOTA models. The over-
acceptance is **not** target reorderings (those are ~0 on TO-HTN — rigid order) but
alternative invalid plans produced by loose repaired methods.

`experiments/run_ipc_overgeneralization.py`, `results/ipc_overgen_*.jsonl`.

## E3 — cost–precision tension (theory) and the limits of cheap fixes

Reaching high precision requires near-complete gold recovery: a greedy completion
frontier on Depots goes cost 5 → precision 0.12 up to cost 17 → precision 1.0;
Satellite cost 3 → cost 6 raises precision 0.04 → 0.44. **Minimal cost and precision
are in fundamental tension; all prior work optimizes only cost and therefore sits at
the precision-pessimal corner.**

Two would-be cheap fixes were tested and *honestly do not work* on single-plan
TO-HTN:
- **Counter-example-guided (CEGIS) repair** does not beat blind completion (and
  sometimes does worse): the invalid length-L language is combinatorially huge, so a
  finite set of counter-examples overfits and does not generalize
  (`scratchpad/cegis_proto.py`).
- The conformance-aware **selector** gives only small gains (it helps at the min-cost
  tie-break margin, but the over-generalization is inherent to minimal cost, not a
  tie-break).

This is why the project pivots to **partial-order HTN** (see
`PARTIAL_ORDER_PLAN.md`), where reordering over-acceptance is structural and large,
counter-examples pin specific missing precedence constraints, and the temporal layer
is load-bearing.

## Reproduce

```
results/ipc_audit_openai-o4-mini-high.jsonl     # per-instance o4-mini audit
results/ipc_audit_openai-gpt-oss-120b-high.jsonl# per-instance gpt-oss audit
results/ipc_selector.jsonl                      # selector E2 (tractable subset)
results/ipc_summary.json                        # consolidated headline numbers
```

Data lives under `data/zenodo_lutalo/` (Zenodo 17620754 = authors' artifact incl.
their run outputs; Zenodo 10946945 = socs2024 benchmark). Scripts that produced
these are in the session scratchpad and should be promoted into
`tcr/experiments/` for the camera-ready.
