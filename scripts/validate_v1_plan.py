#!/usr/bin/env python3
"""Validate the preregistered v1 design and optionally audit built dev/test datasets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl, validate_dataset  # noqa: E402

PLAN = ROOT / "configs" / "v1-benchmark-plan.json"


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    factors = plan.get("factors")
    if not isinstance(factors, list) or len(factors) != 20:
        raise ValueError("v1 plan must declare exactly 20 factors")
    if len({str(row["factor_id"]) for row in factors}) != len(factors):
        raise ValueError("v1 factor IDs must be unique")

    total_pairs = sum(int(row["pairs"]) for row in factors)
    if total_pairs != int(plan["pairs"]) or int(plan["instances"]) != total_pairs * 2:
        raise ValueError("v1 total pair/instance arithmetic is inconsistent")
    if any(int(row["pairs"]) != 10 for row in factors):
        raise ValueError("each preregistered v1 factor must have exactly 10 pairs")

    family_counts = Counter()
    action_counts = Counter()
    dev_action_counts = Counter()
    dev_pairs = 0
    dev_sides = Counter()
    for factor_index, row in enumerate(factors):
        pair_count = int(row["pairs"])
        family_counts[str(row["family"])] += pair_count
        action_counts[str(row["invalid_action"])] += pair_count
        variants = [int(value) for value in row["dev_variants"]]
        if len(variants) != len(set(variants)) or any(not 0 <= value < pair_count for value in variants):
            raise ValueError(f"invalid dev variants for factor {row['factor_id']}")
        dev_pairs += len(variants)
        dev_action_counts[str(row["invalid_action"])] += len(variants)
        for variant in variants:
            side = "A" if (factor_index + variant) % 2 == 0 else "B"
            dev_sides[side] += 1

    if family_counts != Counter(plan["family_pair_counts"]):
        raise ValueError(f"family counts differ from plan: {dict(family_counts)}")
    if action_counts != Counter(plan["overall_invalid_action_counts"]):
        raise ValueError(f"invalid-action counts differ from plan: {dict(action_counts)}")
    if dev_pairs != int(plan["splits"]["dev"]["pairs"]):
        raise ValueError("dev variant allocation does not sum to the dev pair count")
    if dev_action_counts != Counter(plan["dev_invalid_action_counts"]):
        raise ValueError(f"dev invalid-action counts differ from plan: {dict(dev_action_counts)}")
    if dev_sides != Counter(plan["splits"]["dev"]["invalid_side_counts"]):
        raise ValueError(f"dev invalid-side counts differ from plan: {dict(dev_sides)}")

    hidden_action_counts = action_counts - dev_action_counts
    hidden_sides = Counter(plan["overall_invalid_side_counts"]) - dev_sides
    if hidden_action_counts != Counter(plan["test_invalid_action_counts"]):
        raise ValueError("derived hidden invalid-action counts differ from plan")
    if hidden_sides != Counter(plan["splits"]["test"]["invalid_side_counts"]):
        raise ValueError("derived hidden invalid-side counts differ from plan")

    return {
        "status": "PLAN_PASS",
        "pairs": total_pairs,
        "instances": int(plan["instances"]),
        "dev_pairs": dev_pairs,
        "test_pairs": total_pairs - dev_pairs,
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_action_counts": dict(sorted(action_counts.items())),
    }


def audit_dataset(dataset_dir: Path, expected_split: str, plan: dict[str, Any]) -> dict[str, Any]:
    summary = validate_dataset(dataset_dir, ROOT)
    manifest = load_json(dataset_dir / "manifest.json")
    pairs = load_json(dataset_dir / "pairs.json")
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    if not isinstance(manifest, dict) or not isinstance(pairs, list):
        raise ValueError("dataset manifest/pairs are malformed")

    split_plan = plan["splits"][expected_split]
    if int(manifest["pairs"]) != int(split_plan["pairs"]):
        raise ValueError(f"{expected_split} pair count differs from preregistration")
    if int(manifest["instances"]) != int(split_plan["instances"]):
        raise ValueError(f"{expected_split} instance count differs from preregistration")
    if {str(item.get("split")) for item in inputs} != {expected_split}:
        raise ValueError(f"{expected_split} dataset contains an unexpected split label")

    factor_counts = Counter(str(pair["factor_id"]) for pair in pairs)
    planned_by_factor: dict[str, int] = {}
    for row in plan["factors"]:
        dev_count = len(row["dev_variants"])
        planned_by_factor[str(row["factor_id"])] = (
            dev_count if expected_split == "dev" else int(row["pairs"]) - dev_count
        )
    if factor_counts != Counter(planned_by_factor):
        raise ValueError(
            f"{expected_split} factor distribution differs from preregistration: {dict(factor_counts)}"
        )

    invalid_sides = Counter(
        str(pair["invalid_id"]).rsplit("-", 1)[-1].upper() for pair in pairs
    )
    if invalid_sides != Counter(split_plan["invalid_side_counts"]):
        raise ValueError(f"{expected_split} invalid-side balance differs from preregistration")

    return {
        "status": "DATASET_PASS",
        "split": expected_split,
        "validator": summary,
        "factor_pair_counts": dict(sorted(factor_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_sides.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-dir", type=Path)
    parser.add_argument("--test-dir", type=Path)
    args = parser.parse_args()

    plan = load_json(PLAN)
    if not isinstance(plan, dict):
        raise ValueError("v1 benchmark plan must be an object")
    report: dict[str, Any] = {"plan": validate_plan(plan)}
    if args.dev_dir is not None:
        report["dev"] = audit_dataset(args.dev_dir.resolve(), "dev", plan)
    if args.test_dir is not None:
        report["test"] = audit_dataset(args.test_dir.resolve(), "test", plan)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
