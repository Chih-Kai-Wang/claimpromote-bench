from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_policy_switch_hosted_replacement_eligibility import (  # noqa: E402
    classify_records,
)
from freeze_policy_switch_hosted_replacement import (  # noqa: E402
    RESOURCE_EXHAUSTION_RULE,
    SOURCE_EXCLUSION,
    SOURCE_PLAN,
)

STUDY = ROOT / "v2" / "policy-switch-v1" / "hosted-replacement-v2"
DATASET = ROOT / "v2" / "policy-switch-v1" / "frozen" / "dataset"
BASELINE = ROOT / "v2" / "policy-switch-v1" / "frozen" / "baseline"


def test_hosted_replacement_freeze_validates_without_credentials() -> None:
    from validate_policy_switch_hosted_replacement import validate_freeze

    report = validate_freeze(
        STUDY / "study-plan.json",
        STUDY / "request-schedule.json",
        DATASET,
        BASELINE,
    )
    assert report["status"] == "POLICY_SWITCH_HOSTED_REPLACEMENT_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert (report["items"], report["lanes"], report["cells"]) == (120, 2, 240)


def test_hosted_replacement_is_not_a_resume_or_successful_subset() -> None:
    plan = json.loads((STUDY / "study-plan.json").read_text(encoding="utf-8"))
    selection = json.loads((STUDY / "selection-audit.json").read_text(encoding="utf-8"))
    exclusion = json.loads(SOURCE_EXCLUSION.read_text(encoding="utf-8"))
    source_plan = json.loads(SOURCE_PLAN.read_text(encoding="utf-8"))
    assert plan["study_id"] != source_plan["study_id"]
    assert plan["execution"]["partial_resume"] == "FORBIDDEN"
    assert plan["execution"]["client_retry_count"] == 0
    assert plan["replacement"]["predecessor_outputs_eligible"] is False
    assert selection["predecessor_outputs_available_and_inspected"] is True
    assert selection["local_policy_switch_terminal_records_before_freeze"] == 0
    assert exclusion["decision"]["successful_row_subset_selected"] is False
    assert plan["execution"]["resource_exhaustion_eligibility_rule"] == RESOURCE_EXHAUSTION_RULE


def test_hosted_replacement_changes_only_protocol_identifiers() -> None:
    plan = json.loads((STUDY / "study-plan.json").read_text(encoding="utf-8"))
    source_plan = json.loads(SOURCE_PLAN.read_text(encoding="utf-8"))
    for lane, source_lane in zip(plan["formal_lanes"], source_plan["formal_lanes"], strict=True):
        assert {key: value for key, value in lane.items() if key != "lane_id"} == {
            key: value for key, value in source_lane.items() if key != "lane_id"
        }
    for field in ("budget", "statistics", "sources", "baselines", "interpretation_boundary"):
        assert plan[field] == source_plan[field]


def terminal(sequence: int, *, status: str, error: str | None = None) -> dict[str, object]:
    return {
        "sequence": sequence,
        "cell_id": f"cell-{sequence}",
        "record": {
            "transport_status": status,
            "transport_error": error,
            "parse_status": "OK" if status == "OK" else "TRANSPORT_ERROR",
        },
    }


def test_resource_rule_excludes_only_a_persistent_explicit_exhaustion_tail() -> None:
    rows = [terminal(sequence, status="OK") for sequence in range(240)]
    rows[200] = terminal(200, status="ERROR", error="Weekly usage limit has been reached")
    for sequence in range(201, 240):
        rows[sequence] = terminal(sequence, status="ERROR", error="HTTP 429")
    result = classify_records(rows)
    assert result["eligible_for_model_efficacy_reporting"] is False
    assert result["persistent_exhaustion_trigger_sequence"] == 200


def test_resource_rule_keeps_ordinary_failures_and_recovered_service_in_denominator() -> None:
    rows = [terminal(sequence, status="OK") for sequence in range(240)]
    for sequence in range(100, 120):
        rows[sequence] = terminal(sequence, status="ERROR", error="HTTP 429 rate limit")
    rows[150] = terminal(150, status="ERROR", error="Quota exhausted")
    rows[151] = terminal(151, status="OK")
    result = classify_records(rows)
    assert result["eligible_for_model_efficacy_reporting"] is True
    assert result["persistent_exhaustion_trigger_sequence"] is None
