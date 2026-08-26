from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_policy_transition_graph_hosted_study import (  # noqa: E402
    RESOURCE_EXHAUSTION_RULE,
    SOURCE_HOSTED_PLAN,
)
from validate_policy_transition_graph_hosted_study import validate_freeze  # noqa: E402

STUDY = ROOT / "v2" / "policy-transition-graph-v1" / "hosted-v1"
DATASET = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset"
BASELINE = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "baseline"


def test_hosted_transition_graph_freeze_validates_without_credentials() -> None:
    report = validate_freeze(
        STUDY / "study-plan.json",
        STUDY / "request-schedule.json",
        DATASET,
        BASELINE,
    )
    assert report["status"] == "POLICY_TRANSITION_GRAPH_HOSTED_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert (report["pairs"], report["reachable_transitions"], report["cells"]) == (
        60,
        10,
        240,
    )


def test_hosted_transition_graph_selection_is_preinference_and_complete() -> None:
    plan = json.loads((STUDY / "study-plan.json").read_text(encoding="utf-8"))
    schedule = json.loads((STUDY / "request-schedule.json").read_text(encoding="utf-8"))
    selection = json.loads((STUDY / "selection-receipt.json").read_text(encoding="utf-8"))
    assert selection["hosted_transition_graph_terminal_records_before_freeze"] == 0
    assert selection["local_transition_graph_terminal_records_before_freeze"] == 0
    assert selection["outcomes_used_to_choose_graph_edges_or_contexts"] is False
    assert plan["design"]["reachable_directed_nonself_transitions"] == 10
    assert plan["execution"]["partial_resume"] == "FORBIDDEN"
    assert plan["execution"]["client_retry_count"] == 0
    assert plan["execution"]["resource_exhaustion_eligibility_rule"] == RESOURCE_EXHAUSTION_RULE
    assert schedule["planned_cells"] == 240
    assert schedule["application_posts_per_cell"] == 1


def test_hosted_transition_graph_reuses_exact_hosted_route_protocols() -> None:
    plan = json.loads((STUDY / "study-plan.json").read_text(encoding="utf-8"))
    source = json.loads(SOURCE_HOSTED_PLAN.read_text(encoding="utf-8"))
    for lane, source_lane in zip(plan["formal_lanes"], source["formal_lanes"], strict=True):
        assert {key: value for key, value in lane.items() if key != "lane_id"} == {
            key: value for key, value in source_lane.items() if key != "lane_id"
        }


def test_hosted_transition_graph_is_excluded_as_one_complete_resource_failure() -> None:
    eligibility = json.loads(
        (STUDY / "results" / "manuscript-eligibility-receipt.json").read_text(encoding="utf-8")
    )
    privacy = json.loads((STUDY / "results" / "privacy-receipt.json").read_text(encoding="utf-8"))
    assert (
        eligibility["status"]
        == "HOSTED_TRANSITION_GRAPH_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
    )
    assert eligibility["classification"]["explicit_resource_exhaustion_errors"] == 240
    assert eligibility["decision"]["all_240_terminal_outcomes_considered"] is True
    assert eligibility["decision"]["conditional_success_subset_selected"] is False
    assert eligibility["decision"]["hosted_model_rows_enter_manuscript"] is False
    assert privacy["terminal_records_validated"] == 240
    assert privacy["credentials_included"] is False
    assert privacy["provider_response_identifiers_included"] is False
    assert privacy["hidden_reasoning_fields_included"] is False
    assert all(value == 0 for value in privacy["secret_pattern_findings"].values())
