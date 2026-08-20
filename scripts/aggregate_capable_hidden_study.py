#!/usr/bin/env python3
"""Aggregate the precommitted capable-model hidden extension from item-level records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

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


def fail(message: str) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--analysis", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.plan.resolve())
    packet = load_json(args.packet.resolve())
    gold = load_jsonl(args.dataset.resolve() / "gold.jsonl")
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(gold_by_id) != int(plan["dataset"]["instances"]):
        fail("hidden gold coverage differs from the frozen plan")

    runs: dict[str, list[Json]] = {}
    run_paths: dict[str, Path] = {}
    for path in args.run:
        resolved = path.resolve()
        rows = load_jsonl(resolved)
        if not rows or {str(row["phase"]) for row in rows} != {"full"}:
            fail(f"aggregate accepts complete full runs only: {path}")
        lane_ids = {str(row["lane_id"]) for row in rows}
        if len(lane_ids) != 1:
            fail(f"run mixes lane IDs: {path}")
        lane_id = next(iter(lane_ids))
        if lane_id in runs:
            fail(f"duplicate full run for {lane_id}")
        if {str(row["item_id"]) for row in rows} != set(gold_by_id):
            fail(f"full run item coverage differs for {lane_id}")
        runs[lane_id] = rows
        run_paths[lane_id] = resolved

    required = set(plan["routing"]["required_full_lanes"])
    if set(runs) != required:
        missing = sorted(required - set(runs))
        extra = sorted(set(runs) - required)
        fail(f"full-run matrix differs: missing={missing}, extra={extra}")

    analyses: dict[str, Json] = {}
    analysis_paths: dict[str, Path] = {}
    for path in args.analysis:
        resolved = path.resolve()
        value = load_json(resolved)
        lane_id = str(value.get("lane_id"))
        if value.get("phase") != "full" or lane_id not in runs:
            fail(f"analysis does not match a full run: {path}")
        if lane_id in analyses:
            fail(f"duplicate full analysis for {lane_id}")
        if value.get("run_sha256") != sha256_file(run_paths[lane_id]):
            fail(f"analysis run digest mismatch for {lane_id}")
        analyses[lane_id] = value
        analysis_paths[lane_id] = resolved
    if set(analyses) != required:
        fail("analysis matrix differs from the full-run matrix")

    always_allow = [
        gold_by_id[item_id]["decision"]["action"] == "ALLOW" for item_id in sorted(gold_by_id)
    ]
    primary_tests: list[Json] = []
    for lane_id in PRIMARY_LANES:
        test = mcnemar_exact(always_allow, correctness_vector(runs[lane_id], gold_by_id))
        primary_tests.append({"lane_id": lane_id, **test})
    adjusted = holm_adjust([float(row["p"]) for row in primary_tests])
    for row, p_holm in zip(primary_tests, adjusted, strict=True):
        row["p_holm"] = p_holm

    pro_vector = correctness_vector(runs[DEEPSEEK_PRO], gold_by_id)
    flash_vector = correctness_vector(runs[DEEPSEEK_FLASH_MATCHED], gold_by_id)
    deepseek_tier = {
        "lane_a": DEEPSEEK_PRO,
        "lane_b": DEEPSEEK_FLASH_MATCHED,
        "accuracy_a": sum(pro_vector) / len(pro_vector),
        "accuracy_b": sum(flash_vector) / len(flash_vector),
        "delta_b_minus_a": (sum(flash_vector) - sum(pro_vector)) / len(pro_vector),
        **mcnemar_exact(pro_vector, flash_vector),
    }

    free_vector = correctness_vector(runs[DEEPSEEK_FLASH_FREE], gold_by_id)
    flash_service = {
        "lane_a": DEEPSEEK_FLASH_FREE,
        "lane_b": DEEPSEEK_FLASH_MATCHED,
        **mcnemar_exact(free_vector, flash_vector),
        **action_agreement(runs[DEEPSEEK_FLASH_FREE], runs[DEEPSEEK_FLASH_MATCHED]),
    }

    frozen_commits = {str(row["frozen_plan_commit"]) for rows in runs.values() for row in rows}
    if len(frozen_commits) != 1:
        fail("full runs do not share one frozen-plan commit")

    result: Json = {
        "schema_version": "1.0.0",
        "study_id": plan["study_id"],
        "status": "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "interpretation_boundary": plan["amendment"]["interpretation"],
        "frozen_plan": {
            "path": args.plan.resolve().relative_to(ROOT).as_posix(),
            "commit": next(iter(frozen_commits)),
            "sha256": sha256_file(args.plan.resolve()),
        },
        "dataset": {
            "manifest_sha256": sha256_file(args.dataset.resolve() / "manifest.json"),
            "inputs_sha256": sha256_file(args.dataset.resolve() / "inputs.jsonl"),
            "gold_sha256": sha256_file(args.dataset.resolve() / "gold.jsonl"),
            "pairs_sha256": sha256_file(args.dataset.resolve() / "pairs.json"),
            "instances": len(gold_by_id),
            "pairs": len(gold_by_id) // 2,
        },
        "packet_sha256": packet["packet_sha256"],
        "models": [compact_analysis(analyses[lane_id]) for lane_id in sorted(analyses)],
        "baselines": {
            "always_allow": {
                "correct": sum(always_allow),
                "trials": len(always_allow),
                "accuracy": sum(always_allow) / len(always_allow),
            }
        },
        "prespecified_tests": {
            "models_vs_always_allow_holm_family": primary_tests,
            "deepseek_same_gateway_descriptive_contrast": deepseek_tier,
            "deepseek_flash_service_replication": flash_service,
        },
        "raw_item_records_released_separately": True,
        "gate_role": plan["reporting"]["gate_interpretation"],
        "run_sha256": {lane_id: sha256_file(path) for lane_id, path in sorted(run_paths.items())},
        "analysis_sha256": {
            lane_id: sha256_file(path) for lane_id, path in sorted(analysis_paths.items())
        },
    }
    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": "COMPLETE", "models": len(analyses), "out": str(output)}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
