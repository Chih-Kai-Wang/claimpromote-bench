from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from factor_complete_route_breadth import (  # noqa: E402
    CONFIGURATIONS,
    DATASET_ROOT,
    PACKET_PATH,
    REPLICATIONS,
    conservative_cost_upper_bound_usd,
    expanded_lanes,
    request_body,
    schedule_payload,
    selected_action_counts,
    selected_item_ids,
    selected_pairs,
)
from validate_factor_complete_route_breadth import validate_study  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402


def test_factor_complete_selection_covers_every_factor_and_action() -> None:
    pairs = load_json(DATASET_ROOT / "pairs.json")
    assert isinstance(pairs, list)
    selected = selected_pairs(pairs)
    item_ids = selected_item_ids(pairs)
    actions = selected_action_counts(load_jsonl(DATASET_ROOT / "gold.jsonl"), item_ids)
    assert len(selected) == 15
    assert len({str(row["factor_id"]) for row in selected}) == 15
    assert len(item_ids) == 30
    assert actions == Counter({"ALLOW": 15, "HOLD": 5, "DEMOTE": 5, "ESCALATE": 5})


def test_route_request_bodies_preserve_one_prompt_only_contract() -> None:
    lanes = expanded_lanes()
    assert len(lanes) == len(CONFIGURATIONS) * REPLICATIONS == 21
    by_kind = {str(row["api_kind"]): row for row in lanes}
    chat = request_body(by_kind["openai_compatible"], "prompt")
    messages = request_body(by_kind["anthropic_messages"], "prompt")
    responses = request_body(by_kind["openai_responses"], "prompt")
    assert chat["messages"] == [{"role": "user", "content": "prompt"}]
    assert messages["messages"] == [{"role": "user", "content": "prompt"}]
    assert chat["max_tokens"] == messages["max_tokens"] == 4096
    assert responses["input"][0]["content"] == [{"type": "input_text", "text": "prompt"}]
    assert responses["max_output_tokens"] == 4096
    assert all("response_format" not in body for body in (chat, messages, responses))


def test_schedule_is_complete_balanced_and_below_quota_bound() -> None:
    pairs = load_json(DATASET_ROOT / "pairs.json")
    assert isinstance(pairs, list)
    packet = load_json(PACKET_PATH)
    plan = {"formal_lanes": expanded_lanes()}
    schedule = schedule_payload(plan, packet, pairs)
    assert schedule["planned_cells"] == 630
    assert schedule["planned_groups"] == 90
    assert schedule["planned_items_per_lane"] == 30
    assert len({str(row["cell_id"]) for row in schedule["cells"]}) == 630
    lane_counts = Counter(str(row["lane_id"]) for row in schedule["cells"])
    assert set(lane_counts.values()) == {30}
    group_counts = Counter(int(row["group_index"]) for row in schedule["cells"])
    assert set(group_counts.values()) == {len(CONFIGURATIONS)}
    assert conservative_cost_upper_bound_usd() < 7.0 < 12.0


def test_completed_study_binds_runtime_sources_at_frozen_commit() -> None:
    study_root = ROOT / "v2" / "factor-complete-route-breadth-v2"
    result = validate_study(
        study_root / "study-plan.json",
        study_root / "request-schedule.json",
        frozen_plan_commit="d25172929bfea74a1bd48a44d75972e30834fadd",
    )
    assert result["runtime_source_validation"] == "FROZEN_COMMIT"
