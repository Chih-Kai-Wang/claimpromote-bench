from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_builder() -> ModuleType:
    path = ROOT / "scripts" / "build_dual_endpoint_audit.py"
    spec = importlib.util.spec_from_file_location("build_dual_endpoint_audit_policy", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_strict_endpoint_rejects_fences_and_duplicate_keys() -> None:
    module = load_builder()
    assert module.strict_json_action('{"action":"ALLOW"}') == "ALLOW"
    assert module.strict_json_action('```json\n{"action":"ALLOW"}\n```') is None
    assert module.strict_json_action('{"action":"ALLOW","action":"HOLD"}') is None


def test_registered_parser_provenance_is_separate_from_raw_strict() -> None:
    module = load_builder()
    record = {
        "item_id": "example",
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
