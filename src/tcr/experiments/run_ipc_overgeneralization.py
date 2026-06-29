"""E_precision (the real one): over-generalization of SOTA repairs, measured as
process-mining escaping-edges precision over the repaired domain's OWN language.

For each instance we sample, by random leftmost derivation, the set of plans of the
TARGET LENGTH that a domain admits, and report the fraction the GOLD domain accepts
(= precision; how much of the behaviour the model allows is actually valid). We do
this for:

  * gold-pruned  -- the target-scope ideal; admits only valid plans  (precision ~1)
  * their repair -- pruned flawed + the authors' decoded insertions

A precise repair would match gold's language; the minimal-cost repair instead
leaves methods loose, so it admits many invalid same-length plans. This is the
canonical precision notion (Munoz-Gama & Carmona 2010) and is length-matched, so
it is free of the short-trace artifact that inflates naive language sampling.

Fairness: gold-pruned sampled the SAME way yields ~100% valid, so neither pruning
nor the sampler manufactures invalidity -- the over-generalisation is the repair's.
"""
from __future__ import annotations

import csv
import json
import os
import signal
import statistics
from collections import defaultdict

from tcr.cfg.membership import accepts
from tcr.core.types import Domain
from tcr.data.masking import build_mask, decode_repaired_domain
from tcr.data.sas_adapter import load_instance
from tcr.repair.prune import prune_for_plan

VERIFIED = "manual from_cfg verified"


class _Timeout(Exception):
    pass


def _rand_derive(domain: Domain, rng, max_len=200, max_steps=3000):
    seq = [domain.initial]
    steps = 0
    comps = domain.compounds
    while steps < max_steps:
        steps += 1
        idx = next((i for i, s in enumerate(seq) if s in comps), None)
        if idx is None:
            return tuple(seq)
        ms = domain.methods_for(seq[idx])
        if not ms:
            return None
        m = rng.choice(ms)
        seq = seq[:idx] + list(m.body) + seq[idx + 1 :]
        if len(seq) > max_len:
            return None
    return None


def _sample_len(domain: Domain, L: int, rng, n=300, tries=10000):
    out: set = set()
    t = 0
    while len(out) < n and t < tries:
        t += 1
        s = _rand_derive(domain, rng)
        if s is not None and len(s) == L:
            out.add(s)
    return out


def _precision_len(domain: Domain, gold: Domain, L: int, seed: int, n=300):
    import random

    sample = _sample_len(domain, L, random.Random(seed), n=n)
    if not sample:
        return None, 0, 0
    valid = sum(accepts(gold, s) for s in sample)
    return valid / len(sample), valid, len(sample)


def overgen_instance(inst_dir, llm_processed_path, name):
    inst = load_instance(inst_dir, name=name)
    pf = prune_for_plan(inst.flawed, inst.target)
    pg = prune_for_plan(inst.gold, inst.target)
    mm = build_mask(pf)
    rep = decode_repaired_domain(pf, mm, open(llm_processed_path).read())
    if not accepts(rep, inst.target):
        return dict(name=name, error="repair_does_not_derive_target")
    L = len(inst.target)
    gold_p, gv, gn = _precision_len(pg, inst.gold, L, seed=2)
    rep_p, rv, rn = _precision_len(rep, inst.gold, L, seed=1)
    return dict(
        name=name,
        domain=name.split("/")[0] if "/" in name else "ipc",
        L=L,
        gold_pruned_precision=None if gold_p is None else round(gold_p, 4),
        gold_n_lenL=gn,
        repair_precision=None if rep_p is None else round(rep_p, 4),
        repair_valid=rv,
        repair_n_lenL=rn,
        ambiguous=bool(rn > 1 or gn > 1),
    )


def run(model, root, model_runs, csv_path, out_path, gold_cap=8000, per_instance_timeout=120):
    have_alarm = hasattr(signal, "SIGALRM")
    if have_alarm:
        signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(_Timeout()))
    done = set()
    if os.path.exists(out_path):
        for ln in open(out_path):
            try:
                done.add(json.loads(ln)["name"])
            except Exception:
                pass
    rows = [r for r in csv.DictReader(open(csv_path)) if r["status"] == VERIFIED]
    rows.sort(key=lambda r: int(r["methods"]) if r["methods"] else 0)
    fout = open(out_path, "a")
    for r in rows:
        name = r["path"]
        if name in done:
            continue
        if r["methods"] and int(r["methods"]) > gold_cap:
            fout.write(json.dumps(dict(name=name, error="gold_too_large")) + "\n")
            fout.flush()
            continue
        lp = os.path.join(model_runs, name.replace("/", "_"), "llm_processed.txt")
        if not os.path.exists(lp):
            fout.write(json.dumps(dict(name=name, error="no_llm_processed")) + "\n")
            fout.flush()
            continue
        if have_alarm:
            signal.alarm(per_instance_timeout)
        try:
            rec = overgen_instance(os.path.join(root, name), lp, name)
            if have_alarm:
                signal.alarm(0)
        except _Timeout:
            if have_alarm:
                signal.alarm(0)
            rec = dict(name=name, error="timeout")
        except Exception as e:  # noqa: BLE001
            if have_alarm:
                signal.alarm(0)
            rec = dict(name=name, error=f"{type(e).__name__}:{str(e)[:50]}")
        fout.write(json.dumps(rec) + "\n")
        fout.flush()
    fout.close()
    return summarize(out_path, model)


def summarize(out_path, model):
    recs = [json.loads(l) for l in open(out_path)]
    ok = [x for x in recs if x.get("repair_precision") is not None]
    amb = [x for x in ok if x["ambiguous"]]
    print(f"MODEL={model}  scored={len(ok)} (errors/skipped={len(recs) - len(ok)})  ambiguous={len(amb)}")
    if not ok:
        return
    print(f"mean gold-pruned precision (sanity, ~1): {statistics.mean(x['gold_pruned_precision'] for x in ok if x['gold_pruned_precision'] is not None):.3f}")
    print(f"mean REPAIR precision (all):       {statistics.mean(x['repair_precision'] for x in ok):.3f}")
    if amb:
        print(f"mean REPAIR precision (ambiguous): {statistics.mean(x['repair_precision'] for x in amb):.3f}")
        print(f"ambiguous instances with repair precision < 0.5: {sum(x['repair_precision'] < 0.5 for x in amb)}/{len(amb)}")
    bd = defaultdict(list)
    for x in ok:
        bd[x["domain"]].append(x["repair_precision"])
    for d in sorted(bd):
        print(f"   {d:34s} mean repair-precision {statistics.mean(bd[d]):.3f}  (n={len(bd[d])})")


if __name__ == "__main__":
    import sys

    model = sys.argv[1] if len(sys.argv) > 1 else "openai-o4-mini-high"
    base = "data/zenodo_lutalo"
    csv_name = "results_openai.csv" if "o4" in model else "results_openai_oss_120b_high.csv"
    run(
        model=model,
        root=f"{base}/socs2024-evaluation/results",
        model_runs=f"{base}/zenodo/data/model_runs/{model}",
        csv_path=f"{base}/zenodo/data/raw/{csv_name}",
        out_path=f"results/ipc_overgen_{model}.jsonl",
    )
