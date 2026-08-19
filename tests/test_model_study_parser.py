"""Regression tests for semantic format handling in the frozen llama.cpp collector."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_jsonl

ROOT = Path(__file__).resolve().parents[1]


def _load_study_script() -> ModuleType:
    path = ROOT / "scripts" / "run_llama_study.py"
    spec = importlib.util.spec_from_file_location("run_llama_study", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _transition_item() -> dict:
    for item in load_jsonl(ROOT / "data" / "alpha" / "inputs.jsonl"):
        if item["requested_transition"]["target_state"] != item["current_state"]:
            return item
    raise AssertionError("alpha dataset contains no actual state transition")


def test_parse_decision_accepts_schema_and_semantic_valid_hold() -> None:
    script = _load_study_script()
    item = _transition_item()
    decision = {
        "action": "HOLD",
        "proposed_state": item["current_state"],
        "p_admissible": 0.5,
        "used_evidence_ids": [],
        "reason_codes": ["INSUFFICIENT_EVIDENCE"],
        "missing_evidence_ids": [],
    }
    assert script.parse_decision(json.dumps(decision), item) == decision


def test_parse_decision_rejects_schema_valid_semantically_invalid_allow() -> None:
    script = _load_study_script()
    item = _transition_item()
    decision = {
        "action": "ALLOW",
        "proposed_state": item["current_state"],
        "p_admissible": 0.5,
        "used_evidence_ids": [],
        "reason_codes": ["EVIDENCE_OK"],
        "missing_evidence_ids": [],
    }
    # The JSON is schema-valid, but ALLOW must propose the exact requested target.
    assert script.parse_decision(json.dumps(decision), item) is None
