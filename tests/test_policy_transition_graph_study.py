from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_policy_transition_graph_study import validate  # noqa: E402

DATASET = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset"
COVERAGE = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
ADDENDUM = (
    ROOT / "v2" / "policy-transition-graph-v1" / "transition-coverage-interpretation-addendum.json"
)


def test_policy_transition_graph_coverage_recomputes_with_corrected_explanation() -> None:
    historical = json.loads(COVERAGE.read_text(encoding="utf-8"))
    observed = validate(DATASET)
    for field in (
        "directed_nonself_action_transitions_possible",
        "directed_action_transitions_semantically_reachable",
        "directed_action_transitions_covered",
        "evaluation_transition_counts",
        "authored_profile_difference_rules_covered",
        "structurally_unreachable_transitions",
    ):
        assert observed[field] == historical[field]
    assert observed["directed_nonself_action_transitions_possible"] == 12
    assert observed["directed_action_transitions_semantically_reachable"] == 10
    assert observed["directed_action_transitions_covered"] == 10
    assert set(observed["evaluation_transition_counts"].values()) == {6}
    assert observed["authored_profile_difference_rules_covered"] == 12
    assert "reaches DEMOTE before HOLD" in observed["unreachability_certificate"]


def test_policy_transition_graph_profiles_have_identical_action_support() -> None:
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    support = coverage["profile_action_support"]
    assert support["POLICY_BLUE"] == support["POLICY_AMBER"]
    assert support["POLICY_BLUE"] == {
        "ALLOW": 18,
        "HOLD": 12,
        "DEMOTE": 12,
        "ESCALATE": 18,
    }


def test_hold_demote_edges_have_a_structural_unreachability_certificate() -> None:
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    assert coverage["structurally_unreachable_transitions"] == [
        "HOLD->DEMOTE",
        "DEMOTE->HOLD",
    ]
    assert addendum["source_transition_coverage_sha256"].endswith(
        "bb02a0165b3be0db63dc842442b93fa25d4bd37aa9a45bdeff1b502d6331df83"
    )
    assert addendum["conclusions_changed"] is False
    assert "reaches DEMOTE before HOLD" in addendum["corrected_certificate"]
    assert set(addendum["authorized_validation_source_updates"]) == {
        "scripts/build_policy_transition_graph_study.py",
        "scripts/validate_minimal_policy_migration_hosted_study.py",
        "scripts/validate_policy_transition_graph_hosted_study.py",
        "scripts/validate_policy_transition_graph_local_study.py",
        "scripts/validate_policy_transition_graph_study.py",
    }


def test_transition_graph_pair_contract_changes_only_profile() -> None:
    items = {
        row["id"]: row["model_visible"]
        for row in map(
            json.loads,
            (DATASET / "evaluation-items.jsonl").read_text(encoding="utf-8").splitlines(),
        )
    }
    pairs = json.loads((DATASET / "evaluation-pairs.json").read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for pair in pairs:
        left, right = (items[item_id] for item_id in pair["member_ids"])
        assert {key: value for key, value in left.items() if key != "active_policy_profile"} == {
            key: value for key, value in right.items() if key != "active_policy_profile"
        }
        counts[pair["blue_to_amber_transition"]] += 1
    assert len(counts) == 10
    assert set(counts.values()) == {6}


def test_transition_graph_builder_is_importable() -> None:
    path = ROOT / "scripts" / "build_policy_transition_graph_study.py"
    spec = importlib.util.spec_from_file_location("policy_transition_graph_builder", path)
    assert spec is not None and spec.loader is not None
