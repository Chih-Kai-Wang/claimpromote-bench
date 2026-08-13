from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator

from claimpromotebench.dataset import load_json, validate_with_schema


def test_all_schemas_are_draft_2020_12_valid(root) -> None:
    for path in sorted((root / "schemas").glob("*.schema.json")):
        Draft202012Validator.check_schema(load_json(path))


def test_run_record_requires_decisions_for_success(root) -> None:
    schema = root / "schemas" / "run-record.schema.json"
    base = {
        "item_id": "alpha-dep-01-a",
        "model_id": "local-test",
        "model_artifact_sha256": "sha256:" + "1" * 64,
        "arm": "ledger",
        "seed": 104729,
        "prompt_sha256": "sha256:" + "2" * 64,
        "parse_status": "FORMAT_ERROR",
        "raw_decision": None,
        "final_decision": None,
        "latency_ms": 1,
        "output_tokens": 0,
        "verifier_calls": 0,
    }
    validate_with_schema(base, schema, "format error")
    omitted = dict(base)
    omitted.pop("raw_decision")
    omitted.pop("final_decision")
    validate_with_schema(omitted, schema, "format error without decision fields")
    valid = dict(base)
    valid["parse_status"] = "OK"
    validator = Draft202012Validator(load_json(schema))
    assert list(validator.iter_errors(valid))


def test_alpha_input_schema_rejects_resolved_research_status(root, inputs) -> None:
    item = deepcopy(inputs[0])
    item["current_state"]["research_status"] = "RESOLVED"
    validator = Draft202012Validator(load_json(root / "schemas" / "benchmark-input.schema.json"))
    errors = list(validator.iter_errors(item))
    assert any("OPEN" in error.message for error in errors)
