#!/usr/bin/env python3
"""Analyze complete repeated routes on historical upstream policy revisions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from frozen_run_io import atomic_output_directory  # noqa: E402
from upstream_route_repetition import (  # noqa: E402
    GOLD_PATH,
    PAIRS_PATH,
    RUN_SCHEMA,
    STUDY_ID,
    STUDY_ROOT,
    canonical_decision,
)
from validate_upstream_policy_route_repetition import validate_freeze  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "chih-kai")
FORBIDDEN_RESULT_KEYS = {
    "raw_response_text",
    "raw_response_sha256",
    "transport_error",
    "parse_error_detail",
    "provider_response_id",
    "hidden_reasoning",
    "prompt",
    "request_body",
}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-analysis: {message}")


def metric(numerator: int, denominator: int) -> Json:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _load_object(path: Path) -> Json:
    value = load_json(path)
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def _expected_output_names(plan: Json) -> list[str]:
    return [
        f"{lane['lane_id']}-r{repetition}.jsonl"
        for lane in plan["formal_lanes"]
        for repetition in range(1, 4)
    ]


def load_and_validate_records(
    plan: Json,
    schedule: Json,
    private_root: Path,
    journal_root: Path,
) -> tuple[Json, list[Json]]:
    receipt = _load_object(private_root / "execution-receipt.json")
    expected_names = _expected_output_names(plan)
    outputs = receipt.get("outputs")
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("schedule_sha256") != schedule.get("schedule_sha256")
        or receipt.get("planned_cells") != 144
        or receipt.get("durable_intents") != 144
        or receipt.get("durable_terminal_records") != 144
        or receipt.get("application_posts") != 144
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("credentials_retained") is not False
        or receipt.get("provider_response_ids_retained") is not False
        or receipt.get("hidden_reasoning_retained") is not False
        or receipt.get("workflow_initiated_purchase_or_recharge") is not False
        or not isinstance(outputs, list)
        or [str(row.get("file")) for row in outputs] != expected_names
    ):
        fail("execution receipt is incomplete or differs from the frozen protocol")
    records: list[Json] = []
    for output in outputs:
        path = private_root / str(output["file"])
        rows = load_jsonl(path)
        if (
            output.get("records") != 24
            or len(rows) != 24
            or output.get("sha256") != sha256_file(path)
        ):
            fail(f"private route output differs: {path.name}")
        if any(
            row.get("lane_id") != output.get("lane_id")
            or row.get("repetition") != output.get("repetition")
            for row in rows
        ):
            fail(f"private route output mixes lanes or repetitions: {path.name}")
        records.extend(rows)
    if len(records) != 144:
        fail("private outputs must contain 144 terminal records")

    cells_by_id = {str(cell["cell_id"]): cell for cell in schedule["cells"]}
    lanes_by_id = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    records_by_cell: dict[str, Json] = {}
    for record in records:
        validate_with_schema(record, RUN_SCHEMA, str(record.get("cell_id")))
        cell_id = str(record["cell_id"])
        cell = cells_by_id.get(cell_id)
        if cell is None or cell_id in records_by_cell:
            fail(f"terminal record is repeated or absent from schedule: {cell_id}")
        lane = lanes_by_id[str(cell["lane_id"])]
        if (
            record.get("study_id") != STUDY_ID
            or record.get("frozen_plan_commit") != receipt.get("frozen_plan_commit")
            or record.get("schedule_sha256") != schedule.get("schedule_sha256")
            or record.get("packet_sha256") != schedule.get("packet_sha256")
            or record.get("sequence") != cell.get("sequence")
            or record.get("repetition") != cell.get("repetition")
            or record.get("lane_id") != cell.get("lane_id")
            or record.get("item_id") != cell.get("item_id")
            or record.get("pair_id") != cell.get("pair_id")
            or record.get("prompt_sha256") != cell.get("prompt_sha256")
            or record.get("request_sha256") != cell.get("request_body_sha256")
            or record.get("provider") != lane.get("provider")
            or record.get("model_requested") != lane.get("model")
            or record.get("model_family") != lane.get("model_family")
            or record.get("provider_response_id_retained") is not False
            or record.get("hidden_reasoning_retained") is not False
        ):
            fail(f"terminal record differs from its frozen cell: {cell_id}")
        content = record.get("raw_response_text")
        expected_raw_hash = (
            sha256_bytes(content.encode("utf-8")) if isinstance(content, str) else None
        )
        if record.get("raw_response_sha256") != expected_raw_hash:
            fail(f"raw response digest differs: {cell_id}")
        action = record.get("extracted_action")
        if (record.get("action_extraction_status") == "EXTRACTED") != isinstance(action, str):
            fail(f"action extraction status differs: {cell_id}")
        if (record.get("parse_status") == "OK") != isinstance(record.get("full_decision"), dict):
            fail(f"full decision and parse status differ: {cell_id}")
        records_by_cell[cell_id] = record
    if set(records_by_cell) != set(cells_by_id):
        fail("terminal records do not cover every frozen cell exactly once")

    starts = _load_object(journal_root / "run-start.json")
    intents = load_jsonl(journal_root / "request-intents.jsonl")
    terminals = load_jsonl(journal_root / "terminal-records.jsonl")
    if (
        starts.get("frozen_plan_commit") != receipt.get("frozen_plan_commit")
        or starts.get("schedule_sha256") != schedule.get("schedule_sha256")
        or len(intents) != 144
        or len(terminals) != 144
        or [int(row["sequence"]) for row in intents] != list(range(144))
        or [int(row["sequence"]) for row in terminals] != list(range(144))
        or [str(row["cell_id"]) for row in intents]
        != [str(cell["cell_id"]) for cell in schedule["cells"]]
        or [str(row["cell_id"]) for row in terminals]
        != [str(cell["cell_id"]) for cell in schedule["cells"]]
    ):
        fail("durable journal differs from the complete frozen execution")
    for terminal in terminals:
        cell_id = str(terminal["cell_id"])
        if terminal.get("record") != records_by_cell[cell_id]:
            fail(f"durable terminal and private output differ: {cell_id}")
    ordered = [records_by_cell[str(cell["cell_id"])] for cell in schedule["cells"]]
    return receipt, ordered


def score_records(records: list[Json], gold_by_id: dict[str, Json]) -> list[Json]:
    scored: list[Json] = []
    for record in records:
        gold = gold_by_id[str(record["item_id"])]["decision"]
        action_correct = record.get("extracted_action") == gold["action"]
        contract_action_correct = record.get("parse_status") == "OK" and action_correct
        full_exact = record.get("parse_status") == "OK" and canonical_decision(
            record["full_decision"]
        ) == canonical_decision(gold)
        scored.append(
            {
                **record,
                "gold_action": gold["action"],
                "strict_action_correct": action_correct,
                "contract_action_correct": contract_action_correct,
                "full_decision_exact": full_exact,
            }
        )
    return scored


def _confusion(rows: list[Json], *, contract: bool) -> Json:
    columns = ("ALLOW", "HOLD", "INVALID_CONTRACT" if contract else "UNEXTRACTABLE")
    table: Json = {}
    for gold_action in ("ALLOW", "HOLD"):
        row = {column: 0 for column in columns}
        for record in rows:
            if record["gold_action"] != gold_action:
                continue
            if contract and record["parse_status"] != "OK":
                predicted = "INVALID_CONTRACT"
            elif record.get("extracted_action") in ("ALLOW", "HOLD"):
                predicted = str(record["extracted_action"])
            else:
                predicted = "UNEXTRACTABLE"
            row[predicted] += 1
        table[gold_action] = row
    return table


def _recall(rows: list[Json], field: str) -> Json:
    result: Json = {}
    for action in ("ALLOW", "HOLD"):
        selected = [row for row in rows if row["gold_action"] == action]
        result[action] = metric(sum(bool(row[field]) for row in selected), len(selected))
    return result


def _pair_metrics(rows: list[Json], pairs: list[Json]) -> Json:
    by_item = {str(row["item_id"]): row for row in rows}
    if len(by_item) != len(rows):
        fail("pair metrics require one record per item")
    result: Json = {"pairs": len(pairs)}
    for label, field in (
        ("strict_action", "strict_action_correct"),
        ("contract_action", "contract_action_correct"),
        ("full_decision_exact", "full_decision_exact"),
    ):
        correct = sum(
            all(bool(by_item[str(item_id)][field]) for item_id in pair["member_ids"])
            for pair in pairs
        )
        result[label] = metric(correct, len(pairs))
    return result


def summarize_slice(rows: list[Json], pairs: list[Json]) -> Json:
    total = len(rows)
    if total not in (24, 72):
        fail(f"metric slice has unexpected size: {total}")
    strict_correct = sum(bool(row["strict_action_correct"]) for row in rows)
    contract_correct = sum(bool(row["contract_action_correct"]) for row in rows)
    full_correct = sum(bool(row["full_decision_exact"]) for row in rows)
    repetitions = sorted({int(row["repetition"]) for row in rows})
    pair_summaries = [
        _pair_metrics([row for row in rows if row["repetition"] == repetition], pairs)
        for repetition in repetitions
    ]
    pair_total = len(pairs) * len(repetitions)
    pair_summary: Json = {"pairs": pair_total}
    for endpoint in ("strict_action", "contract_action", "full_decision_exact"):
        pair_summary[endpoint] = metric(
            sum(int(summary[endpoint]["numerator"]) for summary in pair_summaries), pair_total
        )
    return {
        "scheduled_items": total,
        "action_extractable": metric(
            sum(row["action_extraction_status"] == "EXTRACTED" for row in rows), total
        ),
        "contract_valid": metric(sum(row["parse_status"] == "OK" for row in rows), total),
        "transport_errors": sum(row["transport_status"] == "ERROR" for row in rows),
        "parse_status_counts": dict(sorted(Counter(row["parse_status"] for row in rows).items())),
        "strict_action": {
            "accuracy": metric(strict_correct, total),
            "recall_by_gold_action": _recall(rows, "strict_action_correct"),
            "confusion_gold_by_terminal_prediction": _confusion(rows, contract=False),
        },
        "contract_action": {
            "accuracy": metric(contract_correct, total),
            "recall_by_gold_action": _recall(rows, "contract_action_correct"),
            "confusion_gold_by_terminal_prediction": _confusion(rows, contract=True),
        },
        "full_decision_exact": {
            "accuracy": metric(full_correct, total),
            "recall_by_gold_action": _recall(rows, "full_decision_exact"),
        },
        "pair_accuracy": pair_summary,
        "usage_totals": {
            key: sum(
                int(row["usage"][key]) for row in rows if isinstance(row["usage"].get(key), int)
            )
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_tokens",
                "total_tokens",
            )
        },
    }


def repetition_agreement(rows: list[Json], pairs: list[Json]) -> Json:
    by_item: dict[str, list[Json]] = defaultdict(list)
    for row in rows:
        by_item[str(row["item_id"])].append(row)
    if len(by_item) != 24 or any(len(item_rows) != 3 for item_rows in by_item.values()):
        fail("repeat agreement requires three records for each of twenty-four items")
    action_unanimous = 0
    decision_unanimous = 0
    all_action_correct = 0
    all_full_exact = 0
    pairwise_action_agreement = 0
    for item_rows in by_item.values():
        ordered = sorted(item_rows, key=lambda row: int(row["repetition"]))
        action_labels = [str(row.get("extracted_action") or "UNEXTRACTABLE") for row in ordered]
        decision_labels = [
            canonical_json(canonical_decision(row["full_decision"]))
            if row["parse_status"] == "OK"
            else str(row["parse_status"])
            for row in ordered
        ]
        action_unanimous += len(set(action_labels)) == 1
        decision_unanimous += len(set(decision_labels)) == 1
        all_action_correct += all(bool(row["strict_action_correct"]) for row in ordered)
        all_full_exact += all(bool(row["full_decision_exact"]) for row in ordered)
        pairwise_action_agreement += sum(
            action_labels[left] == action_labels[right] for left, right in ((0, 1), (0, 2), (1, 2))
        )
    rows_by_rep_item = {(int(row["repetition"]), str(row["item_id"])): row for row in rows}
    all_repeats_pair_correct: Json = {}
    for endpoint, field in (
        ("strict_action", "strict_action_correct"),
        ("contract_action", "contract_action_correct"),
        ("full_decision_exact", "full_decision_exact"),
    ):
        count = sum(
            all(
                all(
                    bool(rows_by_rep_item[(repetition, str(item_id))][field])
                    for item_id in pair["member_ids"]
                )
                for repetition in range(1, 4)
            )
            for pair in pairs
        )
        all_repeats_pair_correct[endpoint] = metric(count, len(pairs))
    return {
        "items": 24,
        "strict_action_unanimous_terminal_outcome": metric(action_unanimous, 24),
        "full_contract_unanimous_terminal_outcome": metric(decision_unanimous, 24),
        "strict_action_correct_in_all_three_repetitions": metric(all_action_correct, 24),
        "full_decision_exact_in_all_three_repetitions": metric(all_full_exact, 24),
        "pairwise_strict_action_terminal_agreement": metric(pairwise_action_agreement, 72),
        "pairs_correct_in_all_three_repetitions": all_repeats_pair_correct,
    }


def sanitized_rows(rows: list[Json]) -> dict[str, list[Json]]:
    grouped: dict[str, list[Json]] = defaultdict(list)
    for row in rows:
        filename = f"{row['lane_id']}-r{row['repetition']}.jsonl"
        grouped[filename].append(
            {
                "schema_version": "1.0.0",
                "study_id": STUDY_ID,
                "sequence": row["sequence"],
                "cell_id": row["cell_id"],
                "lane_id": row["lane_id"],
                "model_requested": row["model_requested"],
                "repetition": row["repetition"],
                "item_id": row["item_id"],
                "pair_id": row["pair_id"],
                "gold_action": row["gold_action"],
                "transport_status": row["transport_status"],
                "action_extraction_status": row["action_extraction_status"],
                "extracted_action": row["extracted_action"],
                "parse_status": row["parse_status"],
                "strict_action_correct": row["strict_action_correct"],
                "contract_action_correct": row["contract_action_correct"],
                "full_decision_exact": row["full_decision_exact"],
            }
        )
    return dict(grouped)


def build_analysis(
    plan_path: Path,
    schedule_path: Path,
    private_root: Path,
    journal_root: Path,
) -> tuple[Json, dict[str, list[Json]]]:
    validate_freeze(plan_path, schedule_path)
    plan = _load_object(plan_path)
    schedule = _load_object(schedule_path)
    receipt, records = load_and_validate_records(plan, schedule, private_root, journal_root)
    gold = load_jsonl(GOLD_PATH)
    gold_by_id = {str(row["id"]): row for row in gold}
    pairs = load_json(PAIRS_PATH)
    if not isinstance(pairs, list):
        fail("pair file must contain an array")
    scored = score_records(records, gold_by_id)
    lane_results: list[Json] = []
    for lane in plan["formal_lanes"]:
        lane_rows = [row for row in scored if row["lane_id"] == lane["lane_id"]]
        lane_results.append(
            {
                "lane_id": lane["lane_id"],
                "provider": lane["provider"],
                "model_requested": lane["model"],
                "model_family": lane["model_family"],
                "descriptive_three_repeat_total": summarize_slice(lane_rows, pairs),
                "by_repetition": [
                    {
                        "repetition": repetition,
                        **summarize_slice(
                            [row for row in lane_rows if row["repetition"] == repetition], pairs
                        ),
                    }
                    for repetition in range(1, 4)
                ],
                "repetition_agreement": repetition_agreement(lane_rows, pairs),
            }
        )
    aggregate: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE_ALL_SCHEDULED_CELLS_END_TO_END",
        "study_id": STUDY_ID,
        "analysis_timestamp_source": "execution-receipt.completed_at_utc",
        "analyzed_at_utc": receipt["completed_at_utc"],
        "frozen_plan_commit": receipt["frozen_plan_commit"],
        "schedule_sha256": schedule["schedule_sha256"],
        "design": "TWO_NAMED_ROUTES_BY_THREE_EXACT_REPETITIONS_ON_TWO_HISTORICAL_REVISIONS",
        "scheduled_cells": 144,
        "items_per_route_repetition": 24,
        "pairs_per_route_repetition": 12,
        "historical_revisions": 2,
        "client_retries": 0,
        "denominator_rule": (
            "Every scheduled terminal outcome remains in its route-repetition denominator."
        ),
        "endpoint_order": ["strict_action", "contract_action", "full_decision_exact"],
        "lanes": lane_results,
        "interpretation_boundary": plan["interpretation_boundary"],
        "raw_or_invalid_response_content_in_aggregate": False,
    }
    return aggregate, sanitized_rows(scored)


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _walk_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _walk_keys(child)}
    return set()


def write_results(
    out_dir: Path,
    aggregate: Json,
    public_records: dict[str, list[Json]],
) -> None:
    with atomic_output_directory(out_dir) as staging:
        aggregate_path = staging / "aggregate.json"
        aggregate_path.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        record_paths: list[Path] = []
        for filename, rows in sorted(public_records.items()):
            path = staging / "records" / filename
            write_jsonl(path, rows)
            record_paths.append(path)
        scanned = [aggregate_path, *record_paths]
        values: list[Any] = [aggregate]
        values.extend(row for rows in public_records.values() for row in rows)
        observed_keys = {key for value in values for key in _walk_keys(value)}
        forbidden_observed = sorted(FORBIDDEN_RESULT_KEYS & observed_keys)
        account_hits = [
            marker
            for marker in ACCOUNT_MARKERS
            if any(marker in path.read_text(encoding="utf-8").lower() for path in scanned)
        ]
        if forbidden_observed or account_hits:
            fail(
                f"sanitized results failed privacy scan: keys={forbidden_observed} "
                f"accounts={account_hits}"
            )
        privacy: Json = {
            "schema_version": "1.0.0",
            "status": "SANITIZED_RESULTS_PRIVACY_PASS",
            "study_id": STUDY_ID,
            "scanned_file_count": len(scanned),
            "scanned_files_sha256": {
                path.relative_to(staging).as_posix(): sha256_file(path) for path in scanned
            },
            "forbidden_result_keys": sorted(FORBIDDEN_RESULT_KEYS),
            "forbidden_result_keys_observed": [],
            "account_markers_observed": [],
            "raw_model_response_content_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_retained": False,
            "invalid_response_contents_entered_results": False,
            "credentials_loaded_for_analysis": False,
        }
        privacy_path = staging / "privacy-receipt.json"
        privacy_path.write_text(
            json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        manifested = [*scanned, privacy_path]
        manifest: Json = {
            "schema_version": "1.0.0",
            "status": "DYNAMIC_SANITIZED_RESULTS_MANIFEST",
            "study_id": STUDY_ID,
            "file_count": len(manifested) + 1,
            "hashed_file_count": len(manifested),
            "files_sha256": {
                path.relative_to(staging).as_posix(): sha256_file(path) for path in manifested
            },
            "contains_private_run_records": False,
            "contains_raw_model_responses": False,
        }
        manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=STUDY_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=STUDY_ROOT / "request-schedule.json")
    parser.add_argument("--private-root", type=Path, default=STUDY_ROOT / "private-results")
    parser.add_argument("--journal-root", type=Path, default=STUDY_ROOT / "journal")
    parser.add_argument("--out-dir", type=Path, default=STUDY_ROOT / "results")
    args = parser.parse_args()
    aggregate, records = build_analysis(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.private_root.resolve(),
        args.journal_root.resolve(),
    )
    write_results(args.out_dir.resolve(), aggregate, records)
    print(
        canonical_json(
            {
                "status": aggregate["status"],
                "lanes": len(aggregate["lanes"]),
                "scheduled_cells": aggregate["scheduled_cells"],
                "sanitized_record_files": len(records),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
