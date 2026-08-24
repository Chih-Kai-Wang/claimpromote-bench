#!/usr/bin/env python3
"""Validate the current paper's anonymous repetition and endpoint evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
FORBIDDEN_KEYS = {
    "hidden_reasoning",
    "parse_error_detail",
    "provider_request_id",
    "provider_response_id",
    "raw_decision",
    "raw_response_sha256",
    "raw_response_text",
    "reasoning_content",
    "request_body",
    "thinking",
    "transport_error",
}
Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"anonymous-current-evidence: {message}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected a JSON object: {path.relative_to(ROOT)}")
    return value


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(row, dict) for row in rows):
        fail(f"expected JSON objects: {path.relative_to(ROOT)}")
    return rows


def walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in walk_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in walk_keys(child)}
    return set()


def validate_dynamic_manifest(root: Path) -> Json:
    manifest_path = root / "MANIFEST.json"
    manifest = load_object(manifest_path)
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256_text(canonical_json(payload)):
        fail(f"manifest self-digest differs: {root.relative_to(ROOT)}")
    actual = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if manifest.get("file_count") != len(actual) or manifest.get("files") != actual:
        fail(f"manifest inventory differs: {root.relative_to(ROOT)}")
    return manifest


def _pair_correct(rows: list[Json], field: str) -> int:
    by_pair: dict[str, list[Json]] = defaultdict(list)
    for row in rows:
        by_pair[str(row["pair_id"])].append(row)
    if any(len(members) != 2 for members in by_pair.values()):
        fail("a repetition pair does not contain exactly two members")
    return sum(all(bool(member[field]) for member in members) for members in by_pair.values())


def _assert_fraction(metric: Any, numerator: int, denominator: int, label: str) -> None:
    if not isinstance(metric, dict) or metric.get("numerator") != numerator:
        fail(f"{label} numerator differs")
    if metric.get("denominator") != denominator:
        fail(f"{label} denominator differs")
    expected = numerator / denominator if denominator else None
    if metric.get("value") != expected:
        fail(f"{label} value differs")


def validate_upstream_route_repetition() -> Json:
    root = EVIDENCE / "upstream-policy-route-repetition"
    top_manifest = validate_dynamic_manifest(root)
    if top_manifest.get("scope", {}).get("scheduled_terminal_records") != 144:
        fail("upstream repetition scope differs")

    results = root / "results"
    result_manifest_path = results / "manifest.json"
    result_manifest = load_object(result_manifest_path)
    payload = {key: value for key, value in result_manifest.items() if key != "self_digest"}
    if result_manifest.get("self_digest") != sha256_text(canonical_json(payload)):
        fail("upstream repetition result-manifest self-digest differs")
    result_files = sorted(path for path in results.rglob("*") if path.is_file())
    hashed = {
        path.relative_to(results).as_posix(): sha256_file(path)
        for path in result_files
        if path != result_manifest_path
    }
    if (
        result_manifest.get("file_count") != len(result_files)
        or result_manifest.get("hashed_file_count") != len(hashed)
        or result_manifest.get("files_sha256") != hashed
    ):
        fail("upstream repetition result-manifest inventory differs")

    privacy = load_object(results / "privacy-receipt.json")
    scanned = privacy.get("scanned_files_sha256")
    if not isinstance(scanned, dict) or scanned != {
        relative: sha256_file(results / str(relative)) for relative in sorted(scanned)
    }:
        fail("upstream repetition privacy bindings differ")
    if any(
        privacy.get(field) is not False
        for field in (
            "credentials_loaded_for_analysis",
            "hidden_reasoning_retained",
            "invalid_response_contents_entered_results",
            "provider_response_identifiers_retained",
            "raw_model_response_content_retained",
        )
    ):
        fail("upstream repetition privacy boundary differs")

    gold = load_jsonl(
        ROOT / "v2" / "upstream-policy-revisions-v1" / "dataset" / "evaluation-gold.jsonl"
    )
    pairs = json.loads(
        (
            ROOT / "v2" / "upstream-policy-revisions-v1" / "dataset" / "evaluation-pairs.json"
        ).read_text(encoding="utf-8")
    )
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
    pair_by_item = {
        str(item_id): str(pair["pair_id"]) for pair in pairs for item_id in pair["member_ids"]
    }

    rows = [
        row for path in sorted((results / "records").glob("*.jsonl")) for row in load_jsonl(path)
    ]
    if len(rows) != 144 or FORBIDDEN_KEYS & walk_keys(rows):
        fail("upstream repetition records violate the release boundary")
    identities = {(str(row["lane_id"]), int(row["repetition"])) for row in rows}
    if len(identities) != 6:
        fail("upstream repetition lane-by-repetition matrix differs")
    seen_cells: set[str] = set()
    for row in rows:
        item_id = str(row["item_id"])
        cell_id = str(row["cell_id"])
        if cell_id in seen_cells or item_id not in gold_by_id:
            fail(f"upstream repetition cell is duplicate or unknown: {cell_id}")
        seen_cells.add(cell_id)
        if (
            row.get("gold_action") != gold_by_id[item_id]
            or row.get("pair_id") != pair_by_item[item_id]
        ):
            fail(f"upstream repetition gold or pair binding differs: {cell_id}")
        extracted = row.get("extracted_action")
        expected_strict = extracted == gold_by_id[item_id]
        expected_contract = row.get("parse_status") == "OK" and expected_strict
        if row.get("strict_action_correct") is not expected_strict:
            fail(f"upstream repetition strict-action score differs: {cell_id}")
        if row.get("contract_action_correct") is not expected_contract:
            fail(f"upstream repetition contract-action score differs: {cell_id}")
        if row.get("parse_status") == "OK" and extracted not in {"ALLOW", "HOLD"}:
            fail(f"upstream repetition valid record lacks an action: {cell_id}")

    aggregate = load_object(results / "aggregate.json")
    if (
        aggregate.get("scheduled_cells") != 144
        or aggregate.get("client_retries") != 0
        or aggregate.get("frozen_plan_commit") != "WITHHELD_PREINFERENCE_COMMIT"
        or aggregate.get("raw_or_invalid_response_content_in_aggregate") is not False
    ):
        fail("upstream repetition aggregate boundary differs")
    aggregate_by_lane = {str(row["lane_id"]): row for row in aggregate.get("lanes", [])}
    if set(aggregate_by_lane) != {lane for lane, _ in identities}:
        fail("upstream repetition aggregate lane set differs")

    for lane_id, repetition in sorted(identities):
        selected = [
            row
            for row in rows
            if row["lane_id"] == lane_id and int(row["repetition"]) == repetition
        ]
        if len(selected) != 24 or {str(row["item_id"]) for row in selected} != set(gold_by_id):
            fail(f"upstream repetition coverage differs: {lane_id}/r{repetition}")
        archived = next(
            row
            for row in aggregate_by_lane[lane_id]["by_repetition"]
            if int(row["repetition"]) == repetition
        )
        strict = sum(bool(row["strict_action_correct"]) for row in selected)
        contract = sum(bool(row["contract_action_correct"]) for row in selected)
        full = sum(bool(row["full_decision_exact"]) for row in selected)
        _assert_fraction(archived["strict_action"]["accuracy"], strict, 24, "strict action")
        _assert_fraction(archived["contract_action"]["accuracy"], contract, 24, "contract action")
        _assert_fraction(archived["full_decision_exact"]["accuracy"], full, 24, "full decision")
        for endpoint, field in (
            ("strict_action", "strict_action_correct"),
            ("contract_action", "contract_action_correct"),
            ("full_decision_exact", "full_decision_exact"),
        ):
            _assert_fraction(
                archived["pair_accuracy"][endpoint],
                _pair_correct(selected, field),
                12,
                f"{endpoint} pair",
            )
        if archived.get("parse_status_counts") != dict(
            sorted(Counter(str(row["parse_status"]) for row in selected).items())
        ):
            fail(f"upstream repetition parser counts differ: {lane_id}/r{repetition}")

    for lane_id, archived_lane in aggregate_by_lane.items():
        selected = [row for row in rows if row["lane_id"] == lane_id]
        total = archived_lane["descriptive_three_repeat_total"]
        for endpoint, field in (
            ("strict_action", "strict_action_correct"),
            ("contract_action", "contract_action_correct"),
            ("full_decision_exact", "full_decision_exact"),
        ):
            _assert_fraction(
                total[endpoint]["accuracy"],
                sum(bool(row[field]) for row in selected),
                72,
                f"{lane_id} total {endpoint}",
            )
            _assert_fraction(
                total["pair_accuracy"][endpoint],
                sum(
                    _pair_correct(
                        [row for row in selected if int(row["repetition"]) == repetition],
                        field,
                    )
                    for repetition in (1, 2, 3)
                ),
                36,
                f"{lane_id} total {endpoint} pair",
            )

    diagnostics = root / "diagnostics"
    diagnostic_manifest_path = diagnostics / "manifest.json"
    diagnostic_manifest = load_object(diagnostic_manifest_path)
    payload = {key: value for key, value in diagnostic_manifest.items() if key != "self_digest"}
    if diagnostic_manifest.get("self_digest") != sha256_text(canonical_json(payload)):
        fail("upstream repetition diagnostic self-digest differs")
    for relative, expected in diagnostic_manifest.get("files_sha256", {}).items():
        if sha256_file(diagnostics / str(relative)) != expected:
            fail(f"upstream repetition diagnostic digest differs: {relative}")
    modes = load_object(diagnostics / "failure-modes.json")
    mode_by_lane = {str(row["lane_id"]): row for row in modes.get("lanes", [])}
    for lane_id, selected in (
        (lane, [row for row in rows if row["lane_id"] == lane]) for lane in aggregate_by_lane
    ):
        mode_counts = mode_by_lane[lane_id]["failure_mode_counts"]
        if sum(int(value) for value in mode_counts.values()) != 72:
            fail(f"upstream repetition failure-mode denominator differs: {lane_id}")
        if int(mode_counts.get("CONTRACT_VALID", 0)) != sum(
            row["parse_status"] == "OK" for row in selected
        ):
            fail(f"upstream repetition contract-valid diagnostic differs: {lane_id}")
    return {
        "scheduled_cells": len(rows),
        "lanes": len(aggregate_by_lane),
        "result_files": len(result_files),
    }


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def confusion_template(no_decision: str) -> Json:
    return {gold: {prediction: 0 for prediction in (*ACTIONS, no_decision)} for gold in ACTIONS}


def derive_dual_metrics(rows: list[Json]) -> Json:
    action_confusion = confusion_template("NO_EXTRACTABLE_ACTION")
    contract_confusion = confusion_template("NO_VALID_CONTRACT")
    extraction_sources: Counter[str] = Counter()
    parse_statuses: Counter[str] = Counter()
    by_pair: dict[str, list[Json]] = defaultdict(list)
    action_correct = contract_valid = contract_correct = 0
    for row in rows:
        record_label = f"{row['route_stack_id']}/{row['item_id']}"
        gold = str(row["gold_action"])
        action = row.get("strict_action")
        contract = row.get("contract_action")
        parse_status = str(row["parse_status"])
        by_pair[str(row["pair_id"])].append(row)
        extraction_sources[str(row["strict_action_source"])] += 1
        parse_statuses[parse_status] += 1
        if action is None:
            action_confusion[gold]["NO_EXTRACTABLE_ACTION"] += 1
        else:
            action_confusion[gold][str(action)] += 1
            action_correct += action == gold
        if parse_status == "OK":
            if contract != action or action is None:
                fail(f"dual endpoint valid record lacks its action: {record_label}")
            contract_valid += 1
            contract_confusion[gold][str(contract)] += 1
            contract_correct += contract == gold
        else:
            if contract is not None:
                fail(f"dual endpoint invalid record retains a contract action: {record_label}")
            contract_confusion[gold]["NO_VALID_CONTRACT"] += 1
    if any(len(members) != 2 for members in by_pair.values()):
        fail("dual endpoint pair membership differs")
    action_covered_pairs = sum(
        all(row["strict_action"] is not None for row in members) for members in by_pair.values()
    )
    action_correct_pairs = sum(
        all(row["strict_action"] == row["gold_action"] for row in members)
        for members in by_pair.values()
    )
    contract_covered_pairs = sum(
        all(row["parse_status"] == "OK" for row in members) for members in by_pair.values()
    )
    contract_correct_pairs = sum(
        all(row["contract_action"] == row["gold_action"] for row in members)
        for members in by_pair.values()
    )
    items = len(rows)
    pairs = len(by_pair)
    extractable = items - extraction_sources["UNEXTRACTABLE"]
    return {
        "scheduled_items": items,
        "scheduled_pairs": pairs,
        "action_only": {
            "extractable_items": extractable,
            "correct_items": action_correct,
            "item_coverage": rate(extractable, items),
            "end_to_end_item_accuracy": rate(action_correct, items),
            "conditional_item_accuracy": rate(action_correct, extractable),
            "covered_pairs": action_covered_pairs,
            "correct_pairs": action_correct_pairs,
            "pair_coverage": rate(action_covered_pairs, pairs),
            "end_to_end_pair_accuracy": rate(action_correct_pairs, pairs),
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
            "pair_validity": rate(contract_covered_pairs, pairs),
            "end_to_end_action_pair_accuracy": rate(contract_correct_pairs, pairs),
            "conditional_action_pair_accuracy": rate(
                contract_correct_pairs, contract_covered_pairs
            ),
            "confusion": contract_confusion,
        },
        "endpoint_difference": {
            "extractable_items_outside_full_contract": extractable - contract_valid,
            "action_correct_items_outside_full_contract": action_correct - contract_correct,
            "additional_action_correct_pairs": action_correct_pairs - contract_correct_pairs,
        },
        "extraction_source_counts": dict(sorted(extraction_sources.items())),
        "parse_status_counts": dict(sorted(parse_statuses.items())),
    }


def validate_dual_endpoint() -> Json:
    root = EVIDENCE / "dual-endpoint-audit"
    manifest = validate_dynamic_manifest(root)
    rows = load_jsonl(root / "items.jsonl")
    if len(rows) != 1320 or FORBIDDEN_KEYS & walk_keys(rows):
        fail("dual-endpoint records violate the release boundary")
    identities = {(str(row["route_stack_id"]), str(row["item_id"])) for row in rows}
    if len(identities) != len(rows):
        fail("dual-endpoint records contain duplicate route-item identities")
    aggregate = load_object(root / "aggregate.json")
    archived = {str(row["route_stack_id"]): row for row in aggregate.get("routes", [])}
    grouped: dict[str, list[Json]] = defaultdict(list)
    for row in rows:
        grouped[str(row["route_stack_id"])].append(row)
    if set(grouped) != set(archived) or len(grouped) != 10:
        fail("dual-endpoint route set differs")
    for route_id, selected in grouped.items():
        if derive_dual_metrics(selected) != archived[route_id].get("metrics"):
            fail(f"dual-endpoint aggregate differs from released rows: {route_id}")
    privacy = load_object(root / "privacy-receipt.json")
    payload = {key: value for key, value in privacy.items() if key != "self_digest"}
    if privacy.get("self_digest") != sha256_text(canonical_json(payload)):
        fail("dual-endpoint privacy self-digest differs")
    if (
        privacy.get("item_records") != len(rows)
        or privacy.get("items_sha256") != sha256_file(root / "items.jsonl")
        or privacy.get("aggregate_sha256") != sha256_file(root / "aggregate.json")
        or privacy.get("model_calls_performed") != 0
        or any(
            privacy.get(field) is not False
            for field in (
                "free_form_error_text_included",
                "full_structured_decisions_included",
                "hidden_reasoning_included",
                "provider_response_identifiers_included",
                "raw_response_text_included",
            )
        )
    ):
        fail("dual-endpoint privacy boundary differs")
    extra_extractable = sum(
        int(row["metrics"]["endpoint_difference"]["extractable_items_outside_full_contract"])
        for row in aggregate["routes"]
    )
    extra_correct_items = sum(
        int(row["metrics"]["endpoint_difference"]["action_correct_items_outside_full_contract"])
        for row in aggregate["routes"]
    )
    extra_pairs = sum(
        int(row["metrics"]["endpoint_difference"]["additional_action_correct_pairs"])
        for row in aggregate["routes"]
    )
    if extra_extractable != 69 or extra_correct_items != 49 or extra_pairs != 40:
        fail("dual-endpoint headline totals differ")
    return {
        "route_stacks": len(grouped),
        "scheduled_items": len(rows),
        "extra_extractable_items": extra_extractable,
        "extra_correct_items": extra_correct_items,
        "extra_correct_pairs": extra_pairs,
        "manifest_files": manifest["file_count"],
    }


def main() -> int:
    report = {
        "status": "PASS",
        "upstream_route_repetition": validate_upstream_route_repetition(),
        "dual_endpoint": validate_dual_endpoint(),
    }
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
