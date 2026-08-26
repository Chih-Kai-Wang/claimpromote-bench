from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_output_contract_transport_diagnostics import classify_transport  # noqa: E402
from review_gap_experiments import (  # noqa: E402
    MODELS,
    NONALLOW_CASES,
    NONALLOW_REASON_ACTION,
    NONALLOW_ROOT,
    OUTPUT_CONDITIONS,
    OUTPUT_ROOT,
    REQUEST_SEED,
    REQUEST_TEMPERATURE,
    REQUEST_TOP_P,
    portable_provider_schema,
    request_body,
)
from run_review_gap_experiments import diagnose_nonallow, expected_records_per_lane  # noqa: E402
from validate_review_gap_experiments import validate_frozen  # noqa: E402


def test_output_ablation_varies_only_registered_contract_coordinates() -> None:
    assert [row["condition_id"] for row in OUTPUT_CONDITIONS] == [
        "prompt-4096",
        "prompt-8192",
        "prompt-12288",
        "json-schema-4096",
    ]
    assert {int(row["max_output_tokens"]) for row in OUTPUT_CONDITIONS} == {
        4096,
        8192,
        12288,
    }
    assert {str(row["model"]) for row in MODELS} == {"glm-5.3", "hy3", "qwen3.7-plus"}


def test_nonallow_support_has_every_nonallow_action_and_no_allow_endpoint() -> None:
    actions = Counter(
        str(case[version]["action"]) for case in NONALLOW_CASES for version in ("before", "after")
    )
    assert len(NONALLOW_CASES) == 8
    assert sum(not bool(case["changed"]) for case in NONALLOW_CASES) == 6
    assert sum(bool(case["changed"]) for case in NONALLOW_CASES) == 2
    assert actions == Counter({"HOLD": 6, "ESCALATE": 6, "DEMOTE": 4})
    assert "ALLOW" not in actions
    stable_actions = Counter(
        str(case["before"]["action"]) for case in NONALLOW_CASES if not bool(case["changed"])
    )
    assert stable_actions == Counter({"HOLD": 2, "ESCALATE": 2, "DEMOTE": 2})
    assert all(
        case["before"]["action"] != case["after"]["action"]
        and "ALLOW" not in {case["before"]["action"], case["after"]["action"]}
        for case in NONALLOW_CASES
        if bool(case["changed"])
    )


def test_nonallow_reason_codes_bind_one_action() -> None:
    observed = {
        str(reason)
        for case in NONALLOW_CASES
        for version in ("before", "after")
        for reason in case[version]["reason_codes"]
    }
    assert observed == set(NONALLOW_REASON_ACTION)
    for case in NONALLOW_CASES:
        for version in ("before", "after"):
            assert all(
                NONALLOW_REASON_ACTION[str(reason)] == case[version]["action"]
                for reason in case[version]["reason_codes"]
            )
        assert str(case["mapping_rationale"]).strip()
        assert set(case["evidence_quotes"]) == {"before", "after"}
        assert all(case["evidence_quotes"][version] for version in ("before", "after"))


def test_smoke_tested_json_schema_request_is_strict_and_portable() -> None:
    schema = json.loads((ROOT / "schemas" / "agent-decision.schema.json").read_text())
    lane = {
        "model": "hy3",
        "max_output_tokens": 4096,
        "response_format": "json_schema",
    }
    body = request_body(lane, "prompt", schema)
    assert body["temperature"] == REQUEST_TEMPERATURE == 0
    assert body["top_p"] == REQUEST_TOP_P == 1
    assert body["seed"] == REQUEST_SEED == 20260825
    registered = body["response_format"]["json_schema"]
    assert registered["strict"] is True
    assert registered["name"] == "registered_decision"
    assert "$defs" not in registered["schema"]
    assert "$ref" not in json.dumps(registered["schema"])
    assert portable_provider_schema(schema)["additionalProperties"] is False


def test_nonallow_semantics_apply_precedence_across_multiple_reasons() -> None:
    item = {"case_id": "nonallow-joint-test", "policy_version": "AFTER"}
    joint = {
        "case_id": item["case_id"],
        "policy_version": item["policy_version"],
        "action": "ESCALATE",
        "reason_codes": ["USER_ONLY_PUBLICATION", "SECURITY_REVIEW_REQUIRED"],
    }
    status, decision, _ = diagnose_nonallow(json.dumps(joint), item)
    assert status == "OK"
    assert decision == joint

    joint["action"] = "HOLD"
    status, decision, detail = diagnose_nonallow(json.dumps(joint), item)
    assert status == "SEMANTIC_ERROR"
    assert decision is None
    assert detail == "action does not match reason-code precedence"


def test_regenerated_frozen_plans_bind_transitive_runtime_and_budget() -> None:
    assert validate_frozen(OUTPUT_ROOT)["cells"] == 360
    assert validate_frozen(NONALLOW_ROOT)["cells"] == 240
    for root in (OUTPUT_ROOT, NONALLOW_ROOT):
        plan = json.loads((root / "study-plan.json").read_text())
        assert plan["budget"]["conservative_schedule_quota_value_with_10pct_margin_usd"] < 12
        assert plan["budget"]["incremental_cash_spend_observable"] is False
        assert {
            "scripts/run_public_model_breadth_study.py",
            "scripts/run_stronger_model_study.py",
            "scripts/analyze_balanced_public_challenge.py",
            "src/claimpromotebench/dataset.py",
            "src/claimpromotebench/hashing.py",
            "pyproject.toml",
        }.issubset(plan["runtime_sources"])


def test_nonallow_mapping_removed_invalid_woo_case_and_pins_awell_operation() -> None:
    assert all(case["case_id"] != "nonallow-woo-shipping-rename-change" for case in NONALLOW_CASES)
    awell = [case for case in NONALLOW_CASES if case["source_id"] == "awell-score-authoring-policy"]
    assert len(awell) == 2
    for case in awell:
        for version in ("before", "after"):
            quote = case["evidence_quotes"][version][0]
            assert "imports all 124 scores" in quote
            assert "registration assertion" in quote
            assert quote.endswith("Not urgent at 25 seconds.")


def test_runner_lane_publication_uses_frozen_selected_item_count() -> None:
    output_schedule = json.loads((OUTPUT_ROOT / "request-schedule.json").read_text())
    nonallow_schedule = json.loads((NONALLOW_ROOT / "request-schedule.json").read_text())
    assert expected_records_per_lane(output_schedule) == 30
    assert expected_records_per_lane(nonallow_schedule) == 16


def test_output_contract_transport_diagnostic_uses_content_free_categories() -> None:
    assert classify_transport("HTTP 402: usage limit reached") == "QUOTA_OR_BILLING_REJECTION"
    assert classify_transport("HTTP 503: service unavailable") == "SERVER_5XX"
    assert classify_transport("The read operation timed out") == "TIMEOUT"
    assert classify_transport("connection reset by peer") == "NETWORK"
    assert classify_transport("unrecognized transport failure") == "OTHER_TRANSPORT_ERROR"
