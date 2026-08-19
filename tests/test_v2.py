from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.v2 import diagnose_decision, llama_response_format, summarize_pilot

ROOT = Path(__file__).resolve().parents[1]


def _model_decision(gold_decision: dict[str, object]) -> dict[str, object]:
    return {key: deepcopy(value) for key, value in gold_decision.items() if key != "minimal_missing_evidence"}


def test_llama_response_format_is_non_mutating() -> None:
    schema = load_json(ROOT / "schemas" / "agent-decision.schema.json")
    original = deepcopy(schema)
    response_format = llama_response_format(schema)
    assert schema == original
    assert response_format["type"] == "json_object"
    assert "$schema" not in response_format["schema"]
    assert "$id" not in response_format["schema"]
    assert response_format["schema"]["title"] == "AgentDecision"


def test_diagnose_decision_separates_failure_layers() -> None:
    item = load_jsonl(ROOT / "data" / "alpha" / "inputs.jsonl")[0]
    gold = load_jsonl(ROOT / "data" / "alpha" / "gold.jsonl")[0]
    schema_path = ROOT / "schemas" / "agent-decision.schema.json"
    valid = _model_decision(gold["decision"])

    status, parsed, detail = diagnose_decision(json.dumps(valid), item, schema_path=schema_path)
    assert status == "OK"
    assert parsed == valid
    assert detail is None

    status, parsed, detail = diagnose_decision("{not-json", item, schema_path=schema_path)
    assert status == "JSON_SYNTAX_ERROR"
    assert parsed is None
    assert detail

    missing_action = deepcopy(valid)
    missing_action.pop("action")
    status, parsed, detail = diagnose_decision(
        json.dumps(missing_action), item, schema_path=schema_path
    )
    assert status == "SCHEMA_ERROR"
    assert parsed is None
    assert detail

    semantically_invalid = deepcopy(valid)
    semantically_invalid["action"] = "ALLOW"
    status, parsed, detail = diagnose_decision(
        json.dumps(semantically_invalid), item, schema_path=schema_path
    )
    assert status == "SEMANTIC_ERROR"
    assert parsed is None
    assert detail


def test_summarize_pilot_reports_coverage_and_counterfactual_accuracy() -> None:
    gold = load_jsonl(ROOT / "data" / "alpha" / "gold.jsonl")[:2]
    pairs = load_json(ROOT / "data" / "alpha" / "pairs.json")[:1]
    decisions = [_model_decision(row["decision"]) for row in gold]
    records = [
        {
            "item_id": gold[index]["id"],
            "parse_status": "OK",
            "raw_decision": decision,
            "postgate_decision": decision,
        }
        for index, decision in enumerate(decisions)
    ]
    summary = summarize_pilot(gold, pairs, records)
    assert summary["decision_coverage"] == 1.0
    assert summary["raw_action_accuracy"] == 1.0
    assert summary["pair_coverage"] == 1.0
    assert summary["raw_pair_accuracy"] == 1.0
    assert summary["raw_flip_rate"] == 1.0

    records[0] = {
        "item_id": gold[0]["id"],
        "parse_status": "JSON_SYNTAX_ERROR",
        "raw_decision": None,
        "postgate_decision": None,
    }
    summary = summarize_pilot(gold, pairs, records)
    assert summary["decision_coverage"] == 0.5
    assert summary["pair_coverage"] == 0.0
    assert summary["raw_pair_accuracy"] is None
