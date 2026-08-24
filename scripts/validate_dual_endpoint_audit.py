#!/usr/bin/env python3
"""Validate the privacy-preserving dual-endpoint audit offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "dual-endpoint-audit-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")
Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"dual-endpoint-validation: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def _confusion_total(confusion: Json) -> int:
    return sum(
        int(count)
        for predictions in confusion.values()
        if isinstance(predictions, dict)
        for count in predictions.values()
    )


def validate(root: Path = STUDY_ROOT) -> Json:
    registry = load_object(root / "registry.json")
    registered_routes = registry.get("routes")
    if not isinstance(registered_routes, list) or len(registered_routes) != 10:
        fail("registry must bind ten route stacks")
    registered_ids = {
        str(row["route_stack_id"]) for row in registered_routes if isinstance(row, dict)
    }
    if len(registered_ids) != 10:
        fail("registered route-stack IDs must be unique")

    manifest = load_object(root / "artifact-manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != {"aggregate.json", "receipt.json"}:
        fail("artifact manifest file set differs")
    for relative, expected in files.items():
        path = root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"generated artifact digest differs: {relative}")
    payload = {key: value for key, value in manifest.items() if key != "self_digest"}
    if manifest.get("self_digest") != sha256_bytes(canonical_json(payload).encode("utf-8")):
        fail("manifest self digest differs")

    receipt = load_object(root / "receipt.json")
    if (
        receipt.get("status") != "DUAL_ENDPOINT_AUDIT_REBUILT_FROM_FROZEN_RECORDS"
        or receipt.get("model_calls") != 0
        or receipt.get("route_stacks") != 10
        or receipt.get("raw_response_content_written") is not False
        or receipt.get("provider_response_ids_written") is not False
        or receipt.get("aggregate_sha256") != sha256_file(root / "aggregate.json")
        or receipt.get("registry_sha256") != sha256_file(root / "registry.json")
    ):
        fail("audit receipt boundary differs")
    source_digests = receipt.get("source_digests")
    if not isinstance(source_digests, dict):
        fail("receipt lacks source digests")
    for relative, expected in source_digests.items():
        path = ROOT / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"frozen source digest differs: {relative}")

    aggregate = load_object(root / "aggregate.json")
    routes = aggregate.get("routes")
    if (
        aggregate.get("schema_version") != "1.1.0"
        or set(aggregate.get("endpoint_definitions", {}))
        != {"denominator_rule", "full_contract", "raw_strict_action", "registered_parser_action"}
        or aggregate.get("status") != "COMPLETE_POST_HOC_DUAL_ENDPOINT_AUDIT"
        or not isinstance(routes, list)
        or len(routes) != 10
        or {str(row["route_stack_id"]) for row in routes if isinstance(row, dict)} != registered_ids
    ):
        fail("aggregate route boundary differs")

    by_id: dict[str, Json] = {}
    for route in routes:
        if not isinstance(route, dict):
            fail("route aggregate must be an object")
        route_id = str(route["route_stack_id"])
        by_id[route_id] = route
        metrics = route.get("metrics")
        if not isinstance(metrics, dict):
            fail(f"route metrics are absent: {route_id}")
        items = int(metrics["scheduled_items"])
        pairs = int(metrics["scheduled_pairs"])
        raw = metrics["raw_strict_action"]
        registered = metrics["registered_parser_action"]
        contract = metrics["full_contract"]
        if (
            _confusion_total(raw["confusion"]) != items
            or _confusion_total(registered["confusion"]) != items
            or _confusion_total(contract["confusion"]) != items
            or int(raw["covered_pairs"]) > pairs
            or int(registered["covered_pairs"]) > pairs
            or int(contract["valid_pairs"]) > pairs
        ):
            fail(f"confusion or pair totals differ: {route_id}")
        if (
            int(registered["extractable_items"]) != int(contract["valid_items"])
            or int(registered["correct_items"]) != int(contract["action_correct_items"])
            or int(registered["covered_pairs"]) != int(contract["valid_pairs"])
            or int(registered["correct_pairs"]) != int(contract["action_correct_pairs"])
        ):
            fail(f"registered parser and current full-contract records differ: {route_id}")
        if sum(int(value) for value in metrics["raw_strict_source_counts"].values()) != items:
            fail(f"raw-strict provenance total differs: {route_id}")
        if (
            sum(int(value) for value in metrics["registered_parser_provenance_counts"].values())
            != items
        ):
            fail(f"registered-parser provenance total differs: {route_id}")

    expected_raw_strict = {
        "challenge-deepseek-flash-host-schema": (180, 105, 90, 19),
        "challenge-qwen-host-prompt": (143, 128, 61, 46),
        "slsa-deepseek-flash-host-schema": (110, 110, 51, 51),
        "slsa-qwen-host-prompt": (120, 120, 60, 60),
    }
    for route_id, expected in expected_raw_strict.items():
        raw = by_id[route_id]["metrics"]["raw_strict_action"]
        observed = tuple(
            int(raw[field])
            for field in ("extractable_items", "correct_items", "covered_pairs", "correct_pairs")
        )
        if observed != expected:
            fail(f"raw-strict endpoint finding differs: {route_id}")

    overlap_totals = {
        key: sum(int(route["metrics"]["endpoint_overlap"][key]) for route in routes)
        for key in (
            "raw_strict_extractable_outside_full_contract",
            "raw_strict_correct_items_outside_full_contract",
            "raw_strict_correct_pairs_outside_full_contract",
            "full_contract_extractable_outside_raw_strict",
            "full_contract_correct_items_outside_raw_strict",
            "full_contract_correct_pairs_outside_raw_strict",
        )
    }
    if overlap_totals != {
        "raw_strict_extractable_outside_full_contract": 69,
        "raw_strict_correct_items_outside_full_contract": 49,
        "raw_strict_correct_pairs_outside_full_contract": 40,
        "full_contract_extractable_outside_raw_strict": 452,
        "full_contract_correct_items_outside_raw_strict": 329,
        "full_contract_correct_pairs_outside_raw_strict": 78,
    }:
        fail("cross-endpoint overlap totals differ")

    for path in (root / "aggregate.json", root / "receipt.json", root / "artifact-manifest.json"):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ACCOUNT_MARKERS:
            if marker.lower() in text:
                fail(f"account marker in release-facing artifact: {path}: {marker}")
    return {
        "route_stacks": len(routes),
        "scheduled_items": sum(int(row["metrics"]["scheduled_items"]) for row in routes),
        "raw_strict_correct_outside_contract": overlap_totals[
            "raw_strict_correct_items_outside_full_contract"
        ],
        "raw_strict_correct_pairs_outside_contract": overlap_totals[
            "raw_strict_correct_pairs_outside_full_contract"
        ],
        "contract_correct_outside_raw_strict": overlap_totals[
            "full_contract_correct_items_outside_raw_strict"
        ],
        "contract_correct_pairs_outside_raw_strict": overlap_totals[
            "full_contract_correct_pairs_outside_raw_strict"
        ],
    }


def main() -> int:
    report = validate()
    print(
        "dual-endpoint-validation: "
        f"routes={report['route_stacks']} items={report['scheduled_items']} "
        f"raw_strict_extra_correct={report['raw_strict_correct_outside_contract']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
