"""Reproduce Lutalo & Bercher's CFG masking, to decode their LLM repairs.

Their pipeline prunes a flawed domain to the target, then emits a *masked* CFG
prompt (``to_cfg.txt``): terminals become integers 1..K, non-terminals become
A1..Am, rules become rule_1..rule_M. The LLM's repair (``llm_processed.txt``) is
expressed in these masked names. To measure whether their *actual* repair
over-accepts, we must map a masked insertion ``rule_N: ... <terminal j> ...``
back to our grounded domain (method id + grounded primitive id).

We reproduce their masking exactly (verified by regenerating ``to_cfg.txt``),
which is the robust way to recover the bijection. Convention (from their
``llm.cpp`` ``to_cfg`` + ``pruner.cpp`` reindex):

  * work on the *pruned* domain;
  * terminal id j (1..K) = the j-th primitive in ascending original-task-id
    order among kept primitives;
  * non-terminal A_i (1..M) = the i-th compound in ascending original-task-id
    order among kept compounds (A1 is the initial/top task, the smallest-id
    compound);
  * rule_N (1..) = methods sorted by (head's A-index, then elementwise by each
    subtask's masked key [terminal id or A-index], then by body length),
    1-indexed in that order.

The grounded ids are our ``t{k}`` strings, so "ascending original-task-id" means
ascending integer ``k``.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcr.core.types import Domain, Method


def _tid(sym: str) -> int:
    return int(sym[1:])  # "t41" -> 41


@dataclass
class MaskMap:
    term_to_int: dict[str, int]      # grounded primitive "t{k}" -> masked int
    int_to_term: dict[int, str]
    comp_to_a: dict[str, int]        # grounded compound "t{k}" -> masked A index
    rule_methods: list[Method]       # methods in rule_1..rule_M order
    mid_to_rule: dict[str, int]      # method id -> rule number (1-indexed)

    def masked_key(self, sym: str) -> int:
        if sym in self.term_to_int:
            return self.term_to_int[sym]
        return self.comp_to_a.get(sym, 0)


def build_mask(pruned: Domain) -> MaskMap:
    prims = sorted(pruned.primitives, key=_tid)
    comps = sorted(pruned.compounds, key=_tid)
    term_to_int = {p: i + 1 for i, p in enumerate(prims)}
    int_to_term = {i + 1: p for i, p in enumerate(prims)}
    comp_to_a = {c: i + 1 for i, c in enumerate(comps)}

    def key(sym: str) -> int:
        return term_to_int[sym] if sym in term_to_int else comp_to_a.get(sym, 0)

    def sort_key(m: Method):
        return (comp_to_a[m.head], tuple(key(s) for s in m.body), len(m.body))

    rule_methods = sorted(pruned.methods, key=sort_key)
    mid_to_rule = {m.mid: i + 1 for i, m in enumerate(rule_methods)}
    return MaskMap(term_to_int, int_to_term, comp_to_a, rule_methods, mid_to_rule)


def render_masked_rules(pruned: Domain, mm: MaskMap) -> list[str]:
    """Regenerate the masked ``rule_N: A_i -> ...`` lines, to validate against
    the authors' shipped ``to_cfg.txt``."""
    lines = []
    for n, m in enumerate(mm.rule_methods, start=1):
        head = f"A{mm.comp_to_a[m.head]}"
        body = " ".join(
            str(mm.term_to_int[s]) if s in mm.term_to_int else f"A{mm.comp_to_a[s]}"
            for s in m.body
        )
        lines.append(f"rule_{n}: {head} -> {body}".rstrip())
    return lines


def decode_repaired_domain(pruned: Domain, mm: MaskMap, llm_processed: str) -> Domain:
    """Apply an authors' masked repair (``llm_processed.txt`` body) to our grounded
    pruned domain, returning their repaired domain in grounded coordinates.

    Each line ``rule_N: A_i -> <tokens>`` gives the FULL updated body of rule N;
    we decode tokens (int -> grounded terminal, A_k -> grounded compound) and
    replace that method's body. Unlisted rules keep their flawed body.
    """
    a_to_comp = {a: c for c, a in mm.comp_to_a.items()}
    methods = list(pruned.methods)
    by_mid = {m.mid: idx for idx, m in enumerate(methods)}

    for ln in llm_processed.splitlines():
        ln = ln.strip()
        if not (ln.startswith("rule_") and "->" in ln):
            continue
        tag, rest = ln.split(":", 1)
        try:
            n = int(tag.split("_")[1])
        except (IndexError, ValueError):
            continue
        if not (1 <= n <= len(mm.rule_methods)):
            continue
        body_str = rest.split("->", 1)[1].strip()
        new_body: list[str] = []
        ok = True
        for tok in body_str.split():
            if tok.startswith("A"):
                try:
                    ai = int(tok[1:])
                except ValueError:
                    ok = False
                    break
                if ai not in a_to_comp:
                    ok = False
                    break
                new_body.append(a_to_comp[ai])
            else:
                try:
                    ti = int(tok)
                except ValueError:
                    ok = False
                    break
                if ti not in mm.int_to_term:
                    ok = False
                    break
                new_body.append(mm.int_to_term[ti])
        if not ok:
            continue
        target_method = mm.rule_methods[n - 1]
        idx = by_mid[target_method.mid]
        methods[idx] = Method(target_method.mid, target_method.head, tuple(new_body))

    return Domain(pruned.primitives, pruned.compounds, tuple(methods), pruned.initial)


def parse_their_cfg_rules(to_cfg_txt: str) -> dict[int, str]:
    """Extract ``rule_N`` body lines from an authors' ``to_cfg.txt`` (normalized)."""
    out: dict[int, str] = {}
    for ln in to_cfg_txt.splitlines():
        ln = ln.strip()
        if ln.startswith("rule_") and ":" in ln:
            tag, rest = ln.split(":", 1)
            try:
                n = int(tag.split("_")[1])
            except (IndexError, ValueError):
                continue
            out[n] = rest.strip()
    return out
