"""Regression tests for the post-review capable-model hidden extension."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_json

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "v2" / "capable-hidden-study-plan.json"


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capable_hidden_plan_is_frozen_before_new_outputs() -> None:
    validator = _load_script("validate_stronger_model_study")
    plan = load_json(PLAN)
    lanes, formal_ids = validator.validate_plan(plan)

    assert plan["status"] == "FROZEN_BEFORE_SCORED_INFERENCE"
    assert plan["truth_status"] == "OPEN"
    assert plan["amendment"]["new_model_outputs_seen_before_initial_freeze"] is False
    assert plan["transport_amendment"]["status"] == "FROZEN_BEFORE_REEXECUTION"
    assert plan["amendment"]["new_hidden_items_or_labels_created"] is False
    assert plan["dataset"]["instances"] == 300
    assert plan["dataset"]["pairs"] == 150
    assert plan["prompt"]["expected_packet_sha256"] is None
    assert plan["prompt"]["packet_binding"] == ("FROZEN_DATASET_PLUS_DETERMINISTIC_RENDERER")
    assert set(plan["routing"]["required_full_lanes"]) == formal_ids
    assert len(formal_ids) == 7
    assert plan["budget"]["incremental_cash_cap_usd"] == 0.0
    assert plan["budget"]["use_zen_balance_after_go_limit"] is False

    assert lanes["bai-deepseek-v4-flash-primary"]["spend_cap_usd"] == 0.0
    assert lanes["bai-deepseek-v4-flash-primary"]["response_format"] == "json_object"
    assert lanes["bai-deepseek-v4-flash-primary"]["minimum_request_interval_seconds"] == 12.0
    assert lanes["bai-deepseek-v4-flash-primary"]["comparison_group"] == (
        "CROSS_SERVICE_REPLICATION_ONLY"
    )
    assert lanes["opencode-go-deepseek-v4-pro"]["comparison_group"] == (
        "OPENCODE_GO_DEEPSEEK_PRO_FLASH_SAME_INTERFACE"
    )
    assert lanes["opencode-go-deepseek-v4-flash-matched"]["comparison_group"] == (
        "OPENCODE_GO_DEEPSEEK_PRO_FLASH_SAME_INTERFACE"
    )
    assert lanes["opencode-go-muse-spark-1.2-contributor"]["data_training"] is True
    assert (
        "not a strict causal ablation"
        in plan["routing"]["deepseek_pro_flash_tier_comparison_rule"].lower()
    )


def test_capable_hidden_request_shapes_use_native_structured_output() -> None:
    runner = _load_script("run_stronger_model_study")
    plan = load_json(PLAN)
    lanes = {row["lane_id"]: row for row in plan["formal_lanes"]}
    schema = runner.provider_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )

    qwen = runner.anthropic_request_body(lanes["opencode-go-qwen3.7-max"], "prompt", schema)
    assert qwen["tool_choice"] == {"type": "tool", "name": "submit_decision"}
    assert qwen["tools"][0]["input_schema"] == schema
    assert qwen["max_tokens"] == 1536

    glm = runner.openai_request_body(lanes["opencode-go-glm-5.2"], "prompt", schema)
    assert glm["response_format"]["type"] == "json_schema"
    assert "reasoning_effort" not in glm

    muse = runner.responses_request_body(
        lanes["opencode-go-muse-spark-1.2-contributor"], "prompt", schema
    )
    assert muse["text"]["format"]["type"] == "json_schema"
    assert muse["text"]["format"]["strict"] is True
    assert muse["max_output_tokens"] == 1536


def test_new_adapters_keep_final_output_and_drop_reasoning() -> None:
    runner = _load_script("run_stronger_model_study")
    plan = load_json(PLAN)
    lanes = {row["lane_id"]: row for row in plan["formal_lanes"]}

    def fake_anthropic(*_args: object, **_kwargs: object) -> dict:
        return {
            "id": "msg-1",
            "model": "qwen3.7-max",
            "stop_reason": "tool_use",
            "content": [
                {"type": "thinking", "thinking": "must not be retained"},
                {
                    "type": "tool_use",
                    "name": "submit_decision",
                    "input": {"action": "HOLD"},
                },
            ],
            "usage": {"input_tokens": 20, "output_tokens": 5},
        }

    runner._http_json = fake_anthropic
    metadata, content, usage = runner.call_anthropic_messages(
        lanes["opencode-go-qwen3.7-max"], {}, "secret", 1.0
    )
    assert metadata["provider_response_id"] == "msg-1"
    assert content == '{"action": "HOLD"}'
    assert usage["reasoning_tokens"] is None
    assert "thinking" not in content

    def fake_responses(*_args: object, **_kwargs: object) -> dict:
        return {
            "id": "resp-1",
            "model": "muse-spark-1.2-contributor",
            "status": "completed",
            "output": [
                {"type": "reasoning", "summary": "must not be retained"},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"action":"ALLOW"}'}],
                },
            ],
            "usage": {
                "input_tokens": 30,
                "output_tokens": 7,
                "total_tokens": 37,
                "output_tokens_details": {"reasoning_tokens": 2},
            },
        }

    runner._http_json = fake_responses
    metadata, content, usage = runner.call_openai_responses(
        lanes["opencode-go-muse-spark-1.2-contributor"], {}, "secret", 1.0
    )
    assert metadata["provider_response_id"] == "resp-1"
    assert content == '{"action":"ALLOW"}'
    assert usage["reasoning_tokens"] == 2
    assert "must not be retained" not in content


def test_api_key_validation_rejects_whitespace_and_control_bytes() -> None:
    runner = _load_script("run_stronger_model_study")

    assert runner.validate_api_key("sk-valid_123", "TEST_KEY") == "sk-valid_123"
    for invalid in (None, "", " sk-key", "sk-key\n", "sk-key\r", "sk-key\t"):
        try:
            runner.validate_api_key(invalid, "TEST_KEY")
        except SystemExit as exc:
            assert "credential" in str(exc)
        else:
            raise AssertionError(f"credential should have been rejected: {invalid!r}")


def test_aggregate_primary_tests_exclude_free_service_replication() -> None:
    aggregate = _load_script("aggregate_capable_hidden_study")
    assert "bai-deepseek-v4-flash-primary" not in aggregate.PRIMARY_LANES
    assert "opencode-go-deepseek-v4-flash-matched" in aggregate.PRIMARY_LANES
    assert len(aggregate.PRIMARY_LANES) == 6
