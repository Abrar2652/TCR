# IPC-2020 / Zenodo benchmark adapter

The synthetic study reproduces every claim with no downloads. This note explains
how to additionally reproduce on the real IPC-2020 HTN domains and on the
benchmark released with Lutalo & Bercher (2026), Zenodo DOI
10.5281/zenodo.17620754.

## Route A — use their pre-extracted CFGs (recommended)

The Lutalo–Bercher pipeline already converts each grounded, totally-ordered HTN
instance into a masked CFG. If you have those artifacts, write each one as the
CFG-JSON schema below and load with `tcr.data.ipc_adapter.load_cfg_json`:

```json
{
  "initial": "S",
  "primitives": ["a", "b", "..."],
  "compounds": ["S", "P", "..."],
  "methods": [{"mid": "m0", "head": "S", "body": ["P", "a"]}]
}
```

This guarantees you evaluate on exactly their instances.

## Route B — ground HDDL yourself

1. Take the IPC-2020 total-order HDDL domain + problem.
2. Ground with PANDA's grounder (Höller et al.). Grounding removes lifted
   parameters so methods become concrete symbol sequences.
3. Map: compound tasks → non-terminals, primitive actions → terminals, each
   grounded method → a production (`head → body`), the initial task network's
   single abstract task → start symbol. (Only single-task initial networks map
   directly; wrap multi-task initial networks in a fresh start non-terminal.)
4. Emit the CFG-JSON above and load via `load_cfg_json`.

`load_hddl` currently raises `NotImplementedError` with this guidance rather than
shipping a half-correct parser — for a reproducibility artifact an honest
boundary beats a silent bug.

## Corruption on real data

Use `tcr.htn.corrupt.corrupt_probabilistic` with `p = 0.30` to match the
benchmark's random 30% primitive-removal protocol, then keep only non-trivial
instances (target no longer derivable). For multi-action removals use
`tcr.repair.candidates.enumerate_k` for candidate generation.
