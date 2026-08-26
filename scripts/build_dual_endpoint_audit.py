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


def raw_strict_action(record: Json) -> tuple[str | None, str]:
    """Parse only the retained raw text as one duplicate-free top-level JSON object."""

    text = record.get("raw_response_text")
    if not isinstance(text, str):
        return None, "NO_RAW_RESPONSE"
    expected_digest = record.get("raw_response_sha256")
    if isinstance(expected_digest, str) and sha256_bytes(text.encode("utf-8")) != expected_digest:
        fail(f"raw response digest differs for {record.get('item_id')}")
    action = strict_json_action(text)
    return (action, "RAW_STRICT_JSON") if action is not None else (None, "RAW_STRICT_REJECTED")


def registered_parser_action(record: Json) -> tuple[str | None, str]:
    """Read the action and extraction provenance recorded by the frozen route parser."""

    parsed = record.get("raw_decision")
    if not isinstance(parsed, dict):
        return None, "NO_REGISTERED_ACTION"
    action = parsed.get("action")
    if not isinstance(action, str) or action not in ACTIONS:
        return None, "NO_REGISTERED_ACTION"
    detail = record.get("parse_error_detail")
    if isinstance(detail, str) and "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION" in detail:
        return action, "REGISTERED_SINGLE_OBJECT_EXTRACTION"
    return action, "REGISTERED_DIRECT_PARSE"


def _confusion_template(no_decision_column: str) -> Json:
    columns = (*ACTIONS, no_decision_column)
    return {gold: {prediction: 0 for prediction in columns} for gold in ACTIONS}


def _endpoint_metrics(
    predictions: dict[str, str | None],
    selected_gold: dict[str, Json],
    selected_pairs: list[Json],
    *,
    no_decision_column: str,
) -> Json:
    confusion = _confusion_template(no_decision_column)
    correct_items = 0
    for item_id, prediction in predictions.items():
        gold_action = str(selected_gold[item_id]["decision"]["action"])
        if prediction is None:
            confusion[gold_action][no_decision_column] += 1
        else:
            confusion[gold_action][prediction] += 1
            correct_items += prediction == gold_action

    covered_pairs = 0
    correct_pairs = 0
    for pair in selected_pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        covered = all(predictions[item_id] is not None for item_id in member_ids)
        covered_pairs += covered
        correct_pairs += covered and all(
            predictions[item_id] == selected_gold[item_id]["decision"]["action"]
            for item_id in member_ids
        )

    items = len(predictions)
    pairs = len(selected_pairs)
    extractable_items = sum(value is not None for value in predictions.values())
    return {
        "extractable_items": extractable_items,
        "correct_items": correct_items,
        "item_coverage": rate(extractable_items, items),
        "end_to_end_item_accuracy": rate(correct_items, items),
        "conditional_item_accuracy": rate(correct_items, extractable_items),
        "covered_pairs": covered_pairs,
        "correct_pairs": correct_pairs,
        "pair_coverage": rate(covered_pairs, pairs),
        "end_to_end_pair_accuracy": rate(correct_pairs, pairs),
        "conditional_pair_accuracy": rate(correct_pairs, covered_pairs),
        "confusion": confusion,
    }


def derive_metrics(gold: list[Json], pairs: list[Json], records: list[Json]) -> Json:
    """Compare raw-strict, registered-parser, and full-contract endpoints."""

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

    raw_predictions: dict[str, str | None] = {}
    registered_predictions: dict[str, str | None] = {}
    contract_predictions: dict[str, str | None] = {}
    raw_sources: Counter[str] = Counter()
    parser_sources: Counter[str] = Counter()
    parse_statuses: Counter[str] = Counter()
    for item_id, row in record_by_id.items():
        gold_action = str(selected_gold[item_id]["decision"]["action"])
        if gold_action not in ACTIONS:
            fail(f"unknown gold action for {item_id}: {gold_action}")
        raw_action, raw_source = raw_strict_action(row)
        parser_action, parser_source = registered_parser_action(row)
        raw_predictions[item_id] = raw_action
        registered_predictions[item_id] = parser_action
        raw_sources[raw_source] += 1
        parser_sources[parser_source] += 1
        parse_status = str(row.get("parse_status"))
        parse_statuses[parse_status] += 1
        if parse_status == "OK":
            if parser_action is None:
                fail(f"OK record lacks a parser-owned action: {item_id}")
            contract_predictions[item_id] = parser_action
        else:
            contract_predictions[item_id] = None

    raw_metrics = _endpoint_metrics(
        raw_predictions,
        selected_gold,
        selected_pairs,
        no_decision_column="NO_RAW_STRICT_ACTION",
    )
    parser_metrics = _endpoint_metrics(
        registered_predictions,
        selected_gold,
        selected_pairs,
        no_decision_column="NO_REGISTERED_ACTION",
    )
    contract_metrics = _endpoint_metrics(
        contract_predictions,
        selected_gold,
        selected_pairs,
        no_decision_column="NO_VALID_CONTRACT",
    )

    raw_correct_outside_contract = sum(
        raw_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
        and contract_predictions[item_id] is None
        for item_id in record_by_id
    )
    contract_correct_outside_raw = sum(
        contract_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
        and raw_predictions[item_id] != selected_gold[item_id]["decision"]["action"]
        for item_id in record_by_id
    )
    raw_extractable_outside_contract = sum(
        raw_predictions[item_id] is not None and contract_predictions[item_id] is None
        for item_id in record_by_id
    )
    contract_extractable_outside_raw = sum(
        contract_predictions[item_id] is not None and raw_predictions[item_id] is None
        for item_id in record_by_id
    )
    raw_correct_pairs_outside_contract = 0
    contract_correct_pairs_outside_raw = 0
    for pair in selected_pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        raw_correct = all(
            raw_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
            for item_id in member_ids
        )
        contract_correct = all(
            contract_predictions[item_id] == selected_gold[item_id]["decision"]["action"]
            for item_id in member_ids
        )
        raw_correct_pairs_outside_contract += raw_correct and not contract_correct
        contract_correct_pairs_outside_raw += contract_correct and not raw_correct

    items = len(records)
    pair_count = len(selected_pairs)
    return {
        "scheduled_items": items,
        "scheduled_pairs": pair_count,
        "raw_strict_action": raw_metrics,
        "registered_parser_action": parser_metrics,
        "full_contract": {
            "valid_items": contract_metrics["extractable_items"],
            "action_correct_items": contract_metrics["correct_items"],
            "item_validity": contract_metrics["item_coverage"],
            "end_to_end_action_accuracy": contract_metrics["end_to_end_item_accuracy"],
            "conditional_action_accuracy": contract_metrics["conditional_item_accuracy"],
            "valid_pairs": contract_metrics["covered_pairs"],
            "action_correct_pairs": contract_metrics["correct_pairs"],
            "pair_validity": contract_metrics["pair_coverage"],
            "end_to_end_action_pair_accuracy": contract_metrics["end_to_end_pair_accuracy"],
            "conditional_action_pair_accuracy": contract_metrics["conditional_pair_accuracy"],
            "confusion": contract_metrics["confusion"],
        },
        "endpoint_overlap": {
            "raw_strict_extractable_outside_full_contract": raw_extractable_outside_contract,
            "raw_strict_correct_items_outside_full_contract": raw_correct_outside_contract,
            "raw_strict_correct_pairs_outside_full_contract": (raw_correct_pairs_outside_contract),
            "full_contract_extractable_outside_raw_strict": contract_extractable_outside_raw,
            "full_contract_correct_items_outside_raw_strict": contract_correct_outside_raw,
            "full_contract_correct_pairs_outside_raw_strict": (contract_correct_pairs_outside_raw),
        },
        "raw_strict_source_counts": dict(sorted(raw_sources.items())),
        "registered_parser_provenance_counts": dict(sorted(parser_sources.items())),
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
        "schema_version": "1.1.0",
        "status": "COMPLETE_POST_HOC_DUAL_ENDPOINT_AUDIT",
        "endpoint_definitions": {
            "raw_strict_action": (
                "Exact four-class action parsed directly from one duplicate-free top-level JSON "
                "object in retained raw response text. No fence or substring extraction, repair, "
                "coercion, or non-standard constant is accepted."
            ),
            "registered_parser_action": (
                "Four-class action in the object emitted by each frozen route's registered parser. "
                "Parser provenance distinguishes direct parsing from deterministic single-object "
                "extraction."
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
            "This offline audit separates raw-strict action parsing, each route's registered "
            "parser policy, and complete output-contract conformance. Registered parsers follow "
            "their frozen duplicate-key and object-extraction policies; no duplicate key occurs "
            "in the audited responses. The audit changes no frozen record or model call."
        ),
        "routes": sorted(outputs, key=lambda row: str(row["route_stack_id"])),
    }
    aggregate_path = output_root / "aggregate.json"
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt: Json = {
        "schema_version": "1.1.0",
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
        "schema_version": "1.1.0",
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
    parser.add_argument(
        "--replace-generated",
        action="store_true",
        help="replace only the three deterministic generated files in the registered study root",
    )
    args = parser.parse_args()
    if args.check and args.replace_generated:
        fail("--check and --replace-generated are mutually exclusive")
    if args.check:
        with tempfile.TemporaryDirectory(prefix="cpb-dual-endpoint-") as directory:
            candidate = Path(directory) / STUDY_ROOT.name
            build(candidate)
            compare_build(candidate)
    else:
        existing = [name for name in GENERATED if (STUDY_ROOT / name).exists()]
        if existing and not args.replace_generated:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        if args.replace_generated:
            for name in existing:
                (STUDY_ROOT / name).unlink()
        build(STUDY_ROOT)
    print(
        "dual-endpoint-audit: "
        f"routes={len(validate_registry(load_json(REGISTRY_PATH)))} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
