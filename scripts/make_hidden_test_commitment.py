#!/usr/bin/env python3
"""Validate a private v1 hidden set and emit only its public commitment record.

The private dataset and seed remain outside the public repository. This script intentionally
writes hashes/counts only; it never copies hidden rows, gold labels, or seed bytes to the output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl, validate_dataset  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

PLAN = ROOT / "configs" / "v1-benchmark-plan.json"
_HEX64 = re.compile(rb"^[0-9a-fA-F]{64}$")


def _normalized_seed(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) == 32:
        return raw
    stripped = raw.strip()
    if _HEX64.fullmatch(stripped):
        return bytes.fromhex(stripped.decode("ascii"))
    raise ValueError("hidden seed file must contain exactly 32 raw bytes or 64 hexadecimal digits")


def _safe_component(dataset_dir: Path, name: str) -> Path:
    path = (dataset_dir / name).resolve()
    try:
        path.relative_to(dataset_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"component escapes private dataset: {name}") from exc
    if not path.is_file():
        raise ValueError(f"private hidden dataset is missing required component: {name}")
    return path


def build_commitment(dataset_dir: Path, seed_file: Path, prompt_manifest: Path) -> dict[str, Any]:
    """Return a public-safe commitment after full private dataset validation."""

    plan = load_json(PLAN)
    if not isinstance(plan, dict):
        raise ValueError("v1 benchmark plan must be an object")
    test_plan = plan["splits"]["test"]
    expected_pairs = int(test_plan["pairs"])
    expected_instances = int(test_plan["instances"])

    summary = validate_dataset(dataset_dir, ROOT)
    manifest = load_json(dataset_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise ValueError("private hidden manifest must be an object")
    if int(manifest.get("pairs", -1)) != expected_pairs:
        raise ValueError(f"hidden manifest must contain exactly {expected_pairs} pairs")
    if int(manifest.get("instances", -1)) != expected_instances:
        raise ValueError(f"hidden manifest must contain exactly {expected_instances} instances")

    inputs = load_jsonl(_safe_component(dataset_dir, "inputs.jsonl"))
    if len(inputs) != expected_instances or {str(item.get("split")) for item in inputs} != {"test"}:
        raise ValueError("every private hidden input must have split=test")

    pairs = load_json(_safe_component(dataset_dir, "pairs.json"))
    if not isinstance(pairs, list) or len(pairs) != expected_pairs:
        raise ValueError("private hidden pairs.json does not match the preregistered pair count")
    family_counts = Counter(str(pair["family"]) for pair in pairs)
    invalid_sides = Counter(
        str(pair["invalid_id"]).rsplit("-", 1)[-1].upper() for pair in pairs
    )
    if invalid_sides != Counter(test_plan["invalid_side_counts"]):
        raise ValueError(
            f"hidden invalid-side distribution differs from plan: {dict(invalid_sides)}"
        )

    gold = load_jsonl(_safe_component(dataset_dir, "gold.jsonl"))
    invalid_ids = {str(pair["invalid_id"]) for pair in pairs}
    gold_by_id = {str(row["id"]): row for row in gold}
    invalid_actions = Counter(
        str(gold_by_id[item_id]["decision"]["action"]) for item_id in invalid_ids
    )
    expected_actions = Counter(plan["test_invalid_action_counts"])
    if invalid_actions != expected_actions:
        raise ValueError(
            f"hidden invalid-action distribution differs from plan: {dict(invalid_actions)}"
        )

    seed = _normalized_seed(seed_file)
    prompt_manifest = prompt_manifest.resolve()
    if not prompt_manifest.is_file():
        raise ValueError("frozen prompt manifest is missing")

    component_names = (
        "manifest.json",
        "author-items.jsonl",
        "inputs.jsonl",
        "gold.jsonl",
        "pairs.json",
    )
    components = {
        name: sha256_file(_safe_component(dataset_dir, name)) for name in component_names
    }
    record: dict[str, Any] = {
        "commitment_version": "1.0.0",
        "benchmark_id": str(plan["benchmark_id"]),
        "split": "test",
        "pairs": expected_pairs,
        "instances": expected_instances,
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_sides.items())),
        "invalid_action_counts": dict(sorted(invalid_actions.items())),
        "dataset_components": components,
        "dataset_manifest_sha256": components["manifest.json"],
        "policy_id": manifest.get("policy_id"),
        "policy_version": manifest.get("policy_version"),
        "policy_sha256": manifest.get("policy_sha256"),
        "schema_sha256": manifest.get("schema_sha256"),
        "benchmark_plan_sha256": sha256_file(PLAN),
        "prompt_manifest_sha256": sha256_file(prompt_manifest),
        "hidden_seed_sha256": sha256_bytes(seed),
        "validator_summary": summary,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "contains_seed_bytes": False,
        "freeze_rule": str(plan["freeze_rule"]),
    }
    record["commitment_sha256"] = sha256_bytes(canonical_json(record).encode("utf-8"))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="private 150-pair test directory",
    )
    parser.add_argument("--seed-file", type=Path, required=True, help="private 32-byte seed")
    parser.add_argument(
        "--prompt-manifest",
        type=Path,
        required=True,
        help="frozen model-facing prompt manifest produced before scored inference",
    )
    parser.add_argument("--out", type=Path, required=True, help="public commitment JSON path")
    args = parser.parse_args()

    record = build_commitment(
        args.dataset.resolve(),
        args.seed_file.resolve(),
        args.prompt_manifest,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
