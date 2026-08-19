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
    identities: set[tuple[str, str, int]] = set()
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
        identity = (model_id, mode, seed)
        if identity in identities:
            raise RuntimeError(f"duplicate pilot identity: {identity}")
        identities.add(identity)
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
        by_mode = {str(row["decoding_mode"]): row for row in rows}
        comparison: Json = {"model_id": model_id, "runs": rows}
        if "free" in by_mode and "json_schema" in by_mode:
            free = by_mode["free"]
            constrained = by_mode["json_schema"]
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


def _delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


if __name__ == "__main__":
    raise SystemExit(main())
