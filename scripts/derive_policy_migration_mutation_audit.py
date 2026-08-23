#!/usr/bin/env python3
"""Audit policy-migration suites against edge-local stale-policy mutants."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
PROFILE_ORDER = ("POLICY_BLUE", "POLICY_AMBER")
DEFAULT_RULE_PAIRS = (
    ROOT / "v2" / "policy-switch-v1" / "frozen" / "dataset" / "evaluation-pairs.json"
)
DEFAULT_RULE_COVERAGE = ROOT / "v2" / "policy-switch-v1" / "policy-difference-coverage.json"
DEFAULT_GRAPH_PAIRS = (
    ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset" / "evaluation-pairs.json"
)
DEFAULT_GRAPH_COVERAGE = (
    ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
)
DEFAULT_OUT = ROOT / "v2" / "policy-transition-graph-v1" / "mutation-audit.json"


def fail(message: str) -> None:
    raise ValueError(f"policy-migration-mutation-audit: {message}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def transition(pair: Json) -> str:
    profiles = pair.get("active_profiles")
    actions = pair.get("expected_actions")
    if not isinstance(profiles, list) or not isinstance(actions, list):
        fail("pair lacks active_profiles or expected_actions")
    if len(profiles) != 2 or len(actions) != 2 or set(profiles) != set(PROFILE_ORDER):
        fail("pair must contain exactly one BLUE and one AMBER member")
    if any(action not in ACTIONS for action in actions):
        fail("pair contains an unknown action")
    by_profile = dict(zip(profiles, actions, strict=True))
    observed = f"{by_profile['POLICY_BLUE']}->{by_profile['POLICY_AMBER']}"
    if by_profile["POLICY_BLUE"] == by_profile["POLICY_AMBER"]:
        fail("policy pair does not change action")
    registered = pair.get("blue_to_amber_transition")
    if registered is not None and registered != observed:
        fail("registered transition disagrees with pair actions")
    if pair.get("controlled_path") != "/active_policy_profile":
        fail("pair changes an unregistered coordinate")
    return observed


def suite_summary(pairs: list[Json], reachable: set[str]) -> Json:
    counts = Counter(transition(pair) for pair in pairs)
    unknown = set(counts) - reachable
    if unknown:
        fail(f"suite contains transitions outside the reachable graph: {sorted(unknown)}")
    detected = sorted(counts)
    missed = sorted(reachable - set(counts))
    return {
        "evaluation_pairs": len(pairs),
        "transition_counts": dict(sorted(counts.items())),
        "edge_local_mutants_detected": detected,
        "edge_local_mutants_missed": missed,
        "edge_local_mutant_detection": {
            "numerator": len(detected),
            "denominator": len(reachable),
            "value": len(detected) / len(reachable),
        },
    }


def derive(
    rule_pairs_path: Path,
    rule_coverage_path: Path,
    graph_pairs_path: Path,
    graph_coverage_path: Path,
) -> Json:
    rule_pairs = read_json(rule_pairs_path)
    graph_pairs = read_json(graph_pairs_path)
    rule_coverage = read_json(rule_coverage_path)
    graph_coverage = read_json(graph_coverage_path)
    if not isinstance(rule_pairs, list) or not isinstance(graph_pairs, list):
        fail("pair files must contain JSON arrays")

    reachable = set(graph_coverage["evaluation_transition_counts"])
    if len(reachable) != 10:
        fail("reachable transition inventory must contain ten edges")
    if set(graph_coverage["structurally_unreachable_transitions"]) & reachable:
        fail("reachable and unreachable transition inventories overlap")

    rule_summary = suite_summary(rule_pairs, reachable)
    graph_summary = suite_summary(graph_pairs, reachable)
    rule_summary["changed_rule_coverage"] = {
        "numerator": rule_coverage["coverage"]["authored_profile_difference_factors_covered"],
        "denominator": rule_coverage["coverage"]["authored_profile_difference_factors_total"],
    }
    graph_summary["changed_rule_coverage"] = {
        "numerator": graph_coverage["authored_profile_difference_rules_covered"],
        "denominator": graph_coverage["authored_profile_difference_rules_total"],
    }

    result: Json = {
        "schema_version": "1.0.0",
        "audit_id": "claimpromotebench-policy-migration-edge-mutant-audit-2026-08-v1",
        "status": "EDGE_LOCAL_MIGRATION_MUTATION_AUDIT_COMPLETE",
        "model_or_client_calls": 0,
        "mutant_family": {
            "name": "SINGLE_EDGE_STALE_POLICY",
            "definition": (
                "For each reachable BLUE-to-AMBER oracle-action edge e=(a,b), mutant m_e "
                "returns the stale BLUE action a on AMBER executions whose correct transition "
                "is e, and otherwise agrees with the published executor."
            ),
            "detection_criterion": (
                "A controlled pair kills m_e exactly when its BLUE-to-AMBER action transition "
                "is e. Therefore a suite kills every mutant in this registered family if and "
                "only if it covers every reachable directed action edge."
            ),
            "interpretation_boundary": (
                "This deterministic oracle-side audit gives operational meaning to transition "
                "coverage. It is not a prevalence model for deployment faults and does not use "
                "or evaluate model outputs."
            ),
        },
        "reachable_edge_inventory": sorted(reachable),
        "structurally_unreachable_edges": graph_coverage["structurally_unreachable_transitions"],
        "suites": {
            "rule_stratified": rule_summary,
            "transition_graph": graph_summary,
        },
        "source_bindings": {
            "rule_pairs_sha256": sha256_file(rule_pairs_path),
            "rule_coverage_sha256": sha256_file(rule_coverage_path),
            "graph_pairs_sha256": sha256_file(graph_pairs_path),
            "graph_coverage_sha256": sha256_file(graph_coverage_path),
        },
    }
    result["self_digest"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule-pairs", type=Path, default=DEFAULT_RULE_PAIRS)
    parser.add_argument("--rule-coverage", type=Path, default=DEFAULT_RULE_COVERAGE)
    parser.add_argument("--graph-pairs", type=Path, default=DEFAULT_GRAPH_PAIRS)
    parser.add_argument("--graph-coverage", type=Path, default=DEFAULT_GRAPH_COVERAGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = derive(
        args.rule_pairs,
        args.rule_coverage,
        args.graph_pairs,
        args.graph_coverage,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "policy-migration-mutation-audit: "
        f"rule={result['suites']['rule_stratified']['edge_local_mutant_detection']['numerator']}/"
        f"{result['suites']['rule_stratified']['edge_local_mutant_detection']['denominator']} "
        f"graph={result['suites']['transition_graph']['edge_local_mutant_detection']['numerator']}/"
        f"{result['suites']['transition_graph']['edge_local_mutant_detection']['denominator']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
