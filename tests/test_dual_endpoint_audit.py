from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_builder() -> ModuleType:
    path = ROOT / "scripts" / "build_dual_endpoint_audit.py"
    spec = importlib.util.spec_from_file_location("build_dual_endpoint_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_strict_action_extraction_rejects_repairs_and_duplicate_keys() -> None:
    module = load_builder()
    assert module.strict_json_action('{"action":"ALLOW"}') == "ALLOW"
    assert module.strict_json_action('```json\n{"action":"ALLOW"}\n```') is None
    assert module.strict_json_action('{"action":"ALLOW","action":"HOLD"}') is None
    assert module.strict_json_action('{"action":1}') is None
    assert module.strict_json_action('{"action":"allow"}') is None


def test_dual_endpoints_separate_action_from_contract() -> None:
    module = load_builder()
    gold = [
        {"id": "a", "decision": {"action": "ALLOW"}},
        {"id": "b", "decision": {"action": "HOLD"}},
    ]
    pairs = [{"pair_id": "p", "member_ids": ["a", "b"]}]
    records = [
        {
            "item_id": "a",
            "pair_id": "p",
            "parse_status": "OK",
            "raw_decision": {"action": "ALLOW"},
            "raw_response_text": '{"action":"ALLOW"}',
        },
        {
            "item_id": "b",
            "pair_id": "p",
            "parse_status": "SEMANTIC_ERROR",
            "raw_decision": None,
            "raw_response_text": '{"action":"HOLD","proposed_state":{}}',
        },
    ]
    result = module.derive_metrics(gold, pairs, records)
    assert result["raw_strict_action"]["correct_items"] == 2
    assert result["raw_strict_action"]["correct_pairs"] == 1
    assert result["registered_parser_action"]["correct_items"] == 1
    assert result["registered_parser_action"]["correct_pairs"] == 0
    assert result["full_contract"]["action_correct_items"] == 1
    assert result["full_contract"]["action_correct_pairs"] == 0
    assert result["endpoint_overlap"] == {
        "raw_strict_extractable_outside_full_contract": 1,
        "raw_strict_correct_items_outside_full_contract": 1,
        "raw_strict_correct_pairs_outside_full_contract": 1,
        "full_contract_extractable_outside_raw_strict": 0,
        "full_contract_correct_items_outside_raw_strict": 0,
        "full_contract_correct_pairs_outside_raw_strict": 0,
    }


def test_parser_provenance_keeps_fence_extraction_out_of_raw_strict() -> None:
    module = load_builder()
    record = {
        "item_id": "a",
        "parse_status": "OK",
        "raw_decision": {"action": "ALLOW"},
        "raw_response_text": '```json\n{"action":"ALLOW"}\n```',
        "parse_error_detail": "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION",
    }
    assert module.raw_strict_action(record) == (None, "RAW_STRICT_REJECTED")
    assert module.registered_parser_action(record) == (
        "ALLOW",
        "REGISTERED_SINGLE_OBJECT_EXTRACTION",
    )


def test_committed_dual_endpoint_audit_rebuilds() -> None:
    module = load_builder()
    aggregate = module.load_json(module.STUDY_ROOT / "aggregate.json")
    assert aggregate["status"] == "COMPLETE_POST_HOC_DUAL_ENDPOINT_AUDIT"
    assert len(aggregate["routes"]) == 10


def test_committed_dual_endpoint_audit_validates() -> None:
    path = ROOT / "scripts" / "validate_dual_endpoint_audit.py"
    spec = importlib.util.spec_from_file_location("validate_dual_endpoint_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate() == {
        "route_stacks": 10,
        "scheduled_items": 1320,
        "raw_strict_correct_outside_contract": 49,
        "raw_strict_correct_pairs_outside_contract": 40,
        "contract_correct_outside_raw_strict": 329,
        "contract_correct_pairs_outside_raw_strict": 78,
    }
