#!/usr/bin/env python3
"""Build a privacy-preserving dual-endpoint audit from frozen route records."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import (  # noqa: E402
    canonical_json,
    sha256_bytes,
    sha256_file,
)

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
STUDY_ROOT = ROOT / "v2" / "dual-endpoint-audit-v1"
REGISTRY_PATH = STUDY_ROOT / "registry.json"
GENERATED = ("aggregate.json", "receipt.json", "artifact-manifest.json")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"dual-endpoint-audit: {message}")


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> Json:
    value: Json = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_action(text: str) -> str | None:
    """Extract an exact action from one strict top-level JSON object."""

    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    action = value.get("action")
    return action if isinstance(action, str) and action in ACTIONS else None


def extract_action(record: Json) -> tuple[str | None, str]:
    """Use a parser-owned object first, then exact strict JSON without repair."""

    parsed = record.get("raw_decision")
    if isinstance(parsed, dict):
        action = parsed.get("action")
        if isinstance(action, str) and action in ACTIONS:
            return action, "PARSER_OBJECT"
    text = record.get("raw_response_text")
    if not isinstance(text, str):
        return None, "UNEXTRACTABLE"
    expected_digest = record.get("raw_response_sha256")
    if isinstance(expected_digest, str) and sha256_bytes(text.encode("utf-8")) != expected_digest:
        fail(f"raw response digest differs for {record.get('item_id')}")
    action = strict_json_action(text)
    return (action, "STRICT_RAW_JSON") if action is not None else (None, "UNEXTRACTABLE")


def _confusion_template(no_decision_column: str) -> Json:
    columns = (*ACTIONS, no_decision_column)
    return {gold: {prediction: 0 for prediction in columns} for gold in ACTIONS}


def derive_metrics(gold: list[Json], pairs: list[Json], records: list[Json]) -> Json:
    """Compare exact-action extraction with contract-validated action conformance."""

    if not records:
        fail("route records are empty")
    record_by_id = {str(row["item_id"]): row for row in records}
    if len(record_by_id) != len(records):
        fail("route records contain duplicate item IDs")
    gold_by_id = {str(row["id"]): row for row in gold}
    if not set(record_by_id) <= set(gold_by_id):
        fail("route records include unknown gold IDs")
    selected_gold = {item_id: gold_by_id[item_id] for item_id in record_by_id}

    pair_ids = {str(row["pair_id"]) for row in records}
    pair_by_id = {str(row["pair_id"]): row for row in pairs}
    if not pair_ids <= set(pair_by_id):
        fail("route records include unknown pair IDs")
    selected_pairs = [pair_by_id[pair_id] for pair_id in sorted(pair_ids)]
    selected_member_ids = {
        str(item_id) for pair in selected_pairs for item_id in pair["member_ids"]
    }
    if selected_member_ids != set(record_by_id):
        fail("selected pairs and route item IDs differ")
    for item_id, row in record_by_id.items():
        expected_pair = next(
            str(pair["pair_id"])
            for pair in selected_pairs
            if item_id in {str(value) for value in pair["member_ids"]}
        )
        if str(row["pair_id"]) != expected_pair:
            fail(f"record pair binding differs for {item_id}")

    action_predictions: dict[str, str | None] = {}
    extraction_sources: Counter[str] = Counter()
    parse_statuses: Counter[str] = Counter()
    action_confusion = _confusion_template("NO_EXTRACTABLE_ACTION")
    contract_confusion = _confusion_template("NO_VALID_CONTRACT")
    action_correct = 0
    contract_valid = 0
    contract_correct = 0
    for item_id, row in record_by_id.items():
        gold_action = str(selected_gold[item_id]["decision"]["action"])
        if gold_action not in ACTIONS:
            fail(f"unknown gold action for {item_id}: {gold_action}")
        action, source = extract_action(row)
        action_predictions[item_id] = action
        extraction_sources[source] += 1
        parse_status = str(row.get("parse_status"))
        parse_statuses[parse_status] += 1
        if action is None:
            action_confusion[gold_action]["NO_EXTRACTABLE_ACTION"] += 1
        else:
            action_confusion[gold_action][action] += 1
            action_correct += action == gold_action
        if parse_status == "OK":
            if source != "PARSER_OBJECT" or action is None:
                fail(f"OK record lacks a parser-owned action: {item_id}")
            contract_valid += 1
            contract_confusion[gold_action][action] += 1
            contract_correct += action == gold_action
        else:
            contract_confusion[gold_action]["NO_VALID_CONTRACT"] += 1

    action_covered_pairs = 0
    action_correct_pairs = 0
    contract_covered_pairs = 0
    contract_correct_pairs = 0
    for pair in selected_pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        action_covered = all(action_predictions[item_id] is not None for item_id in member_ids)
        contract_covered = all(
            record_by_id[item_id]["parse_status"] == "OK" for item_id in member_ids
        )
        action_covered_pairs += action_covered
        contract_covered_pairs += contract_covered
        action_pair_correct = action_covered and all(
            action_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
            for item_id in member_ids
        )
        contract_pair_correct = contract_covered and all(
            action_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
            for item_id in member_ids
        )
        action_correct_pairs += action_pair_correct
        contract_correct_pairs += contract_pair_correct

    items = len(records)
    pair_count = len(selected_pairs)
    extractable_items = items - extraction_sources["UNEXTRACTABLE"]
    outside_contract = extractable_items - contract_valid
    outside_contract_correct = action_correct - contract_correct
    if outside_contract < 0 or outside_contract_correct < 0:
        fail("action extraction cannot be narrower than contract validation")
    return {
        "scheduled_items": items,
        "scheduled_pairs": pair_count,
        "action_only": {
            "extractable_items": extractable_items,
            "correct_items": action_correct,
            "item_coverage": rate(extractable_items, items),
            "end_to_end_item_accuracy": rate(action_correct, items),
            "conditional_item_accuracy": rate(action_correct, extractable_items),
            "covered_pairs": action_covered_pairs,
            "correct_pairs": action_correct_pairs,
            "pair_coverage": rate(action_covered_pairs, pair_count),
            "end_to_end_pair_accuracy": rate(action_correct_pairs, pair_count),
            "conditional_pair_accuracy": rate(action_correct_pairs, action_covered_pairs),
            "confusion": action_confusion,
        },
        "full_contract": {
            "valid_items": contract_valid,
            "action_correct_items": contract_correct,
            "item_validity": rate(contract_valid, items),
            "end_to_end_action_accuracy": rate(contract_correct, items),
            "conditional_action_accuracy": rate(contract_correct, contract_valid),
            "valid_pairs": contract_covered_pairs,
            "action_correct_pairs": contract_correct_pairs,
            "pair_validity": rate(contract_covered_pairs, pair_count),
            "end_to_end_action_pair_accuracy": rate(contract_correct_pairs, pair_count),
            "conditional_action_pair_accuracy": rate(
                contract_correct_pairs, contract_covered_pairs
            ),
            "confusion": contract_confusion,
        },
        "endpoint_difference": {
            "extractable_items_outside_full_contract": outside_contract,
            "action_correct_items_outside_full_contract": outside_contract_correct,
            "additional_action_correct_pairs": action_correct_pairs - contract_correct_pairs,
        },
        "extraction_source_counts": dict(sorted(extraction_sources.items())),
        "parse_status_counts": dict(sorted(parse_statuses.items())),
    }


def validate_registry(registry: Json) -> list[Json]:
    routes = registry.get("routes")
    if not isinstance(routes, list) or not routes:
        fail("registry must contain routes")
    route_ids = [str(row["route_stack_id"]) for row in routes if isinstance(row, dict)]
    if len(route_ids) != len(routes) or len(set(route_ids)) != len(route_ids):
        fail("registry route IDs must be unique")
    return routes


def build(output_root: Path) -> None:
    registry = load_json(REGISTRY_PATH)
    routes = validate_registry(registry)
    outputs: list[Json] = []
    source_digests: Json = {}
    for route in routes:
        gold_path = ROOT / str(route["gold"])
        pairs_path = ROOT / str(route["pairs"])
        run_path = ROOT / str(route["run"])
        for path in (gold_path, pairs_path, run_path):
            if not path.is_file():
                fail(f"registered source is absent: {path}")
            source_digests[str(path.relative_to(ROOT))] = sha256_file(path)
        pair_value = load_json(pairs_path)
        if not isinstance(pair_value, list):
            fail(f"pair source must contain a list: {pairs_path}")
        records = load_jsonl(run_path)
        observed_lanes = {str(row.get("lane_id")) for row in records}
        if observed_lanes != {str(route["record_lane_id"])}:
            fail(f"registered lane differs: {route['route_stack_id']}")
        outputs.append(
            {
                "route_stack_id": route["route_stack_id"],
                "evidence_role": route["evidence_role"],
                "task_id": route["task_id"],
                "run_sha256": sha256_file(run_path),
                "metrics": derive_metrics(load_jsonl(gold_path), pair_value, records),
            }
        )
    output_root.mkdir(parents=True, exist_ok=True)
    aggregate: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE_POST_HOC_DUAL_ENDPOINT_AUDIT",
        "endpoint_definitions": {
            "action_only": (
                "Exact four-class action from a parser-owned object or one strict top-level JSON "
                "object. No repair, code-fence extraction, coercion, or duplicate key is accepted."
            ),
            "full_contract": (
                "The frozen parser marked the six-field output syntax-, schema-, and "
                "semantics-valid; action conformance is then scored."
            ),
            "denominator_rule": (
                "Every scheduled item and pair remains in both end-to-end denominators."
            ),
        },
        "interpretation": (
            "This offline audit separates safely extracted action behavior from complete output-"
            "contract conformance. It changes no frozen record, registered endpoint, or model call."
        ),
        "routes": sorted(outputs, key=lambda row: str(row["route_stack_id"])),
    }
    aggregate_path = output_root / "aggregate.json"
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "DUAL_ENDPOINT_AUDIT_REBUILT_FROM_FROZEN_RECORDS",
        "aggregate_sha256": sha256_file(aggregate_path),
        "registry_sha256": sha256_file(REGISTRY_PATH),
        "route_stacks": len(outputs),
        "model_calls": 0,
        "raw_response_content_written": False,
        "provider_response_ids_written": False,
        "source_digests": dict(sorted(source_digests.items())),
    }
    receipt_path = output_root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE_DETERMINISTIC_BUILD",
        "files": {
            "aggregate.json": sha256_file(aggregate_path),
            "receipt.json": sha256_file(receipt_path),
        },
    }
    manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    (output_root / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def compare_build(candidate: Path) -> None:
    differences = [
        name
        for name in GENERATED
        if not (STUDY_ROOT / name).is_file()
        or (STUDY_ROOT / name).read_bytes() != (candidate / name).read_bytes()
    ]
    if differences:
        fail(f"deterministic rebuild differs: {differences}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="cpb-dual-endpoint-") as directory:
            candidate = Path(directory) / STUDY_ROOT.name
            build(candidate)
            compare_build(candidate)
    else:
        existing = [name for name in GENERATED if (STUDY_ROOT / name).exists()]
        if existing:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        build(STUDY_ROOT)
    print(
        "dual-endpoint-audit: "
        f"routes={len(validate_registry(load_json(REGISTRY_PATH)))} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
