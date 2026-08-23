#!/usr/bin/env python3
"""Freeze two local-model replication plans before any benchmark inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from huggingface_hub import snapshot_download  # noqa: E402
from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    DATASETS,
    REQUIREMENTS_PATH,
    format_chat_prompt,
    generation_request,
    lane_id,
    load_catalog,
    load_object,
)
from transformers import AutoTokenizer  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUNTIME_PATHS = (
    "scripts/local_model_replication.py",
    "scripts/run_local_model_replication.py",
    "scripts/analyze_local_model_replication.py",
    "scripts/validate_local_model_replications.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/run_slsa_portability_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/hashing.py",
    "v2/schemas/stronger-model-run-record.schema.json",
    "v2/schemas/slsa-agent-decision.schema.json",
)


def fail(message: str) -> None:
    raise SystemExit(f"local-model-freeze: {message}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_digest(value: Json, field: str = "self_digest") -> str:
    payload = {key: child for key, child in value.items() if key != field}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def validate_receipts(catalog_path: Path, snapshot_path: Path, qualification_path: Path) -> None:
    snapshot = load_object(snapshot_path)
    qualification = load_object(qualification_path)
    catalog_hash = sha256_file(catalog_path)
    if (
        snapshot.get("status") != "PINNED_LOCAL_MODEL_SNAPSHOTS_VALIDATED"
        or snapshot.get("catalog_sha256") != catalog_hash
        or snapshot.get("self_digest") != self_digest(snapshot)
    ):
        fail("model-snapshot receipt is invalid")
    if (
        qualification.get("status")
        != "LOCAL_MODEL_ENVIRONMENT_QUALIFIED_BEFORE_BENCHMARK_INFERENCE"
        or qualification.get("catalog_sha256") != catalog_hash
        or qualification.get("snapshot_receipt_self_digest") != snapshot.get("self_digest")
        or qualification.get("benchmark_inference_calls") != 0
        or qualification.get("self_digest") != self_digest(qualification)
    ):
        fail("local environment qualification receipt is invalid")
    models = qualification.get("models")
    if (
        not isinstance(models, list)
        or len(models) != 2
        or any(row.get("load_and_generation_succeeded") is not True for row in models)
    ):
        fail("not every preselected local model passed the non-benchmark smoke test")


def load_tokenizers(catalog: Json) -> dict[str, Any]:
    tokenizers: dict[str, Any] = {}
    for lane in catalog["lanes"]:
        snapshot = snapshot_download(
            repo_id=lane["model_repo"],
            revision=lane["model_revision"],
            local_files_only=True,
        )
        tokenizers[lane["lane_stem"]] = AutoTokenizer.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=bool(lane["trust_remote_code"]),
        )
    return tokenizers


def runtime_hashes() -> Json:
    values: Json = {}
    for relative in RUNTIME_PATHS:
        path = ROOT / relative
        if not path.is_file():
            fail(f"runtime-bound source is missing: {relative}")
        values[relative] = sha256_file(path)
    return values


def build_study(
    dataset_key: str,
    catalog: Json,
    tokenizers: dict[str, Any],
    catalog_path: Path,
    snapshot_path: Path,
    qualification_path: Path,
    out_root: Path,
) -> tuple[Json, Json]:
    spec = DATASETS[dataset_key]
    dataset_root = Path(spec["dataset_root"])
    manifest = load_json(dataset_root / "manifest.json")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    if (
        manifest.get("dataset_fingerprint") != spec["expected_dataset_fingerprint"]
        or manifest.get("evaluation", {}).get("items") != 120
        or manifest.get("evaluation", {}).get("pairs") != 60
        or not isinstance(packet.get("records"), list)
        or len(packet["records"]) != 120
    ):
        fail(f"frozen source dataset changed: {dataset_key}")
    records = {str(row["item_id"]): row for row in packet["records"]}
    if len(records) != 120:
        fail(f"prompt packet item IDs are not unique: {dataset_key}")
    item_order = sorted(records)

    formal_lanes: list[Json] = []
    cells: list[Json] = []
    shared = catalog["shared_generation"]
    sequence = 0
    for lane in catalog["lanes"]:
        current_lane_id = lane_id(lane, dataset_key)
        formal_lanes.append(
            {
                "lane_id": current_lane_id,
                "provider": "Local MLX",
                "model": lane["model_repo"],
                "model_family": lane["model_family"],
                "model_revision": lane["model_revision"],
                "response_format": "prompt_only_json",
                "api_kind": "local_mlx",
                "repeated_configuration": lane["lane_stem"],
                "max_output_tokens": shared["max_output_tokens"],
                "sampler": shared["sampler"],
                "temperature": shared["temperature"],
                "top_p": shared["top_p"],
                "client_retry_count": 0,
            }
        )
        tokenizer = tokenizers[lane["lane_stem"]]
        for item_id in item_order:
            packet_row = records[item_id]
            formatted = format_chat_prompt(tokenizer, str(packet_row["prompt"]))
            request = generation_request(lane, formatted, shared)
            cells.append(
                {
                    "sequence": sequence,
                    "cell_id": f"{current_lane_id}::{item_id}",
                    "lane_id": current_lane_id,
                    "item_id": item_id,
                    "pair_id": packet_row["pair_id"],
                    "prompt_sha256": packet_row["prompt_sha256"],
                    "formatted_prompt_sha256": sha256_bytes(formatted.encode("utf-8")),
                    "request_body_sha256": sha256_bytes(canonical_json(request).encode("utf-8")),
                }
            )
            sequence += 1
    if len(cells) != 240:
        fail(f"local schedule does not contain 240 cells: {dataset_key}")
    schedule: Json = {
        "schema_version": "1.0.0",
        "status": "FROZEN_LOCAL_MODEL_REQUEST_SCHEDULE",
        "study_id": spec["study_id"],
        "order_rule": "MODEL_MAJOR_THEN_CANONICAL_ITEM_ID",
        "planned_cells": 240,
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    schedule["schedule_sha256"] = self_digest(schedule, "schedule_sha256")

    snapshot = load_object(snapshot_path)
    qualification = load_object(qualification_path)
    plan: Json = {
        "schema_version": "1.0.0",
        "status": "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION",
        "truth_status": "COMPUTATIONAL",
        "study_id": spec["study_id"],
        "purpose": spec["purpose"],
        "design": spec["design"],
        "interpretation_boundary": spec["interpretation_boundary"],
        "dataset": {
            "source_study_id": manifest["study_id"],
            "root": dataset_root.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256_file(dataset_root / "manifest.json"),
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "packet_sha256": packet["packet_sha256"],
            "evaluation_items": 120,
            "evaluation_pairs": 60,
            "evaluation_factors": 12,
            "evaluation_action_support": manifest["evaluation"]["action_counts"],
        },
        "formal_lanes": formal_lanes,
        "generation": shared,
        "statistics": {
            "primary_endpoints": ["end_to_end_item_accuracy", "end_to_end_pair_accuracy"],
            "secondary_endpoints": [
                "decision_coverage",
                "pair_coverage",
                "conditional_item_accuracy",
                "conditional_pair_accuracy",
                "per_action_recall",
                "balanced_action_recall",
                "macro_f1",
            ],
            "pair_rule": "A pair is correct only when both members are valid and action-correct.",
            "failure_rule": (
                "Every local runtime, syntax, schema, and semantic failure remains incorrect in "
                "the scheduled end-to-end denominator."
            ),
            "comparison_boundary": (
                "Model architecture, quantization, chat template, and hosted-versus-local stack "
                "differ; configuration differences are descriptive."
            ),
        },
        "execution": {
            "base_lane_order": [row["lane_id"] for row in formal_lanes],
            "planned_application_posts": 240,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "interruption_rule": "INCOMPLETE_STUDY_INELIGIBLE_FOR_MANUSCRIPT_NO_RESUME",
            "schedule_path": (
                out_root.relative_to(ROOT) / dataset_key / "request-schedule.json"
            ).as_posix(),
            "schedule_sha256": schedule["schedule_sha256"],
        },
        "freeze": {
            "catalog_sha256": sha256_file(catalog_path),
            "requirements_sha256": sha256_file(REQUIREMENTS_PATH),
            "snapshot_receipt_sha256": sha256_file(snapshot_path),
            "snapshot_receipt_self_digest": snapshot["self_digest"],
            "qualification_receipt_sha256": sha256_file(qualification_path),
            "qualification_receipt_self_digest": qualification["self_digest"],
            "benchmark_inference_calls_before_freeze": 0,
            "runtime_source_sha256": runtime_hashes(),
        },
        "selection_boundary": catalog["selection_boundary"],
        "promotion_rule": "Only all 240 sealed terminal outcomes may enter the manuscript.",
    }
    return plan, schedule


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    catalog_path = args.catalog.resolve()
    snapshot_path = args.snapshot_receipt.resolve()
    qualification_path = args.qualification_receipt.resolve()
    out_root = args.out_root.resolve()
    catalog = load_catalog(catalog_path)
    validate_receipts(catalog_path, snapshot_path, qualification_path)
    tokenizers = load_tokenizers(catalog)
    for dataset_key in DATASETS:
        plan, schedule = build_study(
            dataset_key,
            catalog,
            tokenizers,
            catalog_path,
            snapshot_path,
            qualification_path,
            out_root,
        )
        study_root = out_root / dataset_key
        write_json(study_root / "study-plan.json", plan)
        write_json(study_root / "request-schedule.json", schedule)
    print(
        canonical_json(
            {
                "status": "LOCAL_MODEL_REPLICATIONS_FROZEN",
                "studies": len(DATASETS),
                "planned_cells": 480,
                "benchmark_inference_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
