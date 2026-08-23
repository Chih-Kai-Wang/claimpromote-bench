from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claimpromotebench.policy_difference import (
    PolicyDifference,
    absent_edges,
    adequacy,
    compile_policy_differences,
    minimum_complete_suite,
    minimum_lower_bound_witness,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_GRAPH_ROOT = ROOT / "v2" / "policy-transition-graph-v1"
REVIEW_GRAPH_ROOT = ROOT / "evidence" / "local-model-replications" / "policy-transition-graph"
GRAPH_ROOT = PRIVATE_GRAPH_ROOT if PRIVATE_GRAPH_ROOT.is_dir() else REVIEW_GRAPH_ROOT


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pair_rules(pair: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        str(binding["rule"])
        for binding in pair["binding_rules"].values()
        if binding["rule"] is not None
    )


def test_compile_policy_differences_retains_only_changed_actions() -> None:
    contexts = (
        {"id": "a", "left": "ALLOW", "right": "HOLD", "rules": ["signature"]},
        {"id": "b", "left": "ALLOW", "right": "ALLOW", "rules": []},
    )
    rows = compile_policy_differences(
        contexts,
        left_policy=lambda row: str(row["left"]),
        right_policy=lambda row: str(row["right"]),
        context_id=lambda row: str(row["id"]),
        rule_witnesses=lambda row: list(row["rules"]),
    )
    assert rows == (PolicyDifference("a", "ALLOW", "HOLD", frozenset({"signature"})),)
    report = adequacy(
        rows,
        required_rules={"signature"},
        required_edges={("ALLOW", "HOLD")},
    )
    assert report.complete
    assert (report.rule_fraction, report.edge_fraction) == (1.0, 1.0)
    assert ("HOLD", "ALLOW") in absent_edges(rows, ("ALLOW", "HOLD"))


def test_generic_minimum_witness_reproduces_frozen_policy_migration_suite() -> None:
    dataset_root = GRAPH_ROOT / "frozen" / "dataset"
    if not dataset_root.is_dir():
        dataset_root = GRAPH_ROOT / "dataset"
    pairs = load_json(dataset_root / "evaluation-pairs.json")
    coverage = load_json(dataset_root.parent / "transition-coverage.json")
    expected = load_json(GRAPH_ROOT / "minimal-release-suite.json")
    candidates = []
    for pair in pairs:
        left, right = str(pair["blue_to_amber_transition"]).split("->")
        candidates.append(
            PolicyDifference(
                context_id=str(pair["pair_id"]),
                left_action=left,
                right_action=right,
                witnessed_rules=pair_rules(pair),
            )
        )
    required_edges = {tuple(edge.split("->")) for edge in coverage["evaluation_transition_counts"]}
    required_rules = {rule for row in candidates for rule in row.witnessed_rules}
    selected = minimum_lower_bound_witness(
        candidates,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    assert selected is not None
    assert [row.context_id for row in selected] == expected["selected_pair_ids"]
    assert adequacy(
        selected,
        required_rules=required_rules,
        required_edges=required_edges,
    ).complete
    exact = minimum_complete_suite(
        candidates,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    assert exact is not None
    assert len(exact) == len(required_edges)
    assert adequacy(
        exact,
        required_rules=required_rules,
        required_edges=required_edges,
    ).complete


def test_exact_minimum_suite_can_exceed_the_edge_lower_bound() -> None:
    candidates = (
        PolicyDifference("a-edge-rule-1", "A", "B", frozenset({"r1"})),
        PolicyDifference("a-edge-rule-2", "A", "B", frozenset({"r2"})),
        PolicyDifference("b-edge", "B", "A", frozenset({"r3"})),
    )
    required_rules = {"r1", "r2", "r3"}
    required_edges = {("A", "B"), ("B", "A")}
    assert (
        minimum_lower_bound_witness(
            candidates,
            required_rules=required_rules,
            required_edges=required_edges,
        )
        is None
    )
    selected = minimum_complete_suite(
        candidates,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    assert selected is not None
    assert [row.context_id for row in selected] == [
        "a-edge-rule-1",
        "a-edge-rule-2",
        "b-edge",
    ]
    assert adequacy(
        selected,
        required_rules=required_rules,
        required_edges=required_edges,
    ).complete
