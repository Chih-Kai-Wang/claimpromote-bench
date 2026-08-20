#!/usr/bin/env python3
"""Aggregate the capable-model extension without hiding qualification failures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402
from claimpromotebench.statistics import holm_adjust, mcnemar_exact  # noqa: E402

Json = dict[str, Any]

PRIMARY_LANES = (
    "opencode-go-qwen3.7-max",
    "opencode-go-glm-5.2",
    "opencode-go-deepseek-v4-pro",
    "opencode-go-deepseek-v4-flash-matched",
    "opencode-go-hy3",
    "opencode-go-muse-spark-1.2-contributor",
)
DEEPSEEK_PRO = "opencode-go-deepseek-v4-pro"
DEEPSEEK_FLASH_MATCHED = "opencode-go-deepseek-v4-flash-matched"
DEEPSEEK_FLASH_FREE = "bai-deepseek-v4-flash-primary"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"capable-hidden-aggregate: {message}")


def correctness_vector(rows: list[Json], gold_by_id: dict[str, Json]) -> list[bool]:
    by_id = {str(row["item_id"]): row for row in rows}
    return [
        bool(
            by_id[item_id]["parse_status"] == "OK"
            and by_id[item_id]["raw_decision"]["action"]
            == gold_by_id[item_id]["decision"]["action"]
        )
        for item_id in sorted(gold_by_id)
    ]


def action_agreement(rows_a: list[Json], rows_b: list[Json]) -> Json:
    by_a = {str(row["item_id"]): row for row in rows_a}
    by_b = {str(row["item_id"]): row for row in rows_b}
    if set(by_a) != set(by_b):
        fail("service-replication item coverage differs")
    covered = [
        item_id
        for item_id in sorted(by_a)
        if by_a[item_id]["parse_status"] == "OK" and by_b[item_id]["parse_status"] == "OK"
    ]
    agreements = sum(
        by_a[item_id]["raw_decision"]["action"] == by_b[item_id]["raw_decision"]["action"]
        for item_id in covered
    )
    return {
        "both_parseable": len(covered),
        "action_agreements": agreements,
        "action_agreement_rate": agreements / len(covered) if covered else None,
    }


def compact_analysis(analysis: Json) -> Json:
    metrics = analysis["metrics"]
    complete = analysis["complete_metrics"]
    secondary = complete["secondary"]
    return {
        "lane_id": analysis["lane_id"],
        "provider": analysis["provider"],
        "model_requested": analysis["model_requested"],
        "model_returned_values": analysis["model_returned_values"],
        "frozen_plan_commit": analysis["frozen_plan_commit"],
        "run_sha256": analysis["run_sha256"],
        "records": analysis["records"],
        "status_counts": metrics["status_counts"],
        "raw_action_distribution": analysis["raw_action_distribution"],
        "end_to_end": complete["end_to_end"],
        "decision_coverage": metrics["decision_coverage"],
        "pair_coverage": metrics["pair_coverage"],
        "conditional_raw_action_accuracy": metrics["raw_action_accuracy"],
        "conditional_raw_pair_accuracy": metrics["raw_pair_accuracy"],
        "raw_false_promotion_rate": metrics["raw_fpr"],
        "raw_valid_promotion_rate": metrics["raw_vpr"],
        "reason_code_instance_set_f1": secondary["reason_code_instance_set_f1"],
        "evidence_id_macro_precision": secondary["evidence_id_macro_precision"],
        "evidence_id_macro_recall": secondary["evidence_id_macro_recall"],
        "missing_evidence_exact_match": secondary["missing_evidence_exact_match"],
        "brier": secondary["brier"],
        "nll": secondary["nll"],
        "uncertainty": analysis["uncertainty"],
        "usage": analysis["usage"],
        "quota_or_reference_value": analysis["cost"],
    }


def compact_pilot(analysis: Json) -> Json:
    gate = analysis["continuation_gate"]
    return {
        "lane_id": analysis["lane_id"],
        "provider": analysis["provider"],
        "model_requested": analysis["model_requested"],
        "frozen_plan_commit": analysis["frozen_plan_commit"],
        "run_sha256": analysis["run_sha256"],
        "records": analysis["records"],
        "status_counts": analysis["metrics"]["status_counts"],
        "continuation_gate": {
            "decision": gate["decision"],
            "transport_errors": gate["transport_errors"],
            "parseable_decisions": gate["parseable_decisions"],
            "required_parseable_decisions": gate["required_parseable_decisions"],
            "accuracy_used_by_gate": gate["accuracy_used_by_gate"],
            "action_distribution_used_by_gate": gate["action_distribution_used_by_gate"],
        },
    }


def load_runs(
    paths: list[Path], phase: str, expected_ids: set[str] | None, expected_count: int
) -> tuple[dict[str, list[Json]], dict[str, Path]]:
    runs: dict[str, list[Json]] = {}
    run_paths: dict[str, Path] = {}
    item_sets: list[set[str]] = []
    for path in paths:
        resolved = path.resolve()
        rows = load_jsonl(resolved)
        if not rows or {str(row["phase"]) for row in rows} != {phase}:
            fail(f"expected a {phase} run: {path}")
        lane_ids = {str(row["lane_id"]) for row in rows}
        if len(lane_ids) != 1:
            fail(f"run mixes lane IDs: {path}")
        lane_id = next(iter(lane_ids))
        if lane_id in runs:
            fail(f"duplicate {phase} run for {lane_id}")
        item_ids = {str(row["item_id"]) for row in rows}
        if len(rows) != expected_count or len(item_ids) != expected_count:
            fail(f"{phase} run coverage count differs for {lane_id}")
        if expected_ids is not None and item_ids != expected_ids:
            fail(f"{phase} run item coverage differs for {lane_id}")
        item_sets.append(item_ids)
        runs[lane_id] = rows
        run_paths[lane_id] = resolved
    if phase == "pilot" and item_sets and any(value != item_sets[0] for value in item_sets[1:]):
        fail("pilot item coverage differs across lanes")
    return runs, run_paths


def load_analyses(
    paths: list[Path], phase: str, runs: dict[str, list[Json]], run_paths: dict[str, Path]
) -> tuple[dict[str, Json], dict[str, Path]]:
    analyses: dict[str, Json] = {}
    analysis_paths: dict[str, Path] = {}
    for path in paths:
        resolved = path.resolve()
        value = load_json(resolved)
        lane_id = str(value.get("lane_id"))
        if value.get("phase") != phase or lane_id not in runs:
            fail(f"analysis does not match a {phase} run: {path}")
        if lane_id in analyses:
            fail(f"duplicate {phase} analysis for {lane_id}")
        if value.get("run_sha256") != sha256_file(run_paths[lane_id]):
            fail(f"analysis run digest mismatch for {lane_id}")
        analyses[lane_id] = value
        analysis_paths[lane_id] = resolved
    if set(analyses) != set(runs):
        fail(f"{phase} analysis matrix differs from its run matrix")
    return analyses, analysis_paths


def unavailable_contrast(lanes: set[str], required: set[str]) -> Json:
    return {
        "status": "NOT_AVAILABLE",
        "reason": (
            "One or more prespecified lanes did not pass the accuracy-blind continuation gate."
        ),
        "missing_full_lanes": sorted(required - lanes),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--pilot-run", type=Path, action="append", required=True)
    parser.add_argument("--pilot-analysis", type=Path, action="append", required=True)
    parser.add_argument("--full-run", type=Path, action="append", default=[])
    parser.add_argument("--full-analysis", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.plan.resolve())
    packet = load_json(args.packet.resolve())
    gold = load_jsonl(args.dataset.resolve() / "gold.jsonl")
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(gold_by_id) != int(plan["dataset"]["instances"]):
        fail("hidden gold coverage differs from the frozen plan")

    formal_lanes = {str(row["lane_id"]) for row in plan["formal_lanes"]}
    pilot_runs, pilot_run_paths = load_runs(
        args.pilot_run, "pilot", None, int(plan["pilot"]["instances"])
    )
    if set(pilot_runs) != formal_lanes:
        fail("pilot evidence must cover every registered formal lane")
    pilot_analyses, pilot_analysis_paths = load_analyses(
        args.pilot_analysis, "pilot", pilot_runs, pilot_run_paths
    )

    gate_go = {
        lane_id
        for lane_id, value in pilot_analyses.items()
        if value["continuation_gate"]["decision"] == "GO"
    }
    full_runs, full_run_paths = load_runs(
        args.full_run, "full", set(gold_by_id), int(plan["dataset"]["instances"])
    )
    if set(full_runs) != gate_go:
        fail(
            "full-run matrix must equal the accuracy-blind GO set: "
            f"missing={sorted(gate_go - set(full_runs))}, "
            f"extra={sorted(set(full_runs) - gate_go)}"
        )
    full_analyses, full_analysis_paths = load_analyses(
        args.full_analysis, "full", full_runs, full_run_paths
    )

    packet_sha = str(packet["packet_sha256"])
    for value in [*pilot_analyses.values(), *full_analyses.values()]:
        if str(value["packet_sha256"]) != packet_sha:
            fail(f"analysis packet digest differs for {value['lane_id']}")

    always_allow = [
        gold_by_id[item_id]["decision"]["action"] == "ALLOW" for item_id in sorted(gold_by_id)
    ]
    completed_primary = [lane_id for lane_id in PRIMARY_LANES if lane_id in full_runs]
    primary_tests: list[Json] = []
    for lane_id in completed_primary:
        test = mcnemar_exact(always_allow, correctness_vector(full_runs[lane_id], gold_by_id))
        primary_tests.append({"lane_id": lane_id, **test})
    adjusted = holm_adjust([float(row["p"]) for row in primary_tests]) if primary_tests else []
    for row, p_holm in zip(primary_tests, adjusted, strict=True):
        row["p_holm_within_completed_family"] = p_holm

    completed = set(full_runs)
    tier_required = {DEEPSEEK_PRO, DEEPSEEK_FLASH_MATCHED}
    if tier_required <= completed:
        pro_vector = correctness_vector(full_runs[DEEPSEEK_PRO], gold_by_id)
        flash_vector = correctness_vector(full_runs[DEEPSEEK_FLASH_MATCHED], gold_by_id)
        deepseek_tier: Json = {
            "status": "AVAILABLE_DESCRIPTIVE_ONLY",
            "lane_a": DEEPSEEK_PRO,
            "lane_b": DEEPSEEK_FLASH_MATCHED,
            "accuracy_a": sum(pro_vector) / len(pro_vector),
            "accuracy_b": sum(flash_vector) / len(flash_vector),
            "delta_b_minus_a": (sum(flash_vector) - sum(pro_vector)) / len(pro_vector),
            **mcnemar_exact(pro_vector, flash_vector),
        }
    else:
        deepseek_tier = unavailable_contrast(completed, tier_required)

    service_required = {DEEPSEEK_FLASH_FREE, DEEPSEEK_FLASH_MATCHED}
    if service_required <= completed:
        free_vector = correctness_vector(full_runs[DEEPSEEK_FLASH_FREE], gold_by_id)
        flash_vector = correctness_vector(full_runs[DEEPSEEK_FLASH_MATCHED], gold_by_id)
        flash_service: Json = {
            "status": "AVAILABLE_REPLICATION_ONLY",
            "lane_a": DEEPSEEK_FLASH_FREE,
            "lane_b": DEEPSEEK_FLASH_MATCHED,
            **mcnemar_exact(free_vector, flash_vector),
            **action_agreement(full_runs[DEEPSEEK_FLASH_FREE], full_runs[DEEPSEEK_FLASH_MATCHED]),
        }
    else:
        flash_service = unavailable_contrast(completed, service_required)

    result: Json = {
        "schema_version": "1.1.0",
        "study_id": plan["study_id"],
        "status": "COMPLETE_WITH_QUALIFICATION_FAILURES"
        if completed != formal_lanes
        else "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "interpretation_boundary": plan["amendment"]["interpretation"],
        "collection_rule": (
            "All registered pilots are retained. A full run is required exactly when the "
            "accuracy-blind continuation gate is GO; STOP is not converted to a 300-item score."
        ),
        "dataset": {
            "manifest_sha256": sha256_file(args.dataset.resolve() / "manifest.json"),
            "inputs_sha256": sha256_file(args.dataset.resolve() / "inputs.jsonl"),
            "gold_sha256": sha256_file(args.dataset.resolve() / "gold.jsonl"),
            "pairs_sha256": sha256_file(args.dataset.resolve() / "pairs.json"),
            "instances": len(gold_by_id),
            "pairs": len(gold_by_id) // 2,
        },
        "packet_sha256": packet_sha,
        "qualification": {
            "attempted_lanes": sorted(formal_lanes),
            "go_lanes": sorted(gate_go),
            "stop_lanes": sorted(formal_lanes - gate_go),
            "pilots": [compact_pilot(pilot_analyses[lane]) for lane in sorted(formal_lanes)],
        },
        "models_with_complete_hidden_pass": [
            compact_analysis(full_analyses[lane_id]) for lane_id in sorted(full_analyses)
        ],
        "baselines": {
            "always_allow": {
                "correct": sum(always_allow),
                "trials": len(always_allow),
                "accuracy": sum(always_allow) / len(always_allow),
            }
        },
        "prespecified_tests": {
            "models_vs_always_allow": {
                "status": "PARTIAL_FAMILY"
                if len(completed_primary) != len(PRIMARY_LANES)
                else "COMPLETE_FAMILY",
                "registered_lanes": list(PRIMARY_LANES),
                "completed_lanes": completed_primary,
                "missing_due_to_qualification": [
                    lane_id for lane_id in PRIMARY_LANES if lane_id not in full_runs
                ],
                "holm_scope": "completed lanes only; not the originally planned six-test family",
                "tests": primary_tests,
            },
            "deepseek_same_gateway_descriptive_contrast": deepseek_tier,
            "deepseek_flash_service_replication": flash_service,
        },
        "raw_item_records_released_separately": True,
        "gate_role": plan["reporting"]["gate_interpretation"],
        "provenance": {
            "pilot_run_sha256": {
                lane: sha256_file(path) for lane, path in sorted(pilot_run_paths.items())
            },
            "pilot_analysis_sha256": {
                lane: sha256_file(path) for lane, path in sorted(pilot_analysis_paths.items())
            },
            "full_run_sha256": {
                lane: sha256_file(path) for lane, path in sorted(full_run_paths.items())
            },
            "full_analysis_sha256": {
                lane: sha256_file(path) for lane, path in sorted(full_analysis_paths.items())
            },
            "frozen_plan_commits": {
                lane: pilot_analyses[lane]["frozen_plan_commit"] for lane in sorted(formal_lanes)
            },
        },
    }
    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "attempted": len(formal_lanes),
                "full": len(full_analyses),
                "out": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
