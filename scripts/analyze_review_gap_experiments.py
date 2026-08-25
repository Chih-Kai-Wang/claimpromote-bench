#!/usr/bin/env python3
"""Publish privacy-safe metrics for one completed reviewer-gap experiment."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import (  # noqa: E402
    combine_lane_metrics,
    derive_reporting_metrics,
)
from review_gap_experiments import BALANCED_DATASET, NONALLOW_ROOT, OUTPUT_ROOT  # noqa: E402
from run_factor_complete_route_breadth import atomic_output_directory  # noqa: E402
from validate_review_gap_experiments import validate_frozen  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]
STRONGER_RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
EXTERNAL_RUN_SCHEMA = ROOT / "v2" / "schemas" / "external-agent-policy-run-record.schema.json"
FORBIDDEN = re.compile(
    r"(?i)(/Users/|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"\b(?:org|user|acct|account)_[A-Za-z0-9_-]{12,}\b|"
    r"\b(?:sk|key|token)-[A-Za-z0-9_-]{16,}\b)"
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"review-gap-analysis: {message}")


def public_record(record: Json, schema: Path) -> Json:
    value = json.loads(json.dumps(record))
    value["raw_response_text"] = None
    value["provider_response_id"] = None
    value["system_fingerprint"] = None
    if value.get("transport_error") is not None:
        value["transport_error"] = "TRANSPORT_ERROR_DETAIL_WITHHELD"
    if value["parse_status"] == "OK":
        detail = value.get("parse_error_detail")
        value["parse_error_detail"] = (
            "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
            if isinstance(detail, str)
            and detail.startswith("DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION")
            else None
        )
    else:
        value["parse_error_detail"] = f"{value['parse_status']}_DETAIL_WITHHELD"
    validate_with_schema(value, schema, str(value["item_id"]))
    return cast(Json, value)


def numeric_summary(values: Sequence[int | float]) -> Json:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def route_diagnostics(records: list[Json]) -> Json:
    output_tokens = [
        int(row["usage"]["output_tokens"])
        for row in records
        if isinstance(row["usage"].get("output_tokens"), int)
    ]
    reasoning_tokens = [
        int(row["usage"]["reasoning_tokens"])
        for row in records
        if isinstance(row["usage"].get("reasoning_tokens"), int)
    ]
    visible_bytes = [
        len(str(row["raw_response_text"]).encode("utf-8"))
        for row in records
        if isinstance(row.get("raw_response_text"), str)
    ]
    finish = Counter(str(row.get("finish_reason")) for row in records)
    length_count = sum(
        isinstance(row.get("finish_reason"), str)
        and any(token in str(row["finish_reason"]).lower() for token in ("length", "token"))
        for row in records
    )
    return {
        "contract_completed": sum(row["parse_status"] == "OK" for row in records),
        "contract_completion_rate": sum(row["parse_status"] == "OK" for row in records)
        / len(records),
        "finish_reason_counts": dict(sorted(finish.items())),
        "length_termination_count": length_count,
        "length_termination_rate": length_count / len(records),
        "output_tokens": numeric_summary(output_tokens),
        "reasoning_tokens_when_reported": numeric_summary(reasoning_tokens),
        "visible_response_utf8_bytes": numeric_summary(visible_bytes),
    }


def supported_action_metrics(metrics: Json) -> Json:
    """Add macro summaries over gold-supported actions without hiding four-class counts."""

    value = cast(Json, json.loads(json.dumps(metrics)))
    supported = [
        action
        for action in value["confusion_matrix"]["row_order"]
        if int(value["per_action"][action]["gold_instances"]) > 0
    ]
    if not supported:
        fail("metric set has no gold-supported actions")
    value["supported_action_order"] = supported
    value["supported_balanced_action_recall"] = statistics.fmean(
        float(value["per_action"][action]["end_to_end_recall"]) for action in supported
    )
    value["supported_conditional_balanced_action_recall"] = statistics.fmean(
        float(value["per_action"][action]["conditional_recall"]) for action in supported
    )
    value["supported_macro_f1"] = statistics.fmean(
        float(value["per_action"][action]["end_to_end_f1"]) for action in supported
    )
    value["supported_conditional_macro_f1"] = statistics.fmean(
        float(value["per_action"][action]["conditional_f1"]) for action in supported
    )
    return value


def subset_metrics(gold: list[Json], pairs: list[Json], records: list[Json], changed: bool) -> Json:
    chosen_pairs = [row for row in pairs if bool(row["changed"]) is changed]
    ids = {str(value) for row in chosen_pairs for value in row["member_ids"]}
    return supported_action_metrics(
        derive_reporting_metrics(
            [row for row in gold if str(row["id"]) in ids],
            chosen_pairs,
            [row for row in records if str(row["item_id"]) in ids],
        )
    )


def fake_records(gold: list[Json], pairs: list[Json], mode: str) -> list[Json]:
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
    predicted: dict[str, str] = {}
    if mode == "ALWAYS_ALLOW":
        predicted = {item_id: "ALLOW" for item_id in gold_by_id}
    elif mode == "COPY_BEFORE_ACTION_TO_AFTER":
        for pair in pairs:
            members = [str(value) for value in pair["member_ids"]]
            before = next(value for value in members if value.endswith("-before"))
            for member in members:
                predicted[member] = gold_by_id[before]
    else:
        fail(f"unknown offline baseline: {mode}")
    return [
        {
            "item_id": item_id,
            "parse_status": "OK",
            "raw_decision": {"action": predicted[item_id]},
        }
        for item_id in sorted(predicted)
    ]


def all_three_full_policy(
    lane_records: dict[str, list[Json]], lanes: list[Json], gold: list[Json], pairs: list[Json]
) -> Json:
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
    by_model: list[Json] = []
    for model in sorted({str(row["model"]) for row in lanes}):
        selected = [
            row
            for row in lanes
            if row["model"] == model and str(row["condition_id"]).startswith("full-policy-r")
        ]
        if len(selected) != 3:
            fail(f"full-policy replication coverage changed: {model}")
        records_by_rep = {
            int(row["replication"]): {
                str(value["item_id"]): value for value in lane_records[str(row["lane_id"])]
            }
            for row in selected
        }
        correct_items = sum(
            all(
                records_by_rep[rep][item_id]["parse_status"] == "OK"
                and records_by_rep[rep][item_id]["raw_decision"]["action"] == action
                for rep in (1, 2, 3)
            )
            for item_id, action in gold_by_id.items()
        )
        correct_pairs = 0
        for pair in pairs:
            members = [str(value) for value in pair["member_ids"]]
            correct_pairs += all(
                records_by_rep[rep][item_id]["parse_status"] == "OK"
                and records_by_rep[rep][item_id]["raw_decision"]["action"] == gold_by_id[item_id]
                for rep in (1, 2, 3)
                for item_id in members
            )
        by_model.append(
            {
                "model_requested": model,
                "all_three_correct_items": correct_items,
                "items": len(gold_by_id),
                "all_three_correct_pairs": correct_pairs,
                "pairs": len(pairs),
            }
        )
    return {"by_model": by_model}


def analyze(root: Path, private_dir: Path, output_dir: Path) -> Json:
    plan = load_json(root / "study-plan.json")
    schedule = load_json(root / "request-schedule.json")
    receipt = load_json(private_dir / "execution-receipt.json")
    validate_frozen(root, frozen_commit=str(receipt.get("frozen_plan_commit", "")))
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != plan["study_id"]
        or receipt.get("schedule_sha256") != schedule["schedule_sha256"]
        or receipt.get("planned_cells") != schedule["planned_cells"]
        or receipt.get("application_posts") != schedule["planned_cells"]
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
    ):
        fail("execution receipt is incomplete or changed")
    output_study = root.resolve() == OUTPUT_ROOT.resolve()
    dataset = BALANCED_DATASET if output_study else NONALLOW_ROOT / "dataset"
    run_schema = STRONGER_RUN_SCHEMA if output_study else EXTERNAL_RUN_SCHEMA
    gold_all = load_jsonl(dataset / "gold.jsonl")
    pairs_all = load_json(dataset / "pairs.json")
    if not isinstance(pairs_all, list):
        fail("pair file is not a list")
    selected_ids = set(schedule["selected_item_ids"])
    selected_pairs = [
        row for row in pairs_all if str(row["pair_id"]) in schedule["selected_pair_ids"]
    ]
    gold = [row for row in gold_all if str(row["id"]) in selected_ids]
    lanes = plan["formal_lanes"]
    lane_records: dict[str, list[Json]] = {}
    lane_rows: list[Json] = []
    public_files: list[Path] = []
    all_costs: list[float] = []
    with atomic_output_directory(output_dir) as staging:
        runs_dir = staging / "runs"
        runs_dir.mkdir(parents=True)
        for lane in lanes:
            lane_id = str(lane["lane_id"])
            source = private_dir / f"{lane_id}.jsonl"
            if receipt["lane_output_sha256"].get(source.name) != sha256_file(source):
                fail(f"private lane digest changed: {source.name}")
            records = load_jsonl(source)
            lane_records[lane_id] = records
            metrics = derive_reporting_metrics(gold, selected_pairs, records)
            if not output_study:
                metrics = supported_action_metrics(metrics)
            costs = [
                float(row["actual_cost_usd"])
                for row in records
                if isinstance(row.get("actual_cost_usd"), (int, float))
            ]
            all_costs.extend(costs)
            lane_rows.append(
                {
                    "lane_id": lane_id,
                    "condition_id": lane["condition_id"],
                    "replication": lane["replication"],
                    "model_requested": lane["model"],
                    "model_family": lane["model_family"],
                    "response_format": lane["response_format"],
                    "prompt_variant": lane["prompt_variant"],
                    "max_output_tokens": lane["max_output_tokens"],
                    "metrics": metrics,
                    "route_diagnostics": route_diagnostics(records),
                    "host_usage_derived_quota_value_usd": sum(costs)
                    if len(costs) == len(records)
                    else None,
                    "run_sha256": sha256_file(source),
                }
            )
            public_path = runs_dir / source.name
            write_jsonl(public_path, [public_record(row, run_schema) for row in records])
            public_files.append(public_path)
        aggregate: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE",
            "truth_status": "COMPUTATIONAL",
            "study_id": plan["study_id"],
            "interpretation_boundary": plan["interpretation_boundary"],
            "freeze": {
                "frozen_plan_commit": receipt["frozen_plan_commit"],
                "plan_sha256": sha256_file(root / "study-plan.json"),
                "schedule_sha256": schedule["schedule_sha256"],
                "execution_receipt_sha256": sha256_file(private_dir / "execution-receipt.json"),
            },
            "execution": {
                "scheduled_cells": schedule["planned_cells"],
                "application_posts": receipt["application_posts"],
                "client_retries": 0,
                "partial_resume_used": False,
            },
            "failure_rule": plan["statistics"]["failure_rule"],
            "lanes": sorted(lane_rows, key=lambda row: str(row["lane_id"])),
            "budget": {
                "billing_mode": "OPENCODE_GO_LEDGER_MODE_NOT_RETURNED_PER_RESPONSE",
                "host_usage_derived_quota_value_usd": sum(all_costs),
                "incremental_cash_spend_usd": None,
                "incremental_cash_spend_observable": False,
            },
            "raw_prompts_or_responses_in_aggregate": False,
        }
        if output_study:
            by_model: list[Json] = []
            for model in sorted({str(row["model_requested"]) for row in lane_rows}):
                rows = [row for row in lane_rows if row["model_requested"] == model]
                baseline = next(row for row in rows if row["condition_id"] == "prompt-4096")
                base_records = {
                    str(row["item_id"]): row for row in lane_records[str(baseline["lane_id"])]
                }
                gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
                comparisons: list[Json] = []
                for row in sorted(rows, key=lambda value: str(value["condition_id"])):
                    current = {
                        str(value["item_id"]): value for value in lane_records[str(row["lane_id"])]
                    }
                    wins = losses = 0
                    pair_wins = pair_losses = 0
                    for item_id, action in gold_by_id.items():
                        base_correct = (
                            base_records[item_id]["parse_status"] == "OK"
                            and base_records[item_id]["raw_decision"]["action"] == action
                        )
                        current_correct = (
                            current[item_id]["parse_status"] == "OK"
                            and current[item_id]["raw_decision"]["action"] == action
                        )
                        wins += current_correct and not base_correct
                        losses += base_correct and not current_correct
                    for pair in selected_pairs:
                        member_ids = [str(value) for value in pair["member_ids"]]
                        base_pair_correct = all(
                            base_records[item_id]["parse_status"] == "OK"
                            and base_records[item_id]["raw_decision"]["action"]
                            == gold_by_id[item_id]
                            for item_id in member_ids
                        )
                        current_pair_correct = all(
                            current[item_id]["parse_status"] == "OK"
                            and current[item_id]["raw_decision"]["action"]
                            == gold_by_id[item_id]
                            for item_id in member_ids
                        )
                        pair_wins += current_pair_correct and not base_pair_correct
                        pair_losses += base_pair_correct and not current_pair_correct
                    comparisons.append(
                        {
                            "condition_id": row["condition_id"],
                            "correct_item_delta_vs_prompt_4096": int(
                                row["metrics"]["correct_items"]
                            )
                            - int(baseline["metrics"]["correct_items"]),
                            "paired_item_wins": wins,
                            "paired_item_losses": losses,
                            "correct_pair_delta_vs_prompt_4096": int(
                                row["metrics"]["correct_pairs"]
                            )
                            - int(baseline["metrics"]["correct_pairs"]),
                            "paired_pair_wins": pair_wins,
                            "paired_pair_losses": pair_losses,
                            "registered_primary_contrast": row["condition_id"]
                            == "prompt-12288",
                        }
                    )
                by_model.append(
                    {
                        "model_requested": model,
                        "conditions": sorted(rows, key=lambda value: str(value["condition_id"])),
                        "paired_comparisons": comparisons,
                    }
                )
            aggregate["output_contract_ablation"] = {"by_model": by_model}
        else:
            primary: list[Json] = []
            controls: list[Json] = []
            pooled: list[Json] = []
            for model in sorted({str(row["model_requested"]) for row in lane_rows}):
                model_rows = [row for row in lane_rows if row["model_requested"] == model]
                first = next(row for row in model_rows if row["condition_id"] == "full-policy-r1")
                first_records = lane_records[str(first["lane_id"])]
                primary.append(
                    {
                        **first,
                        "stable_controls": subset_metrics(
                            gold, selected_pairs, first_records, False
                        ),
                        "changed_pairs": subset_metrics(gold, selected_pairs, first_records, True),
                    }
                )
                full_rows = [
                    row
                    for row in model_rows
                    if str(row["condition_id"]).startswith("full-policy-r")
                ]
                pooled_metrics = supported_action_metrics(
                    combine_lane_metrics([row["metrics"] for row in full_rows])
                )
                pooled_stable = supported_action_metrics(
                    combine_lane_metrics(
                        [
                            subset_metrics(
                                gold,
                                selected_pairs,
                                lane_records[str(row["lane_id"])],
                                False,
                            )
                            for row in full_rows
                        ]
                    )
                )
                pooled_changed = supported_action_metrics(
                    combine_lane_metrics(
                        [
                            subset_metrics(
                                gold,
                                selected_pairs,
                                lane_records[str(row["lane_id"])],
                                True,
                            )
                            for row in full_rows
                        ]
                    )
                )
                pooled.append(
                    {
                        "model_requested": model,
                        "metrics": pooled_metrics,
                        "stable_controls": pooled_stable,
                        "changed_pairs": pooled_changed,
                    }
                )
                controls.extend(
                    row
                    for row in model_rows
                    if row["condition_id"] in {"case-only", "source-shuffled"}
                )
            offline = []
            for mode in ("ALWAYS_ALLOW", "COPY_BEFORE_ACTION_TO_AFTER"):
                records = fake_records(gold, selected_pairs, mode)
                offline.append(
                    {
                        "baseline": mode,
                        "label": "DETERMINISTIC_OFFLINE_CONTROL_NOT_A_LEARNED_BASELINE",
                        "metrics": supported_action_metrics(
                            derive_reporting_metrics(gold, selected_pairs, records)
                        ),
                        "stable_controls": subset_metrics(gold, selected_pairs, records, False),
                        "changed_pairs": subset_metrics(gold, selected_pairs, records, True),
                    }
                )
            aggregate["nonallow_policy_controls"] = {
                "primary_pooled_three_replications": pooled,
                "secondary_replication_one": primary,
                "negative_controls_one_replication": controls,
                "all_three_correct": all_three_full_policy(
                    lane_records, lanes, gold, selected_pairs
                ),
                "offline_baselines": offline,
                "label_provenance": (
                    "Author policy mapping; no policy-owner labels, human annotators, "
                    "or agreement statistic."
                ),
            }
        write_path = staging / "aggregate.json"
        write_path.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        public_files.append(write_path)
        execution_copy = json.loads(json.dumps(receipt))
        execution_copy["lane_output_sha256"] = {
            path.name: sha256_file(path)
            for path in sorted(public_files)
            if path.parent.name == "runs"
        }
        execution_copy["private_journal_hashes_withheld"] = True
        execution_copy["request_intent_journal_sha256"] = None
        execution_copy["terminal_journal_sha256"] = None
        execution_path = staging / "execution-receipt.json"
        execution_path.write_text(
            json.dumps(execution_copy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        public_files.append(execution_path)
        for path in public_files:
            text = path.read_text(encoding="utf-8")
            if FORBIDDEN.search(text) or '"raw_response_text": "' in text:
                fail(f"privacy scan failed: {path.name}")
        privacy: Json = {
            "schema_version": "1.0.0",
            "status": "PASS",
            "files_scanned": len(public_files),
            "raw_response_text_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_retained": False,
            "credentials_or_account_identifiers_found": False,
            "file_sha256": {
                path.relative_to(staging).as_posix(): sha256_file(path)
                for path in sorted(public_files)
            },
        }
        (staging / "privacy-receipt.json").write_text(
            json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        canonical_json(
            {
                "status": "COMPLETE",
                "study_id": plan["study_id"],
                "lanes": len(lane_rows),
                "records": schedule["planned_cells"],
                "quota_value_usd": sum(all_costs),
            }
        )
    )
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.root.resolve(), args.private_dir.resolve(), args.out_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
