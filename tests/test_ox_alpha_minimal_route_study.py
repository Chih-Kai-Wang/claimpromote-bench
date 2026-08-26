from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_ox_alpha_minimal_route_study import (  # noqa: E402
    DATASET_ROOT,
    EXPECTED_ROOT,
    LANE_ID,
    MINIMAL_SUITE_PATH,
    build_schedule,
    request_body,
    route_lane,
)
from validate_ox_alpha_minimal_route_study import validate_freeze  # noqa: E402

Json = dict[str, Any]


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_ox_alpha_request_is_prompt_only_and_parameter_frozen() -> None:
    body = request_body(route_lane(), "test prompt")
    assert body == {
        "model": "ox-alpha-free",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": "test prompt"}],
        "stream": False,
    }
    assert "response_format" not in body
    assert "temperature" not in body
    assert "reasoning_effort" not in body


def test_ox_alpha_schedule_reuses_only_the_preexisting_minimum_witness() -> None:
    packet = load_object(DATASET_ROOT / "evaluation-prompt-packet.json")
    suite = load_object(MINIMAL_SUITE_PATH)
    plan: Json = {"route": route_lane()}
    schedule = build_schedule(plan, packet, suite)
    assert schedule["planned_cells"] == 20
    assert schedule["client_retry_count"] == 0
    assert [str(row["item_id"]) for row in schedule["cells"]] == [
        str(value) for value in suite["selected_item_ids"]
    ]
    assert {str(row["lane_id"]) for row in schedule["cells"]} == {LANE_ID}
    assert all("prompt" not in row and "gold" not in row for row in schedule["cells"])


def test_frozen_ox_alpha_study_validates_without_credentials() -> None:
    report = validate_freeze(
        EXPECTED_ROOT / "study-plan.json",
        EXPECTED_ROOT / "request-schedule.json",
    )
    assert report["status"] == "OX_ALPHA_MINIMAL_ROUTE_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert (report["items"], report["pairs"], report["planned_calls"]) == (20, 10, 20)


def test_frozen_plan_does_not_claim_a_model_family() -> None:
    plan = load_object(EXPECTED_ROOT / "study-plan.json")
    assert plan["route"]["model_identity_status"] == "UNDISCLOSED_STEALTH_MODEL"
    assert "model_family" not in plan["route"]
    assert "no claim" in plan["identity_boundary"]
