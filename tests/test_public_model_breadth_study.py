from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_public_model_breadth_study as breadth_runner  # noqa: E402
from build_public_model_breadth_study import request_body  # noqa: E402
from finalize_public_model_breadth_study import missing_record  # noqa: E402
from validate_public_model_breadth_study import EXPECTED_MODELS, validate_study  # noqa: E402

from claimpromotebench.dataset import load_json, validate_with_schema  # noqa: E402

PLAN = ROOT / "v2" / "public-model-breadth-v1" / "study-plan.json"
SCHEDULE = ROOT / "v2" / "public-model-breadth-v1" / "request-schedule.json"
PACKET = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def test_public_model_breadth_freeze_validates_without_credentials() -> None:
    result = validate_study(PLAN, SCHEDULE, PACKET)
    assert result["status"] == "PUBLIC_MODEL_BREADTH_FREEZE_VALID"
    assert result["models"] == 7
    assert result["items"] == 180
    assert result["cells"] == 1260
    assert result["credentials_loaded"] is False


def test_every_lane_uses_the_same_prompt_only_body_shape() -> None:
    plan = load_json(PLAN)
    packet = load_json(PACKET)
    prompt = packet["records"][0]["prompt"]
    for lane in plan["formal_lanes"]:
        body = request_body(lane, prompt)
        assert set(body) == {"model", "max_tokens", "messages", "stream"}
        assert body["messages"] == [{"role": "user", "content": prompt}]
        assert body["max_tokens"] == 1536
        assert body["stream"] is False


def test_schedule_rotates_lane_position_and_covers_each_cell_once() -> None:
    schedule = load_json(SCHEDULE)
    lanes = schedule["base_lane_order"]
    cells = schedule["cells"]
    assert len({row["cell_id"] for row in cells}) == 1260
    assert Counter(row["lane_id"] for row in cells) == Counter({lane: 180 for lane in lanes})
    for item_index in range(180):
        block = cells[item_index * 7 : (item_index + 1) * 7]
        rotation = item_index % 7
        assert [row["lane_id"] for row in block] == lanes[rotation:] + lanes[:rotation]
        assert len({row["item_id"] for row in block}) == 1


def test_catalog_selection_is_model_output_independent_and_new_for_this_challenge() -> None:
    catalog = load_json(ROOT / "v2" / "public-model-breadth-v1" / "catalog-snapshot.json")
    assert tuple(catalog["selected_model_ids"]) == EXPECTED_MODELS
    assert catalog["account_identifiers_retained"] is False
    assert catalog["provider_response_identifiers_retained"] is False
    assert not set(EXPECTED_MODELS) & {"qwen3.7-max", "deepseek-v4-flash"}


def test_interruption_record_is_schema_valid_and_incorrect_by_construction() -> None:
    plan = load_json(PLAN)
    plan["_frozen_plan_commit"] = "0" * 40
    packet = load_json(PACKET)
    schedule = load_json(SCHEDULE)
    cell = schedule["cells"][0]
    lane = {row["lane_id"]: row for row in plan["formal_lanes"]}[cell["lane_id"]]
    record = missing_record(
        plan,
        packet,
        lane,
        cell,
        request_started="2026-08-22T20:00:00Z",
        sealed_at="2026-08-22T20:01:00Z",
        error="NOT_ATTEMPTED_AFTER_EXECUTION_INTERRUPTION_NO_RESUME",
    )
    validate_with_schema(record, RUN_SCHEMA, cell["cell_id"])
    assert record["transport_status"] == "ERROR"
    assert record["parse_status"] == "TRANSPORT_ERROR"
    assert record["raw_decision"] is None


def test_openai_adapter_keeps_only_final_text_and_nonidentifying_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        breadth_runner,
        "_http_json",
        lambda *args, **kwargs: {
            "id": "provider-response-id-must-not-propagate",
            "model": "glm-5.3",
            "provider": "example-route",
            "choices": [
                {
                    "message": {
                        "content": '{"action":"HOLD"}',
                        "reasoning_content": "private reasoning must be ignored",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 4,
                "total_tokens": 14,
            },
        },
    )
    lane = load_json(PLAN)["formal_lanes"][2]
    metadata, content, usage = breadth_runner.call_openai_compatible(
        lane, request_body(lane, "prompt"), "test-key", 1.0
    )
    assert content == '{"action":"HOLD"}'
    assert metadata == {
        "model_returned": "glm-5.3",
        "routed_provider": "example-route",
        "finish_reason": "stop",
    }
    assert usage["total_tokens"] == 14


def test_anthropic_adapter_discards_nontext_blocks(monkeypatch) -> None:
    monkeypatch.setattr(
        breadth_runner,
        "_http_json",
        lambda *args, **kwargs: {
            "id": "provider-response-id-must-not-propagate",
            "model": "qwen3.8-max",
            "content": [
                {"type": "thinking", "thinking": "private reasoning must be ignored"},
                {"type": "text", "text": '{"action":"ALLOW"}'},
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 5},
        },
    )
    lane = load_json(PLAN)["formal_lanes"][0]
    metadata, content, usage = breadth_runner.call_anthropic_messages(
        lane, request_body(lane, "prompt"), "test-key", 1.0
    )
    assert content == '{"action":"ALLOW"}'
    assert metadata["model_returned"] == "qwen3.8-max"
    assert metadata["finish_reason"] == "end_turn"
    assert usage["total_tokens"] == 17


def test_sanitizer_removes_credentials_and_provider_ids() -> None:
    value = 'request_id="abc-123" credential-secret user_Aa12345678901234567890'
    cleaned = breadth_runner.sanitize_text(value, "credential-secret")
    assert cleaned is not None
    assert "credential-secret" not in cleaned
    assert "abc-123" not in cleaned
    assert "user_Aa12345678901234567890" not in cleaned


def test_openai_adapter_turns_malformed_message_into_a_terminal_error(monkeypatch) -> None:
    monkeypatch.setattr(
        breadth_runner,
        "_http_json",
        lambda *args, **kwargs: {"choices": [{"message": ["not", "an", "object"]}]},
    )
    lane = load_json(PLAN)["formal_lanes"][2]
    with pytest.raises(RuntimeError, match=r"choices\[0\]\.message"):
        breadth_runner.call_openai_compatible(lane, request_body(lane, "prompt"), "test-key", 1.0)


def test_atomic_output_publication_preserves_finalizer_path_on_failure(tmp_path: Path) -> None:
    complete = tmp_path / "complete"
    with breadth_runner.atomic_output_directory(complete) as staging:
        (staging / "receipt.json").write_text("complete\n", encoding="utf-8")
    assert (complete / "receipt.json").read_text(encoding="utf-8") == "complete\n"

    interrupted = tmp_path / "interrupted"
    with (
        pytest.raises(RuntimeError, match="simulated interruption"),
        breadth_runner.atomic_output_directory(interrupted) as staging,
    ):
        (staging / "partial.json").write_text("partial\n", encoding="utf-8")
        raise RuntimeError("simulated interruption")
    assert not interrupted.exists()
    assert list(tmp_path.glob(".interrupted.building-*"))
