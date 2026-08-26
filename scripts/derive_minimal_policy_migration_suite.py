#!/usr/bin/env python3
"""Derive a minimum graph-and-rule-complete policy-migration smoke suite."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
DEFAULT_PAIRS = (
    ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset" / "evaluation-pairs.json"
)
DEFAULT_COVERAGE = (
    ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
)
DEFAULT_OUT = ROOT / "v2" / "policy-transition-graph-v1" / "minimal-release-suite.json"


def fail(message: str) -> None:
    raise ValueError(f"minimal-policy-migration-suite: {message}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pair_rules(pair: Json) -> set[str]:
    bindings = pair.get("binding_rules")
    if not isinstance(bindings, dict):
        fail("pair lacks binding_rules")
    rules: set[str] = set()
    for binding in bindings.values():
        if not isinstance(binding, dict):
            fail("pair contains a malformed rule binding")
        rule = binding.get("rule")
        if rule is not None:
            rules.add(str(rule))
    return rules


def derive(pairs_path: Path, coverage_path: Path) -> Json:
    pairs = read_json(pairs_path)
    coverage = read_json(coverage_path)
    if not isinstance(pairs, list) or not isinstance(coverage, dict):
        fail("pair or coverage file is malformed")

    edge_inventory = sorted(str(value) for value in coverage["evaluation_transition_counts"])
    if len(edge_inventory) != 10:
        fail("expected ten reachable directed edges")
    groups: dict[str, list[Json]] = defaultdict(list)
    rule_inventory: set[str] = set()
    for pair in pairs:
        edge = str(pair.get("blue_to_amber_transition"))
        if edge not in edge_inventory:
            fail(f"pair has an unknown edge: {edge}")
        if pair.get("controlled_path") != "/active_policy_profile":
            fail("pair changes an unregistered coordinate")
        groups[edge].append(pair)
        rule_inventory.update(pair_rules(pair))
    if set(groups) != set(edge_inventory) or any(len(groups[edge]) != 6 for edge in edge_inventory):
        fail("expected six candidate pairs for every reachable edge")
    if len(rule_inventory) != 12:
        fail("expected twelve authored rule differences")

    rule_order = sorted(rule_inventory)
    rule_bits = {rule: 1 << index for index, rule in enumerate(rule_order)}
    full_mask = (1 << len(rule_order)) - 1
    states: dict[int, tuple[str, ...]] = {0: ()}
    pair_by_id = {str(pair["pair_id"]): pair for pair in pairs}
    for edge in edge_inventory:
        next_states: dict[int, tuple[str, ...]] = {}
        for prior_mask, prior_ids in states.items():
            for pair in sorted(groups[edge], key=lambda row: str(row["pair_id"])):
                mask = prior_mask
                for rule in pair_rules(pair):
                    mask |= rule_bits[rule]
                candidate = (*prior_ids, str(pair["pair_id"]))
                current = next_states.get(mask)
                if current is None or candidate < current:
                    next_states[mask] = candidate
        states = next_states
    selected_ids = states.get(full_mask)
    if selected_ids is None:
        fail("no one-pair-per-edge selection covers all rules")
    selected = [pair_by_id[pair_id] for pair_id in selected_ids]
    selected_edges = {str(pair["blue_to_amber_transition"]) for pair in selected}
    selected_rules = set().union(*(pair_rules(pair) for pair in selected))
    selected_items = [str(item_id) for pair in selected for item_id in pair["member_ids"]]
    if selected_edges != set(edge_inventory) or selected_rules != rule_inventory:
        fail("derived suite does not satisfy both adequacy coordinates")

    result: Json = {
        "schema_version": "1.0.0",
        "suite_id": "claimpromotebench-minimal-policy-migration-smoke-suite-2026-08-v1",
        "status": "PROVABLY_MINIMUM_GRAPH_AND_RULE_COMPLETE_SUITE",
        "model_or_client_calls_to_derive": 0,
        "objective": (
            "Minimize controlled pairs while covering every reachable BLUE-to-AMBER oracle-action "
            "edge and all authored profile-difference rules in the frozen candidate pool."
        ),
        "optimality_certificate": {
            "lower_bound_pairs": len(edge_inventory),
            "lower_bound_reason": (
                "Each controlled pair realizes exactly one directed action edge, so covering ten "
                "distinct reachable edges requires at least ten pairs."
            ),
            "witness_pairs": len(selected),
            "bound_met": len(selected) == len(edge_inventory),
        },
        "coverage": {
            "reachable_edges": {"covered": len(selected_edges), "total": len(edge_inventory)},
            "changed_rules": {"covered": len(selected_rules), "total": len(rule_inventory)},
        },
        "selected_pair_ids": list(selected_ids),
        "selected_item_ids": selected_items,
        "selected_pairs": [
            {
                "pair_id": str(pair["pair_id"]),
                "member_ids": [str(value) for value in pair["member_ids"]],
                "blue_to_amber_transition": str(pair["blue_to_amber_transition"]),
                "binding_rules": sorted(pair_rules(pair)),
            }
            for pair in selected
        ],
        "execution_budget": {
            "minimum_smoke_pairs": len(selected),
            "minimum_smoke_items": len(selected_items),
            "balanced_diagnostic_pairs": len(pairs),
            "balanced_diagnostic_items": 2 * len(pairs),
            "item_call_reduction_fraction": 1.0 - len(selected_items) / (2 * len(pairs)),
        },
        "interpretation_boundary": (
            "The minimum suite is a deterministic structural smoke gate. It preserves the two "
            "published adequacy coordinates but not six-context-per-edge balance, factor-level "
            "diagnostics, or repeated-context evidence for a stochastic route."
        ),
        "source_bindings": {
            "evaluation_pairs_sha256": sha256_file(pairs_path),
            "transition_coverage_sha256": sha256_file(coverage_path),
        },
    }
    result["self_digest"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--expect", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = derive(args.pairs, args.coverage)
    if args.expect is not None and result != read_json(args.expect):
        fail(f"derived suite differs from expected receipt: {args.expect}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "minimal-policy-migration-suite: "
        f"pairs={result['optimality_certificate']['witness_pairs']} "
        f"items={result['execution_budget']['minimum_smoke_items']} "
        f"rules={result['coverage']['changed_rules']['covered']}/"
        f"{result['coverage']['changed_rules']['total']} "
        f"edges={result['coverage']['reachable_edges']['covered']}/"
        f"{result['coverage']['reachable_edges']['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
