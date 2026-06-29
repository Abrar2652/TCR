"""Regression guard for the partial-order corpus completeness.

A glob that matched only `<domain>/domain.hddl` silently dropped Monroe-* and
PCP (per-instance `*-domain.hddl` files), shrinking the PO corpus to 6 domains /
111 methods and reporting n_gold_partial == 0. `iter_domain_methods` now covers
both layouts; these tests fail if that regresses.
"""
import os

import pytest

from tcr.experiments.run_po_ipc_overaccept import iter_domain_methods, linext_count

PO_ROOT = "data/ipc2020-domains/partial-order"

pytestmark = pytest.mark.skipif(
    not os.path.isdir(PO_ROOT), reason="IPC-2020 partial-order data not present"
)

EXPECTED_DOMAINS = {
    "Barman-BDI", "Monroe-Fully-Observable", "Monroe-Partially-Observable",
    "PCP", "Rover", "Satellite", "Transport", "UM-Translog", "Woodworking",
}


def _collect():
    return list(iter_domain_methods(PO_ROOT))


def test_all_nine_domains_present():
    doms = {dom for dom, *_ in _collect()}
    missing = EXPECTED_DOMAINS - doms
    assert not missing, f"PO corpus dropped domains: {missing}"


def test_monroe_and_pcp_contribute_methods():
    # the two layouts both reach the corpus; Monroe/PCP were the dropped ones
    by_dom = {}
    for dom, *_ in _collect():
        by_dom[dom] = by_dom.get(dom, 0) + 1
    for d in ("Monroe-Fully-Observable", "Monroe-Partially-Observable", "PCP"):
        assert by_dom.get(d, 0) >= 10, f"{d} contributed too few methods: {by_dom.get(d)}"


def test_corpus_size_floor():
    # 334 unique methods (yielding 775 primitive-removal units) at the time of
    # writing; floor guards against silent shrink (the bug dropped it to ~65)
    assert len(_collect()) >= 300


def test_genuine_partial_order_methods_exist():
    # the whole PO claim needs at least some gold methods with reordering freedom
    n_partial = sum(
        1 for _, subs, _, order in _collect()
        if len(subs) <= 14 and linext_count(len(subs), order) > 1
    )
    assert n_partial >= 5, f"expected genuinely partial-order gold methods, found {n_partial}"
