"""Regression tests for the frozen stronger-model public-dev follow-up."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.dataset import load_json, load_jsonl, write_jsonl
from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "v2" / "stronger-model-study-plan.json"
OPENROUTER_AMENDMENT = ROOT / "v2" / "stronger-model-openrouter-amendment.json"
OPENROUTER_AMENDMENT_V2 = ROOT / "v2" / "stronger-model-openrouter-amendment-v2.json"


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def stronger_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset = tmp_path_factory.mktemp("stronger-model-study") / "dev"
    builder = _load_script("build_v1_dataset")
    report = builder.build("dev", dataset, None)
    assert report["manifest_sha256"] == (
        "sha256:d04b2458ec34bafb2a818c720d6b85131c27d80c1d182b8911aa106c1ba2f014"
    )
    return dataset


def test_packet_build_is_deterministic_and_model_output_independent(
    stronger_dataset: Path,
) -> None:
    builder = _load_script("build_stronger_model_packet")
    packet_a = builder.build_packet(stronger_dataset, PLAN)
    packet_b = builder.build_packet(stronger_dataset, PLAN)
    assert packet_a == packet_b
    assert len(packet_a["records"]) == 100
    assert len(packet_a["pilot_item_ids"]) == 12
    assert packet_a["selection_uses_model_outputs"] is False
    assert packet_a["pilot_pair_ids"] == [
        "v1-dev-dep-001",
        "v1-dev-formal-001",
        "v1-dev-num-001",
        "v1-dev-prov-001",
        "v1-dev-run-001",
        "v1-dev-stale-001",
    ]


def test_provider_schema_is_flattened_for_strict_output_modes() -> None:
    runner = _load_script("run_stronger_model_study")
    schema = runner.provider_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )
    assert "$schema" not in schema
    assert "$id" not in schema
    assert "$defs" not in schema
    assert schema["properties"]["proposed_state"]["type"] == "object"
    assert "$ref" not in schema["properties"]["proposed_state"]
    assert "minimum" not in schema["properties"]["p_admissible"]
    assert "maximum" not in schema["properties"]["p_admissible"]
    assert "uniqueItems" not in schema["properties"]["reason_codes"]
    assert "pattern" not in schema["properties"]["reason_codes"]["items"]


def test_provider_request_bodies_freeze_interface_specific_controls() -> None:
    runner = _load_script("run_stronger_model_study")
    plan = load_json(PLAN)
    schema = runner.provider_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )
    lanes = {row["lane_id"]: row for row in plan["formal_lanes"]}

    openai = runner.openai_request_body(lanes["openai-gpt-5.4-api"], "prompt", schema)
    assert openai["max_completion_tokens"] == 3072
    assert "max_tokens" not in openai
    assert openai["response_format"]["type"] == "json_schema"

    deepseek = runner.openai_request_body(lanes["deepseek-v4-pro-api"], "prompt", schema)
    assert deepseek["max_tokens"] == 4096
    assert deepseek["thinking"] == {"type": "enabled"}
    assert deepseek["response_format"] == {"type": "json_object"}

    gemini = runner.gemini_request_body(lanes["google-gemini-3.7-flash-api"], "prompt", schema)
    config = gemini["generationConfig"]
    assert config["thinkingConfig"] == {"thinkingLevel": "high"}
    assert config["maxOutputTokens"] == 2048
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == schema

    amendment = load_json(OPENROUTER_AMENDMENT)
    openrouter = amendment["formal_lanes"][0]
    routed = runner.openai_request_body(openrouter, "prompt", schema)
    assert routed["model"] == "openai/gpt-5.4"
    assert routed["max_completion_tokens"] == 3072
    assert "max_tokens" not in routed
    assert routed["provider"] == {
        "order": ["openai"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }

    amendment_v2 = load_json(OPENROUTER_AMENDMENT_V2)
    revised_lane = amendment_v2["formal_lanes"][0]
    revised = runner.openai_request_body(revised_lane, "prompt", schema)
    assert revised["max_tokens"] == 3072
    assert "max_completion_tokens" not in revised
    assert revised["provider"] == {
        "order": ["openai"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "max_price": {"prompt": 2.5, "completion": 15.0},
    }


def test_adapters_retain_final_text_and_usage_but_not_hidden_reasoning() -> None:
    runner = _load_script("run_stronger_model_study")
    plan = load_json(PLAN)
    lanes = {row["lane_id"]: row for row in plan["formal_lanes"]}

    def fake_openai(*_args: object, **_kwargs: object) -> dict:
        return {
            "id": "response-1",
            "model": "deepseek-v4-pro",
            "provider": "OpenAI",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"action":"HOLD"}',
                        "reasoning_content": "must never be retained",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 22,
                "total_tokens": 33,
                "completion_tokens_details": {"reasoning_tokens": 17},
            },
        }

    runner._http_json = fake_openai
    metadata, content, usage = runner.call_openai_compatible(
        lanes["deepseek-v4-pro-api"], {"request": "body"}, "secret", 1.0
    )
    assert metadata["provider_response_id"] == "response-1"
    assert metadata["routed_provider"] == "OpenAI"
    assert content == '{"action":"HOLD"}'
    assert usage["reasoning_tokens"] == 17
    assert "reasoning_content" not in metadata
    assert "reasoning_content" not in usage

    def fake_gemini(*_args: object, **_kwargs: object) -> dict:
        return {
            "responseId": "response-2",
            "modelVersion": "gemini-3.7-flash",
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"thought": True, "text": "must never be retained"},
                            {"text": '{"action":"ALLOW"}'},
                        ]
                    },
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
                "thoughtsTokenCount": 20,
                "totalTokenCount": 35,
            },
        }

    runner._http_json = fake_gemini
    metadata, content, usage = runner.call_gemini(
        lanes["google-gemini-3.7-flash-api"], {"request": "body"}, "secret", 1.0
    )
    assert metadata["provider_response_id"] == "response-2"
    assert content == '{"action":"ALLOW"}'
    assert usage["reasoning_tokens"] == 20


def test_conservative_cost_bound_and_host_usage_costs() -> None:
    runner = _load_script("run_stronger_model_study")
    plan = load_json(PLAN)
    lanes = {row["lane_id"]: row for row in plan["formal_lanes"]}
    rows = [{"utf8_bytes": 9}, {"utf8_bytes": 10}]
    deepseek = lanes["deepseek-v4-pro-api"]
    observed_bound = runner.conservative_upper_bound_usd(rows, deepseek)
    expected_bound = ((5 + 5) * 0.435 + (2 * deepseek["max_output_tokens"]) * 0.87) / 1_000_000
    assert math.isclose(observed_bound, expected_bound, rel_tol=0.0, abs_tol=1e-15)

    usage = {
        "input_tokens": 1000,
        "cached_input_tokens": 100,
        "output_tokens": 500,
        "reasoning_tokens": 400,
        "total_tokens": 1900,
    }
    observed_deepseek = runner.actual_cost_usd(usage, deepseek)
    expected_deepseek = (900 * 0.435 + 100 * 0.003625 + 500 * 0.87) / 1_000_000
    assert math.isclose(observed_deepseek, expected_deepseek, rel_tol=0.0, abs_tol=1e-15)

    gemini = lanes["google-gemini-3.7-flash-api"]
    observed_gemini = runner.actual_cost_usd(usage, gemini)
    expected_gemini = (900 * 0.75 + 100 * 0.075 + 900 * 3.75) / 1_000_000
    assert math.isclose(observed_gemini, expected_gemini, rel_tol=0.0, abs_tol=1e-15)


def test_pilot_gate_cannot_depend_on_accuracy_or_action_distribution() -> None:
    analyzer = _load_script("analyze_stronger_model_study")
    always_allow = [
        {"transport_status": "OK", "parse_status": "OK", "raw_decision": {"action": "ALLOW"}}
        for _ in range(12)
    ]
    always_hold = [
        {"transport_status": "OK", "parse_status": "OK", "raw_decision": {"action": "HOLD"}}
        for _ in range(12)
    ]
    assert analyzer.pilot_gate(always_allow) == analyzer.pilot_gate(always_hold)
    assert analyzer.pilot_gate(always_allow)["decision"] == "GO"
    assert analyzer.pilot_gate(always_allow)["accuracy_used_by_gate"] is False
    assert analyzer.pilot_gate(always_allow)["action_distribution_used_by_gate"] is False

    two_format_errors = [
        *always_allow[:10],
        *({"transport_status": "OK", "parse_status": "SCHEMA_ERROR"} for _ in range(2)),
    ]
    assert analyzer.pilot_gate(two_format_errors)["decision"] == "GO"
    one_transport_error = [
        *always_allow[:11],
        {"transport_status": "ERROR", "parse_status": "TRANSPORT_ERROR"},
    ]
    assert analyzer.pilot_gate(one_transport_error)["decision"] == "STOP"


def test_analyzer_accepts_complete_bound_pilot_and_reports_uncertainty(
    tmp_path: Path,
    stronger_dataset: Path,
) -> None:
    builder = _load_script("build_stronger_model_packet")
    analyzer = _load_script("analyze_stronger_model_study")
    packet = builder.build_packet(stronger_dataset, PLAN)
    plan = load_json(PLAN)
    gold_by_id = {str(row["id"]): row for row in load_jsonl(stronger_dataset / "gold.jsonl")}
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    records = []
    for item_id in packet["pilot_item_ids"]:
        gold_decision = dict(gold_by_id[item_id]["decision"])
        gold_decision.pop("minimal_missing_evidence")
        raw = canonical_json(gold_decision)
        records.append(
            {
                "schema_version": "1.0.0",
                "study_id": plan["study_id"],
                "frozen_plan_commit": "0" * 40,
                "packet_sha256": packet["packet_sha256"],
                "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
                "phase": "pilot",
                "lane_id": "deepseek-v4-pro-api",
                "provider": "DeepSeek",
                "model_requested": "deepseek-v4-pro",
                "model_returned": "deepseek-v4-pro",
                "model_family": "DeepSeek",
                "item_id": item_id,
                "pair_id": packet_by_id[item_id]["pair_id"],
                "request_sha256": "sha256:" + "1" * 64,
                "prompt_sha256": packet_by_id[item_id]["prompt_sha256"],
                "response_format_sha256": "sha256:" + "2" * 64,
                "provider_response_id": f"response-{item_id}",
                "system_fingerprint": None,
                "finish_reason": "stop",
                "request_started_at_utc": "2026-08-20T00:00:00Z",
                "response_received_at_utc": "2026-08-20T00:00:01Z",
                "transport_status": "OK",
                "transport_error": None,
                "raw_response_text": raw,
                "raw_response_sha256": sha256_bytes(raw.encode("utf-8")),
                "parse_status": "OK",
                "parse_error_detail": None,
                "raw_decision": gold_decision,
                "postgate_decision": gold_decision,
                "latency_ms": 1000.0,
                "usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 0,
                    "output_tokens": 50,
                    "reasoning_tokens": 25,
                    "total_tokens": 150,
                },
                "actual_cost_usd": 0.0001,
                "cost_status": "COMPUTED_FROM_HOST_USAGE",
                "evidence_ceiling": "COMPUTATIONAL",
            }
        )
    run_path = tmp_path / "pilot.jsonl"
    write_jsonl(run_path, records)
    result = analyzer.analyze(stronger_dataset, packet, plan, run_path)
    assert result["continuation_gate"]["decision"] == "GO"
    assert result["metrics"]["raw_action_accuracy"] == 1.0
    assert result["uncertainty"]["raw_action_accuracy"]["successes"] == 12
    assert result["uncertainty"]["raw_action_accuracy"]["trials"] == 12
    assert result["raw_prompts_or_responses_in_aggregate"] is False
    json.dumps(result)


def test_registered_paid_lane_caps_do_not_exceed_ten_dollars() -> None:
    validator = _load_script("validate_stronger_model_study")
    plan = load_json(PLAN)
    lanes, formal_ids = validator.validate_plan(plan)
    assert math.isclose(
        sum(float(lanes[lane_id]["spend_cap_usd"]) for lane_id in formal_ids),
        10.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_openrouter_amendment_is_separate_and_pins_one_upstream() -> None:
    validator = _load_script("validate_stronger_model_study")
    amendment = load_json(OPENROUTER_AMENDMENT)
    lanes, formal_ids = validator.validate_plan(amendment)

    assert amendment["amendment"]["base_plan_sha256"] == (
        "sha256:e83df93b598032627e4ce5a59189780d5ae57538d4fc8e98173b1343da07ff0d"
    )
    assert amendment["amendment"]["created_after_base_pilot_outcomes_known"] is True
    assert amendment["amendment"]["openrouter_outputs_seen_before_freeze"] is False
    assert amendment["amendment"]["official_openai_lane_replaced"] is False
    assert formal_ids == {"openrouter-openai-gpt-5.4"}
    lane = lanes["openrouter-openai-gpt-5.4"]
    assert lane["provider_routing"]["order"] == ["openai"]
    assert lane["provider_routing"]["allow_fallbacks"] is False
    assert lane["required_routed_provider"] == "OpenAI"
    assert amendment["exploratory_lanes"] == []
    assert float(lane["spend_cap_usd"]) == 8.0


def test_openrouter_v2_amendment_preserves_failed_v1_and_fixes_only_interface() -> None:
    validator = _load_script("validate_stronger_model_study")
    amendment = load_json(OPENROUTER_AMENDMENT_V2)
    lanes, formal_ids = validator.validate_plan(amendment)

    lineage = amendment["amendment"]
    assert lineage["openrouter_v1_plan_sha256"] == (
        "sha256:57ba2c63ca53890b3c90844961149dc70dcd30cb2c00ddb6d7f87c266b225ef4"
    )
    assert lineage["openrouter_v1_run_sha256"] == (
        "sha256:a7154c939a040150dde4d23408ed70a131033ae05c674ec0a830974cba26abc5"
    )
    assert lineage["openrouter_v1_gate"] == "STOP"
    assert lineage["openrouter_v1_transport_errors"] == 12
    assert lineage["v1_transport_failure_informed_interface_revision"] is True
    assert lineage["v2_outputs_seen_before_freeze"] is False
    assert formal_ids == {"openrouter-openai-gpt-5.4-max-tokens"}
    lane = lanes["openrouter-openai-gpt-5.4-max-tokens"]
    assert lane["max_output_parameter"] == "max_tokens"
    assert lane["provider_routing"]["order"] == ["openai"]
    assert lane["provider_routing"]["allow_fallbacks"] is False
    assert lane["provider_routing"]["max_price"] == {
        "prompt": 2.5,
        "completion": 15.0,
    }
    assert lane["required_routed_provider"] == "OpenAI"


def test_routed_provider_is_required_only_after_transport_success() -> None:
    validator = _load_script("validate_stronger_model_study")
    lane = {"required_routed_provider": "OpenAI"}

    validator.validate_required_routed_provider(
        {"transport_status": "ERROR", "routed_provider": None}, lane, "failed"
    )
    validator.validate_required_routed_provider(
        {"transport_status": "OK", "routed_provider": "OpenAI"}, lane, "ok"
    )
    with pytest.raises(SystemExit, match="routed provider mismatch"):
        validator.validate_required_routed_provider(
            {"transport_status": "OK", "routed_provider": "Azure"},
            lane,
            "wrong",
        )
