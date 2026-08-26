#!/usr/bin/env python3
"""Analyze low-cost v2 pilot runs without changing the frozen v1 evaluator."""

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
from claimpromotebench.v2 import summarize_pilot  # noqa: E402

Json = dict[str, Any]
Identity = tuple[str, str, int]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dataset_dir = args.dataset.resolve()
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        raise RuntimeError("pairs.json must contain a list")

    summaries: list[Json] = []
    identities: set[Identity] = set()
    records_by_identity: dict[Identity, list[Json]] = {}
    for run_path in args.runs:
        records = load_jsonl(run_path)
        if not records:
            raise RuntimeError(f"empty pilot run: {run_path}")
        model_ids = {str(row["model_id"]) for row in records}
        modes = {str(row["decoding_mode"]) for row in records}
        seeds = {int(row["seed"]) for row in records}
        if len(model_ids) != 1 or len(modes) != 1 or len(seeds) != 1:
            raise RuntimeError(f"mixed identity in pilot run: {run_path}")
        model_id = next(iter(model_ids))
        mode = next(iter(modes))
        seed = next(iter(seeds))
        identity: Identity = (model_id, mode, seed)
        if identity in identities:
            raise RuntimeError(f"duplicate pilot identity: {identity}")
        identities.add(identity)
        records_by_identity[identity] = records
        _validate_mode_metadata(mode, records, run_path)
        summary = summarize_pilot(gold, pairs, records)
        summary.update(
            {
                "model_id": model_id,
                "decoding_mode": mode,
                "seed": seed,
                "run_path": str(run_path),
                "run_sha256": sha256_file(run_path),
            }
        )
        summaries.append(summary)

    summaries.sort(key=lambda row: (row["model_id"], row["decoding_mode"], row["seed"]))
    by_model: list[Json] = []
    for model_id in sorted({str(row["model_id"]) for row in summaries}):
        rows = [row for row in summaries if row["model_id"] == model_id]
        seeds_for_model = sorted({int(row["seed"]) for row in rows})
        for seed in seeds_for_model:
            by_mode = {str(row["decoding_mode"]): row for row in rows if int(row["seed"]) == seed}
            comparison: Json = {"model_id": model_id, "seed": seed, "runs": list(by_mode.values())}
            if "free" in by_mode and "json_schema" in by_mode:
                free_records = records_by_identity[(model_id, "free", seed)]
                constrained_records = records_by_identity[(model_id, "json_schema", seed)]
                invariant_report = _verify_only_decoding_constraint_differs(
                    free_records, constrained_records
                )
                free = by_mode["free"]
                constrained = by_mode["json_schema"]
                comparison["invariants"] = invariant_report
                comparison["constraint_effect"] = {
                    "decision_coverage_delta": constrained["decision_coverage"]
                    - free["decision_coverage"],
                    "pair_coverage_delta": constrained["pair_coverage"] - free["pair_coverage"],
                    "raw_action_accuracy_delta": _delta(
                        constrained["raw_action_accuracy"], free["raw_action_accuracy"]
                    ),
                    "raw_pair_accuracy_delta": _delta(
                        constrained["raw_pair_accuracy"], free["raw_pair_accuracy"]
                    ),
                    "json_syntax_errors_removed": free["status_counts"]["JSON_SYNTAX_ERROR"]
                    - constrained["status_counts"]["JSON_SYNTAX_ERROR"],
                    "schema_errors_removed": free["status_counts"]["SCHEMA_ERROR"]
                    - constrained["status_counts"]["SCHEMA_ERROR"],
                    "semantic_errors_delta": constrained["status_counts"]["SEMANTIC_ERROR"]
                    - free["status_counts"]["SEMANTIC_ERROR"],
                }
            by_model.append(comparison)

    result = {
        "status": "COMPLETE",
        "dataset": str(dataset_dir),
        "pairs": len(pairs),
        "instances": len(gold),
        "run_count": len(summaries),
        "runs": summaries,
        "model_comparisons": by_model,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "COMPLETE", "output": str(args.out)}, sort_keys=True))
    return 0


def _validate_mode_metadata(mode: str, records: list[Json], run_path: Path) -> None:
    response_hashes = {row.get("response_format_sha256") for row in records}
    if mode == "free":
        if response_hashes != {None}:
            raise RuntimeError(f"free run contains a response-format constraint: {run_path}")
        return
    if mode == "json_schema":
        if len(response_hashes) != 1 or None in response_hashes:
            raise RuntimeError(f"constrained run lacks one fixed response-format hash: {run_path}")
        return
    raise RuntimeError(f"unknown decoding mode: {mode}")


def _verify_only_decoding_constraint_differs(
    free_records: list[Json], constrained_records: list[Json]
) -> Json:
    free_by_id = {str(row["item_id"]): row for row in free_records}
    constrained_by_id = {str(row["item_id"]): row for row in constrained_records}
    if set(free_by_id) != set(constrained_by_id):
        raise RuntimeError("free and constrained runs cover different item IDs")

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
            raise RuntimeError(f"prompt hash differs across decoding modes for {item_id}")
        for field in invariant_fields:
            if free.get(field) != constrained.get(field):
                raise RuntimeError(f"{field} differs across decoding modes for {item_id}")

    return {
        "status": "PASS",
        "items_compared": len(free_by_id),
        "prompt_hashes_identical": True,
        "model_runtime_seed_hardware_identical": True,
        "only_registered_difference": "response_format",
    }


def _delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


if __name__ == "__main__":
    raise SystemExit(main())
