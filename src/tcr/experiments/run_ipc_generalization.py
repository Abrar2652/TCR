"""E_generalize: does a single-target-plan repair actually repair the DOMAIN?

The repair problem (Lin, Hoeller & Bercher 2024; Lutalo & Bercher 2026) inserts a
minimum number of actions to make ONE target plan derivable. The stated goal,
however, is repairing the flawed *domain model*. We test whether the repaired
model generalises: does it derive the domain's *other* valid plans, or only the
one it was handed?

For each instance we port the authors' (pruned) repair back onto the FULL flawed
domain by method id, then sample plans from the GOLD (uncorrupted) domain other
than the target and measure how many the repaired domain still derives -- a recall
/ generalisation rate. Gold derives all of them by construction; the minimal
single-plan repair, having fixed only the target's derivation path, typically does
not. This quantifies the overfitting of the single-plan objective for the first
time, motivating a multi-plan / gold-aligned repair objective.
"""
from __future__ import annotations

import csv
import json
import os
import signal
import statistics
from collections import defaultdict

from tcr.cfg.membership import accepts, language_sample
from tcr.core.types import Domain
from tcr.data.masking import build_mask, decode_repaired_domain
from tcr.data.sas_adapter import load_instance
from tcr.repair.prune import prune_for_plan

VERIFIED = "manual from_cfg verified"


class _Timeout(Exception):
    pass


def apply_repair_to_full(full_flawed: Domain, pruned: Domain, repaired_pruned: Domain) -> Domain:
    """Port the pruned-domain body edits onto the full flawed domain by method id."""
    base = {m.mid: m.body for m in pruned.methods}
    edited = {
        m.mid: m.body
        for m in repaired_pruned.methods
        if base.get(m.mid) != m.body
    }
    new = [m.with_body(edited[m.mid]) if m.mid in edited else m for m in full_flawed.methods]
    return Domain(full_flawed.primitives, full_flawed.compounds, tuple(new), full_flawed.initial)


def generalization(inst_dir, llm_processed_path, name, n_plans=200):
    inst = load_instance(inst_dir, name=name)
    pf = prune_for_plan(inst.flawed, inst.target)
    mm = build_mask(pf)
    rep_p = decode_repaired_domain(pf, mm, open(llm_processed_path).read())
    full_rep = apply_repair_to_full(inst.flawed, pf, rep_p)

    if not accepts(full_rep, inst.target):
        return dict(name=name, error="repair_does_not_derive_target")

    # other valid plans from the gold domain (gold derives them by construction)
    others = [t for t in language_sample(inst.gold, max_len=len(inst.target) + 3, limit=n_plans + 50)
              if t != tuple(inst.target)]
    others = others[:n_plans]
    if not others:
        return dict(name=name, error="no_other_gold_plans")
    derived = sum(accepts(full_rep, t) for t in others)
    return dict(
        name=name,
        domain=name.split("/")[0] if "/" in name else "ipc",
        n_other_plans=len(others),
        n_derived=derived,
        recall=round(derived / len(others), 4),
        gold_methods=len(inst.gold.methods),
    )


def run(model, root, model_runs, csv_path, out_path, gold_cap=8000, per_instance_timeout=90):
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
            rec = generalization(os.path.join(root, name), lp, name)
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
    ok = [x for x in recs if "recall" in x]
    if not ok:
        print(f"MODEL={model}: no scored instances")
        return
    print(f"MODEL={model}  scored={len(ok)}  (errors/skipped={len(recs) - len(ok)})")
    print(f"mean recall on OTHER gold plans: {statistics.mean(x['recall'] for x in ok):.3f}")
    print(f"median recall: {statistics.median(x['recall'] for x in ok):.3f}")
    print(f"instances with recall < 50%: {sum(x['recall'] < 0.5 for x in ok)}/{len(ok)}")
    print(f"instances with recall = 0%:  {sum(x['recall'] == 0 for x in ok)}/{len(ok)}")
    bd = defaultdict(list)
    for x in ok:
        bd[x["domain"]].append(x["recall"])
    for d in sorted(bd):
        print(f"   {d:34s} mean recall {statistics.mean(bd[d]):.2f}  (n={len(bd[d])})")


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
        out_path=f"results/ipc_generalization_{model}.jsonl",
    )
