"""E_real: audit the authors' actual published LLM repairs for over-acceptance.

For every verified repair instance we decode the authors' masked repair into our
grounded (pruned) domain and measure, against the reconstructed gold domain, two
complementary things:

1. **Binary over-acceptance** -- does the repaired domain admit *any* gold-rejected
   trace among a fixed gold-structural negative set (target transpositions, target
   single-deletions, gold-language single edits)?

2. **Escaping-edges precision** (the sharper, process-mining metric; Munoz-Gama &
   Carmona 2010). We sample the *repaired domain's own language* up to the target
   length and report the fraction that the gold domain rejects -- i.e. how much of
   the behaviour the repair allows was never part of the intended language. This
   is `1 - |L(repair)_sample \\ L(gold)| / |L(repair)_sample|`, plus the raw count
   of admitted invalid plans. Unlike negative-set precision it is not diluted by
   easy negatives, so it reflects the true magnitude of over-generalisation.

Soundness is independent of the LLM: we only read its repair; every accept/reject
is our differentially-tested verifier's.
"""
from __future__ import annotations

import csv
import json
import os
import signal
import statistics
from collections import defaultdict

from tcr.cfg.membership import accepts, language_sample
from tcr.data.masking import build_mask, decode_repaired_domain
from tcr.data.sas_adapter import load_instance
from tcr.repair.prune import prune_for_plan

VERIFIED = "manual from_cfg verified"


class _Timeout(Exception):
    pass


def _negatives(gold_p, target, cap=300):
    negs: set = set()
    t = list(target)
    for i in range(len(t) - 1):
        c = tuple(t[:i] + [t[i + 1], t[i]] + t[i + 2 :])
        if c != tuple(target) and not accepts(gold_p, c):
            negs.add(c)
    for i in range(len(t)):
        c = tuple(t[:i] + t[i + 1 :])
        if c and not accepts(gold_p, c):
            negs.add(c)
    for s in language_sample(gold_p, max_len=len(target) + 1, limit=120):
        sl = list(s)
        for i in range(len(sl) - 1):
            c = tuple(sl[:i] + [sl[i + 1], sl[i]] + sl[i + 2 :])
            if c not in negs and not accepts(gold_p, c):
                negs.add(c)
        for i in range(len(sl)):
            c = tuple(sl[:i] + sl[i + 1 :])
            if c and c not in negs and not accepts(gold_p, c):
                negs.add(c)
        if len(negs) > cap:
            break
    return list(negs)[:cap]


def _escaping(repaired, gold, max_len, limit=500):
    """Process-mining escaping-edges precision over the repair's own language."""
    sample = language_sample(repaired, max_len=max_len, limit=limit)
    if not sample:
        return 1.0, 0, 0
    invalid = [t for t in sample if not accepts(gold, t)]
    n = len(sample)
    return 1.0 - len(invalid) / n, len(invalid), n


def audit_instance(inst_dir, llm_processed_path, name):
    inst = load_instance(inst_dir, name=name)
    pf = prune_for_plan(inst.flawed, inst.target)
    pg = prune_for_plan(inst.gold, inst.target)
    mm = build_mask(pf)
    repaired = decode_repaired_domain(pf, mm, open(llm_processed_path).read())
    derives = accepts(repaired, inst.target)

    negs = _negatives(pg, inst.target)
    neg_prec = 1.0 if not negs else sum(not accepts(repaired, n) for n in negs) / len(negs)
    esc_prec, n_invalid, n_lang = _escaping(repaired, pg, max_len=len(inst.target) + 1)

    return dict(
        name=name,
        domain=name.split("/")[0] if "/" in name else inst.metadata.get("family", "ipc"),
        derives=bool(derives),
        n_neg=len(negs),
        neg_precision=round(neg_prec, 4),
        escaping_precision=round(esc_prec, 4),
        n_invalid_admitted=n_invalid,
        n_lang_sampled=n_lang,
        over_accepts=bool(neg_prec < 0.9999 or n_invalid > 0),
        gold_methods=len(inst.gold.methods),
    )


def run(model, root, model_runs, csv_path, out_path, per_instance_timeout=90):
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
        lp = os.path.join(model_runs, name.replace("/", "_"), "llm_processed.txt")
        if not os.path.exists(lp):
            fout.write(json.dumps(dict(name=name, error="no_llm_processed")) + "\n")
            fout.flush()
            continue
        if have_alarm:
            signal.alarm(per_instance_timeout)
        try:
            rec = audit_instance(os.path.join(root, name), lp, name)
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
    ok = [x for x in recs if "escaping_precision" in x]
    err = [x for x in recs if "error" in x]
    oa = [x for x in ok if x["over_accepts"]]
    print(f"MODEL={model}  audited={len(ok)}  errors={len(err)}")
    if not ok:
        return
    print(f"decode derives target: {sum(x['derives'] for x in ok)}/{len(ok)}")
    print(f"over-accepts (any invalid): {len(oa)}/{len(ok)} = {len(oa)/len(ok)*100:.1f}%")
    print(f"mean negative-set precision : {statistics.mean(x['neg_precision'] for x in ok):.4f}")
    print(f"mean escaping precision     : {statistics.mean(x['escaping_precision'] for x in ok):.4f}")
    oa_esc = [x['escaping_precision'] for x in oa]
    if oa_esc:
        print(f"mean escaping precision (over-accepting instances only): {statistics.mean(oa_esc):.4f}")
    print(f"mean invalid plans admitted (over-accepting only): "
          f"{statistics.mean(x['n_invalid_admitted'] for x in oa):.1f}" if oa else "")
    bd = defaultdict(lambda: [0, 0])
    for x in ok:
        bd[x["domain"]][0] += 1
        bd[x["domain"]][1] += int(x["over_accepts"])
    for d in sorted(bd):
        print(f"   {d:34s} {bd[d][1]:>2}/{bd[d][0]:<2}")
    return dict(n=len(ok), over_accept=len(oa))


if __name__ == "__main__":
    import sys

    model = sys.argv[1] if len(sys.argv) > 1 else "openai-o4-mini-high"
    base = "data/zenodo_lutalo"
    csv_name = ("results_openai.csv" if "o4" in model
                else "results_openai_oss_120b_high.csv")
    run(
        model=model,
        root=f"{base}/socs2024-evaluation/results",
        model_runs=f"{base}/zenodo/data/model_runs/{model}",
        csv_path=f"{base}/zenodo/data/raw/{csv_name}",
        out_path=f"results/ipc_audit2_{model}.jsonl",
    )
