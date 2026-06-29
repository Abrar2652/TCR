"""Adapter for real IPC-2020 HTN benchmarks (HDDL) and the Lutalo-Bercher data.

This module is a *thin, clearly-bounded* bridge from external benchmark data to
the internal grammar representation. It is intentionally optional: the synthetic
pipeline reproduces every scientific claim with zero downloads, and this adapter
lets the same claims be reproduced on the real IPC-2020 HTN domains and on the
156-instance benchmark released with Lutalo & Bercher (2026)
(Zenodo DOI 10.5281/zenodo.17620754).

We support two ingestion routes:

  1. HDDL parsing (``load_hddl``): parse a grounded, totally-ordered HDDL domain
     into our Domain. Only the TO subset is handled here; PO domains are routed
     to the partial-order conformance path (see docs/PARTIAL_ORDER.md).

  2. Pre-extracted CFG JSON (``load_cfg_json``): the Lutalo-Bercher pipeline
     already extracts a masked CFG per instance; if those artifacts are present
     we load them directly, guaranteeing we evaluate on exactly their instances.

Both routes are stubbed with explicit ``NotImplementedError`` guidance rather
than silently returning wrong data, because a half-working parser is worse than
an honest boundary for a reproducibility artifact. The grounded-HDDL -> CFG
mapping itself is straightforward (compounds->nonterminals, actions->terminals,
methods->productions) and is documented in docs/IPC_ADAPTER.md for whoever wires
in the real files.
"""
from __future__ import annotations

import json
from pathlib import Path

from tcr.core.types import Domain, Method, RepairInstance, Trace


def load_cfg_json(path: str | Path) -> Domain:
    """Load a domain from a simple CFG JSON schema.

    Schema::

        {
          "initial": "S",
          "primitives": ["a", "b", ...],
          "compounds": ["S", "P", ...],
          "methods": [{"mid": "m0", "head": "S", "body": ["P", "a"]}, ...]
        }

    This is the interchange format the synthetic exporter also writes, so the
    same loader serves both synthetic dumps and externally-converted IPC data.
    """
    data = json.loads(Path(path).read_text())
    methods = tuple(
        Method(m["mid"], m["head"], tuple(m["body"])) for m in data["methods"]
    )
    return Domain(
        primitives=frozenset(data["primitives"]),
        compounds=frozenset(data["compounds"]),
        methods=methods,
        initial=data["initial"],
    )


def dump_cfg_json(domain: Domain, path: str | Path) -> None:
    data = {
        "initial": domain.initial,
        "primitives": sorted(domain.primitives),
        "compounds": sorted(domain.compounds),
        "methods": [
            {"mid": m.mid, "head": m.head, "body": list(m.body)} for m in domain.methods
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2))


def load_instance_json(path: str | Path) -> RepairInstance:
    """Load a full repair instance (flawed + gold + target) from JSON."""
    data = json.loads(Path(path).read_text())
    return RepairInstance(
        name=data["name"],
        flawed=load_cfg_json_obj(data["flawed"]),
        gold=load_cfg_json_obj(data["gold"]),
        target=tuple(data["target"]),
        deleted_action=data.get("deleted_action"),
        metadata=data.get("metadata", {}),
    )


def load_cfg_json_obj(data: dict) -> Domain:
    methods = tuple(
        Method(m["mid"], m["head"], tuple(m["body"])) for m in data["methods"]
    )
    return Domain(
        primitives=frozenset(data["primitives"]),
        compounds=frozenset(data["compounds"]),
        methods=methods,
        initial=data["initial"],
    )


def load_hddl(domain_path: str | Path, problem_path: str | Path) -> Domain:
    raise NotImplementedError(
        "HDDL ingestion is not wired in this build. To reproduce on real "
        "IPC-2020 HTN data: ground the domain with PANDA's grounder, export the "
        "grounded methods, and convert with the mapping documented in "
        "docs/IPC_ADAPTER.md (compounds->non-terminals, actions->terminals, "
        "methods->productions). Then use load_cfg_json on the converted file."
    )
