"""Provider-agnostic LLM repair proposer.

The repair proposer is an interface, not a vendor. Three backends implement it:

    StubProposer     : no API key needed. Proposes candidate insertions
                       symbolically (delegates to the enumerator) so the entire
                       pipeline -- and the full test suite -- runs offline and
                       deterministically. This is what CI and reviewers run.
    AnthropicProposer: Claude backend via the Anthropic Messages API.
    OpenAIProposer   : OpenAI-compatible backend (matches the o4-mini / gpt-oss
                       setup of Lutalo & Bercher 2026), usable against any
                       OpenAI-compatible endpoint.

All three consume the SAME masked prompt (names stripped to integers /
A1,A2,... and rule_1,rule_2,...), so a reviewer can verify there is no semantic
leakage regardless of backend. The masking follows Lutalo & Bercher: primitive
tasks -> integers, non-terminals -> A_i, methods -> rule_i, and the LLM may only
*insert terminals into existing rules*.

The proposer returns candidate Repairs; selection and verification happen
downstream, so an LLM can never bypass the symbolic CYK check. This keeps the
soundness of the pipeline independent of model quality -- a property reviewers
explicitly look for in LLM-in-the-loop planning papers.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from tcr.core.types import Domain, RepairInstance
from tcr.repair.candidates import Repair, candidate_single_insertions, target_valid_repairs


# --------------------------------------------------------------------------
# Masking: build the anonymized CFG prompt and the inverse maps to decode.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MaskedProblem:
    prompt: str
    term_map: dict[str, int]       # primitive -> integer
    inv_term: dict[int, str]
    nonterm_map: dict[str, str]    # compound -> A_i
    rule_map: dict[str, str]       # method_id -> rule_i
    inv_rule: dict[str, str]       # rule_i -> method_id


def build_masked_problem(instance: RepairInstance) -> MaskedProblem:
    flawed = instance.flawed
    primitives = sorted(flawed.primitives)
    compounds = sorted(flawed.compounds)
    term_map = {a: i + 1 for i, a in enumerate(primitives)}
    inv_term = {v: k for k, v in term_map.items()}
    nonterm_map = {c: f"A{i+1}" for i, c in enumerate(compounds)}
    # ensure start symbol mapping known
    rule_map = {m.mid: f"rule_{i+1}" for i, m in enumerate(flawed.methods)}
    inv_rule = {v: k for k, v in rule_map.items()}

    def enc(sym: str) -> str:
        if sym in term_map:
            return str(term_map[sym])
        return nonterm_map[sym]

    lines = []
    lines.append("I have a context free grammar (CFG).")
    lines.append(f"The initial symbol is `{nonterm_map[flawed.initial]}`.")
    lines.append("")
    lines.append("Allowed operation: insert TERMINAL symbols into existing rules.")
    lines.append("Do NOT delete, reorder existing symbols, or create new rules.")
    lines.append("Minimise the total number of insertions.")
    lines.append("")
    lines.append("Production rules:")
    for m in flawed.methods:
        rhs = " ".join(enc(s) for s in m.body) if m.body else "(empty)"
        lines.append(f"{rule_map[m.mid]}: {nonterm_map[m.head]} -> {rhs}")
    lines.append("")
    target_enc = " ".join(str(term_map[a]) for a in instance.target)
    lines.append("Target sequence:")
    lines.append(target_enc)
    lines.append("")
    lines.append(
        "Respond ONLY with JSON: a list of insertions, each "
        '{"rule": "rule_i", "position": <int>, "terminal": <int>}.'
    )
    return MaskedProblem(
        prompt="\n".join(lines),
        term_map=term_map,
        inv_term=inv_term,
        nonterm_map=nonterm_map,
        rule_map=rule_map,
        inv_rule=inv_rule,
    )


def decode_insertions(masked: MaskedProblem, raw_json: str) -> Repair:
    """Parse an LLM JSON response into a Repair, mapping masks back to names."""
    data = json.loads(raw_json)
    insertions = []
    for item in data:
        mid = masked.inv_rule[item["rule"]]
        action = masked.inv_term[int(item["terminal"])]
        pos = int(item["position"])
        insertions.append((action, mid, pos))
    return Repair(tuple(insertions))


# --------------------------------------------------------------------------
# Proposer protocol + backends
# --------------------------------------------------------------------------
class RepairProposer(Protocol):
    def propose(self, instance: RepairInstance, n: int = 8) -> list[Repair]:
        ...


class StubProposer:
    """Offline, deterministic proposer. Returns target-valid candidates.

    Crucially this does NOT cheat by reading the gold domain; it only uses the
    flawed domain and the deleted action, exactly the information a real
    proposer is given. It exists so the pipeline is runnable and testable with
    no API key, and so experiments that isolate the *selection* contribution can
    hold the candidate set fixed.
    """

    def propose(self, instance: RepairInstance, n: int = 8) -> list[Repair]:
        return target_valid_repairs(instance)


class AnthropicProposer:
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def propose(self, instance: RepairInstance, n: int = 8) -> list[Repair]:
        import anthropic  # imported lazily so the dep is optional

        client = anthropic.Anthropic(api_key=self.api_key)
        masked = build_masked_problem(instance)
        repairs: list[Repair] = []
        for _ in range(n):
            resp = client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": masked.prompt}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text")
            try:
                repairs.append(decode_insertions(masked, _extract_json(text)))
            except Exception:
                continue
        return _dedup(repairs)


class OpenAIProposer:
    def __init__(self, model: str = "o4-mini", api_key: str | None = None,
                 base_url: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")

    def propose(self, instance: RepairInstance, n: int = 8) -> list[Repair]:
        from openai import OpenAI  # lazy optional dep

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        masked = build_masked_problem(instance)
        repairs: list[Repair] = []
        for _ in range(n):
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": masked.prompt}],
            )
            text = resp.choices[0].message.content or ""
            try:
                repairs.append(decode_insertions(masked, _extract_json(text)))
            except Exception:
                continue
        return _dedup(repairs)


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        return text[start : end + 1]
    return text


def _dedup(repairs: list[Repair]) -> list[Repair]:
    seen: set = set()
    out = []
    for r in repairs:
        key = tuple(sorted(r.insertions))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def make_proposer(backend: str = "stub", **kwargs) -> RepairProposer:
    backend = backend.lower()
    if backend == "stub":
        return StubProposer()
    if backend == "anthropic":
        return AnthropicProposer(**kwargs)
    if backend in ("openai", "openai-compatible"):
        return OpenAIProposer(**kwargs)
    raise ValueError(f"unknown backend {backend!r}")
