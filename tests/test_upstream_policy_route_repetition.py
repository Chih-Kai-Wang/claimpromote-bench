from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openai_compatible_call as adapter  # noqa: E402
from analyze_upstream_policy_route_repetition import (  # noqa: E402
    FORBIDDEN_RESULT_KEYS,
    _walk_keys,
    sanitized_rows,
    summarize_slice,
)
from derive_upstream_route_repetition_failure_modes import (  # noqa: E402
    OUT_ROOT as FAILURE_MODE_ROOT,
)
from derive_upstream_route_repetition_failure_modes import (  # noqa: E402
    validate as validate_failure_modes,
)
from freeze_upstream_policy_route_repetition import build_schedule  # noqa: E402
from upstream_route_repetition import diagnose_response, lanes, request_body  # noqa: E402
from validate_upstream_policy_route_repetition import validate_freeze  # noqa: E402
from validate_upstream_policy_route_repetition_results import validate_results  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402

STUDY_ROOT = ROOT / "v2" / "upstream-policy-route-repetition-v1"
PACKET = ROOT / "v2" / "upstream-policy-revisions-v1" / "dataset" / "evaluation-prompt-packet.json"
PAIRS = ROOT / "v2" / "upstream-policy-revisions-v1" / "dataset" / "evaluation-pairs.json"


def valid_allow() -> dict[str, object]:
    return {
        "action": "ALLOW",
        "violation_count": 0,
        "subject": {"kind": "Pod", "namespace": "apps", "name": "web"},
        "rule_id": "NONE",
        "witnesses": [],
    }


def test_strict_response_parser_rejects_repair_and_duplicate_keys() -> None:
    status, action, decision, detail = diagnose_response('{"action":"ALLOW","action":"HOLD"}')
    assert status == "JSON_SYNTAX_ERROR"
    assert action is None
    assert decision is None
    assert detail is not None and "duplicate JSON key" in detail

    status, action, decision, _ = diagnose_response('```json\n{"action":"ALLOW"}\n```')
    assert (status, action, decision) == ("JSON_SYNTAX_ERROR", None, None)


def test_action_endpoint_survives_schema_failure_but_contract_endpoint_does_not() -> None:
    status, action, decision, _ = diagnose_response('{"action":"ALLOW"}')
    assert status == "SCHEMA_ERROR"
    assert action == "ALLOW"
    assert decision is None

    malformed = valid_allow()
    malformed["violation_count"] = 1
    status, action, decision, _ = diagnose_response(__import__("json").dumps(malformed))
    assert status == "SEMANTIC_ERROR"
    assert action == "ALLOW"
    assert decision is None


def test_valid_contract_decision_is_retained() -> None:
    status, action, decision, detail = diagnose_response(__import__("json").dumps(valid_allow()))
    assert status == "OK"
    assert action == "ALLOW"
    assert decision == valid_allow()
    assert detail is None


def test_adapter_discards_response_ids_and_hidden_reasoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "_http_json",
        lambda *args, **kwargs: {
            "id": "provider-response-id",
            "model": "qwen3.7-max",
            "provider": "example-route",
            "choices": [
                {
                    "message": {
                        "content": '{"action":"ALLOW"}',
                        "reasoning_content": "private reasoning",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        },
    )
    lane = lanes()[0]
    metadata, content, usage = adapter.call_openai_compatible(
        lane, request_body(lane, "prompt"), "test-key", 1.0
    )
    assert metadata == {
        "model_returned": "qwen3.7-max",
        "routed_provider": "example-route",
        "finish_reason": "stop",
    }
    assert content == '{"action":"ALLOW"}'
    assert usage["total_tokens"] == 14
    assert "provider-response-id" not in str((metadata, content, usage))
    assert "private reasoning" not in str((metadata, content, usage))


def test_schedule_interleaves_two_lanes_and_repeats_exact_requests() -> None:
    packet = load_json(PACKET)
    plan = {"formal_lanes": [dict(row) for row in lanes()]}
    schedule = build_schedule(plan, packet)
    cells = schedule["cells"]
    lane_ids = [row["lane_id"] for row in plan["formal_lanes"]]
    assert len(cells) == 144
    assert Counter(row["lane_id"] for row in cells) == Counter({lane: 72 for lane in lane_ids})
    assert Counter(row["repetition"] for row in cells) == Counter({1: 48, 2: 48, 3: 48})
    for repetition in range(1, 4):
        repetition_cells = [row for row in cells if row["repetition"] == repetition]
        for item_index in range(24):
            block = repetition_cells[item_index * 2 : (item_index + 1) * 2]
            rotation = (item_index + repetition - 1) % 2
            assert [row["lane_id"] for row in block] == lane_ids[rotation:] + lane_ids[:rotation]
            assert len({row["item_id"] for row in block}) == 1
    request_hashes: dict[tuple[str, str], set[str]] = {}
    for row in cells:
        key = (row["lane_id"], row["item_id"])
        request_hashes.setdefault(key, set()).add(row["request_body_sha256"])
    assert all(len(values) == 1 for values in request_hashes.values())


def test_all_failures_remain_in_endpoint_denominators() -> None:
    pairs = load_json(PAIRS)
    assert isinstance(pairs, list)
    rows: list[dict[str, object]] = []
    for pair in pairs:
        for item_id in pair["member_ids"]:
            rows.append(
                {
                    "item_id": item_id,
                    "repetition": 1,
                    "gold_action": "ALLOW",
                    "action_extraction_status": "UNEXTRACTABLE",
                    "transport_status": "ERROR",
                    "parse_status": "TRANSPORT_ERROR",
                    "strict_action_correct": False,
                    "contract_action_correct": False,
                    "full_decision_exact": False,
                    "usage": {
                        "input_tokens": None,
                        "cached_input_tokens": None,
                        "output_tokens": None,
                        "reasoning_tokens": None,
                        "total_tokens": None,
                    },
                }
            )
    summary = summarize_slice(rows, pairs)
    assert summary["strict_action"]["accuracy"] == {
        "numerator": 0,
        "denominator": 24,
        "value": 0.0,
    }
    assert summary["contract_action"]["accuracy"]["denominator"] == 24
    assert summary["full_decision_exact"]["accuracy"]["denominator"] == 24
    assert summary["pair_accuracy"]["strict_action"]["denominator"] == 12


def test_sanitized_rows_exclude_raw_content_and_diagnostics() -> None:
    row = {
        "lane_id": "lane",
        "model_requested": "model",
        "repetition": 1,
        "sequence": 0,
        "cell_id": "cell",
        "item_id": "item",
        "pair_id": "pair",
        "gold_action": "ALLOW",
        "transport_status": "ERROR",
        "action_extraction_status": "UNEXTRACTABLE",
        "extracted_action": None,
        "parse_status": "TRANSPORT_ERROR",
        "strict_action_correct": False,
        "contract_action_correct": False,
        "full_decision_exact": False,
        "raw_response_text": "private invalid content",
        "transport_error": "private provider detail",
    }
    public = sanitized_rows([row])["lane-r1.jsonl"][0]
    assert not (FORBIDDEN_RESULT_KEYS & _walk_keys(public))
    assert "private invalid content" not in str(public)
    assert "private provider detail" not in str(public)


def test_committed_freeze_validates_without_credentials() -> None:
    if not (STUDY_ROOT / "study-plan.json").exists():
        pytest.skip("preinference freeze has not been generated yet")
    report = validate_freeze()
    assert report["status"] == "UPSTREAM_ROUTE_REPETITION_FREEZE_VALID"
    assert report["planned_calls"] == 144
    assert report["credentials_loaded"] is False


def test_committed_results_recompute_without_credentials() -> None:
    if not (STUDY_ROOT / "results" / "manifest.json").exists():
        pytest.skip("route-repetition results have not been generated yet")
    report = validate_results()
    assert report["status"] == "UPSTREAM_ROUTE_REPETITION_RESULTS_VALID"
    assert report["scheduled_cells"] == 144
    assert report["credentials_loaded"] is False


def test_content_free_failure_modes_recompute_without_credentials() -> None:
    if not (FAILURE_MODE_ROOT / "manifest.json").exists():
        pytest.skip("content-free failure-mode diagnostic has not been generated yet")
    report = validate_failure_modes()
    assert report["status"] == "UPSTREAM_ROUTE_REPETITION_FAILURE_MODES_VALID"
    assert report["scheduled_cells"] == 144
    assert report["credentials_loaded"] is False
