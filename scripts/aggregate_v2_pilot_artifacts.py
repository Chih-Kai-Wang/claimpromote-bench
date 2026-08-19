#!/usr/bin/env python3
"""Aggregate a complete v2 public pilot from downloaded GitHub Actions artifacts.

This script never calls a model. It validates every raw-response run record, recomputes all
coverage and controlled-pair metrics, proves the free/constrained prompt identity, and emits a
public-safe aggregate that contains no raw model text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
)
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402
from claimpromotebench.v2 import summarize_pilot  # noqa: E402

Json = dict[str, Any]
Identity = tuple[str, str, int]
EXPECTED_MODELS = {"Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"}
EXPECTED_MODES = {"free", "json_schema"}
EXPECTED_SEED = 104729
EXPECTED_RECORDS_PER_RUN = 40


def fail(message: str) -> None:
    raise SystemExit(f"v2-pilot-aggregate: {message}")


def digest_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def discover_runs(root: Path) -> list[Path]:
    candidates = sorted(
        path
        for path in root.rglob("*.jsonl")
        if path.is_file() and ("free" in path.name or "json_schema" in path.name)
    )
    if len(candidates) != 4:
        fail(f"expected four pilot run JSONL files, found {len(candidates)}")
    return candidates


def validate_records(records: list[Json], run_path: Path, schema_path: Path) -> Identity:
    if len(records) != EXPECTED_RECORDS_PER_RUN:
        fail(f"{run_path} has {len(records)} records; expected {EXPECTED_RECORDS_PER_RUN}")
    for index, record in enumerate(records):
        validate_with_schema(record, schema_path, f"{run_path}:{index + 1}")

    models = {str(row["model_id"]) for row in records}
    modes = {str(row["decoding_mode"]) for row in records}
    seeds = {int(row["seed"]) for row in records}
    arms = {str(row["prompt_arm"]) for row in records}
    if len(models) != 1 or len(modes) != 1 or len(seeds) != 1 or arms != {"ledger_verifier"}:
        fail(f"mixed run identity in {run_path}")
    identity = (next(iter(models)), next(iter(modes)), next(iter(seeds)))
    if identity[0] not in EXPECTED_MODELS:
        fail(f"unexpected model in {run_path}: {identity[0]}")
    if identity[1] not in EXPECTED_MODES or identity[2] != EXPECTED_SEED:
        fail(f"unexpected mode/seed in {run_path}: {identity[1:]}")

    item_ids = [str(row["item_id"]) for row in records]
    if len(set(item_ids)) != EXPECTED_RECORDS_PER_RUN:
        fail(f"duplicate item_id in {run_path}")
    response_hashes = {row.get("response_format_sha256") for row in records}
    if identity[1] == "free" and response_hashes != {None}:
        fail(f"free run contains a response-format constraint: {run_path}")
    if identity[1] == "json_schema" and (len(response_hashes) != 1 or None in response_hashes):
        fail(f"constrained run lacks one fixed response-format hash: {run_path}")
    return identity


def compare_modes(free_records: list[Json], constrained_records: list[Json]) -> Json:
    free_by_id = {str(row["item_id"]): row for row in free_records}
    constrained_by_id = {str(row["item_id"]): row for row in constrained_records}
    if set(free_by_id) != set(constrained_by_id):
        fail("free and constrained modes cover different item IDs")

    invariant_fields = (
        "model_id",
        "model_artifact_sha256",
        "quantization",
        "runtime_commit",
        "prompt_arm",
        "seed",
        "hardware",
    )
    for item_id in sorted(free_by_id):
        free = free_by_id[item_id]
        constrained = constrained_by_id[item_id]
        if free["prompt_sha256"] != constrained["prompt_sha256"]:
            fail(f"prompt hash differs between decoding modes for {item_id}")
        for field in invariant_fields:
            if free.get(field) != constrained.get(field):
                fail(f"{field} differs between decoding modes for {item_id}")

    return {
        "status": "PASS",
        "items_compared": len(free_by_id),
        "prompt_hashes_identical": True,
        "model_runtime_seed_hardware_identical": True,
        "only_registered_difference": "response_format",
    }


def delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def public_summary(summary: Json) -> Json:
    return {
        key: summary[key]
        for key in (
            "records",
            "status_counts",
            "decision_coverage",
            "raw_action_accuracy",
            "postgate_action_accuracy",
            "raw_fpr",
            "raw_vpr",
            "pairs",
            "covered_pairs",
            "pair_coverage",
            "raw_pair_accuracy",
            "postgate_pair_accuracy",
            "raw_flip_rate",
            "factor_metrics",
            "pair_metrics",
        )
    }


def build(artifact_root: Path, dataset_dir: Path, workflow_run_id: int) -> Json:
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        fail("pairs.json must contain a list")
    if len(gold) != 40 or len(pairs) != 20:
        fail("pilot dataset is not the frozen 40-instance / 20-pair alpha set")

    schema_path = ROOT / "v2" / "schemas" / "run-record-v2.schema.json"
    records_by_identity: dict[Identity, list[Json]] = {}
    run_path_by_identity: dict[Identity, Path] = {}
    for run_path in discover_runs(artifact_root):
        records = load_jsonl(run_path)
        identity = validate_records(records, run_path, schema_path)
        if identity in records_by_identity:
            fail(f"duplicate run identity: {identity}")
        records_by_identity[identity] = records
        run_path_by_identity[identity] = run_path

    expected = {
        (model, mode, EXPECTED_SEED) for model in EXPECTED_MODELS for mode in EXPECTED_MODES
    }
    if set(records_by_identity) != expected:
        missing = sorted(expected - set(records_by_identity))
        extra = sorted(set(records_by_identity) - expected)
        fail(f"pilot matrix mismatch: missing={missing}, extra={extra}")

    runs: list[Json] = []
    comparisons: list[Json] = []
    aggregate_status_counts: Counter[str] = Counter()
    for identity in sorted(records_by_identity):
        records = records_by_identity[identity]
        summary = summarize_pilot(gold, pairs, records)
        aggregate_status_counts.update(str(row["parse_status"]) for row in records)
        runs.append(
            {
                "model_id": identity[0],
                "decoding_mode": identity[1],
                "seed": identity[2],
                "run_sha256": sha256_file(run_path_by_identity[identity]),
                "summary": public_summary(summary),
            }
        )

    for model in sorted(EXPECTED_MODELS):
        free_identity = (model, "free", EXPECTED_SEED)
        constrained_identity = (model, "json_schema", EXPECTED_SEED)
        free_records = records_by_identity[free_identity]
        constrained_records = records_by_identity[constrained_identity]
        invariants = compare_modes(free_records, constrained_records)
        free_summary = summarize_pilot(gold, pairs, free_records)
        constrained_summary = summarize_pilot(gold, pairs, constrained_records)
        comparisons.append(
            {
                "model_id": model,
                "seed": EXPECTED_SEED,
                "invariants": invariants,
                "constraint_effect": {
                    "decision_coverage_delta": constrained_summary["decision_coverage"]
                    - free_summary["decision_coverage"],
                    "pair_coverage_delta": constrained_summary["pair_coverage"]
                    - free_summary["pair_coverage"],
                    "raw_action_accuracy_delta": delta(
                        constrained_summary["raw_action_accuracy"],
                        free_summary["raw_action_accuracy"],
                    ),
                    "raw_pair_accuracy_delta": delta(
                        constrained_summary["raw_pair_accuracy"],
                        free_summary["raw_pair_accuracy"],
                    ),
                    "json_syntax_errors_removed": (
                        free_summary["status_counts"]["JSON_SYNTAX_ERROR"]
                        - constrained_summary["status_counts"]["JSON_SYNTAX_ERROR"]
                    ),
                    "schema_errors_removed": (
                        free_summary["status_counts"]["SCHEMA_ERROR"]
                        - constrained_summary["status_counts"]["SCHEMA_ERROR"]
                    ),
                    "semantic_errors_delta": (
                        constrained_summary["status_counts"]["SEMANTIC_ERROR"]
                        - free_summary["status_counts"]["SEMANTIC_ERROR"]
                    ),
                },
            }
        )

    result: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "study_kind": "POST_V1_PUBLIC_INTERFACE_PILOT",
        "source_workflow_run_id": workflow_run_id,
        "protocol": {
            "dataset": "data/alpha",
            "instances": 40,
            "pairs": 20,
            "models": sorted(EXPECTED_MODELS),
            "decoding_modes": sorted(EXPECTED_MODES),
            "seed": EXPECTED_SEED,
            "prompt_arm": "ledger_verifier",
            "total_decisions": 160,
            "paid_api_calls": 0,
        },
        "aggregate_status_counts": dict(sorted(aggregate_status_counts.items())),
        "runs": runs,
        "model_comparisons": comparisons,
        "interpretation_status": "PENDING_AUTHOR_REVIEW",
        "interpretation_boundary": (
            "This is a post-v1 public interface pilot. It does not alter the frozen v1 hidden "
            "study, and post-gate correctness is not model correctness."
        ),
    }
    result["study_sha256"] = digest_json(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "alpha")
    parser.add_argument("--source-workflow-run-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = build(
        args.artifact_root.resolve(),
        args.dataset.resolve(),
        args.source_workflow_run_id,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "decisions": result["protocol"]["total_decisions"],
                "study_sha256": result["study_sha256"],
                "output": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
