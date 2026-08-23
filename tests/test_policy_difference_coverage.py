from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "derive_policy_difference_coverage.py"
DATASET = ROOT / "v2" / "policy-switch-v1" / "frozen" / "dataset"
POLICY = ROOT / "v2" / "policy-switch-v1" / "policy-contract.json"
RECEIPT = ROOT / "v2" / "policy-switch-v1" / "policy-difference-coverage.json"


def module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("derive_policy_difference_coverage", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_policy_difference_coverage_recomputes_byte_exactly() -> None:
    value = module().derive(DATASET, POLICY)
    observed = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert value == observed
    coverage = value["coverage"]
    assert coverage["authored_profile_difference_factors_covered"] == 12
    assert coverage["authored_profile_difference_factors_total"] == 12
    assert coverage["contexts_per_factor"] == 5
    assert coverage["directed_nonself_action_transitions_covered"] == 6
    assert coverage["directed_nonself_action_transitions_possible_over_four_actions"] == 12
    assert set(coverage["blue_to_amber_transition_counts"].values()) == {10}


def test_policy_difference_receipt_states_incomplete_action_graph() -> None:
    value = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert value["coverage"]["transition_scope"] == (
        "ADMISSION_CENTERED_STAR_NOT_COMPLETE_ACTION_GRAPH"
    )
    assert "not the complete four-action transition graph" in value["interpretation_boundary"]
