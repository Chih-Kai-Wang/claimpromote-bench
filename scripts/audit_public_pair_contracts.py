#!/usr/bin/env python3
"""Audit the public controlled-pair contracts without human annotations.

This audit checks the integrity of the public 20-pair alpha benchmark. It verifies that each pair
contains exactly one policy-admissible member and one policy-inadmissible member, that the two
members differ only under the registered controlled JSON pointers, and that the committed gold
labels are reproduced exactly by the versioned policy oracle.

The report is evidence about benchmark construction and implementation consistency. It is not an
independent human judgment and does not claim that the policy is a universal ground truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402
from claimpromotebench.oracle import evaluate  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"pair-contract-audit: {message}")


def escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def diff_pointers(left: Any, right: Any, pointer: str = "") -> set[str]:
    """Return leaf/container JSON pointers whose values differ."""

    if type(left) is not type(right):
        return {pointer or "/"}
    if isinstance(left, dict):
        differences: set[str] = set()
        keys = set(left) | set(right)
        for key in sorted(keys):
            child = f"{pointer}/{escape_pointer_part(str(key))}"
            if key not in left or key not in right:
                differences.add(child)
            else:
                differences.update(diff_pointers(left[key], right[key], child))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return {pointer or "/"}
        differences: set[str] = set()
        for index, (left_child, right_child) in enumerate(zip(left, right, strict=True)):
            differences.update(diff_pointers(left_child, right_child, f"{pointer}/{index}"))
        return differences
    return set() if left == right else {pointer or "/"}


def pointer_is_registered(pointer: str, registered: list[str]) -> bool:
    """Allow a difference at or below a registered controlled subtree."""

    for allowed in registered:
        if pointer == allowed or pointer.startswith(f"{allowed}/"):
            return True
        # A list-length or whole-object replacement may be reported at the parent container.
        if allowed.startswith(f"{pointer}/"):
            return True
    return False


def comparable_item(item: Json) -> Json:
    value = json.loads(json.dumps(item))
    value.pop("id", None)
    return value


def exact_gold_decision(row: Json) -> Json:
    decision = row.get("decision")
    if not isinstance(decision, dict):
        fail(f"gold row {row.get('id')} lacks a decision object")
    return decision


def audit(dataset_dir: Path) -> Json:
    manifest = load_json(dataset_dir / "manifest.json")
    pairs = load_json(dataset_dir / "pairs.json")
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    if not isinstance(manifest, dict):
        fail("manifest.json must contain an object")
    if not isinstance(pairs, list) or not all(isinstance(row, dict) for row in pairs):
        fail("pairs.json must contain a list of objects")
    if len(pairs) != 20 or len(inputs) != 40 or len(gold) != 40:
        fail("public alpha must contain 20 pairs and 40 instances")

    input_by_id = {str(row["id"]): row for row in inputs}
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(input_by_id) != len(inputs) or len(gold_by_id) != len(gold):
        fail("duplicate input or gold IDs")
    if set(input_by_id) != set(gold_by_id):
        fail("input and gold ID sets differ")

    policy_path = ROOT / "policies" / str(manifest["policy_file"])
    policy = load_policy(policy_path)
    evaluation_time = str(manifest["evaluation_time"])

    seen_pair_ids: set[str] = set()
    seen_factor_ids: set[str] = set()
    family_counts: Counter[str] = Counter()
    invalid_side_counts: Counter[str] = Counter()
    invalid_actions: Counter[str] = Counter()
    contracts: list[Json] = []

    for pair in pairs:
        pair_id = str(pair.get("pair_id"))
        factor_id = str(pair.get("factor_id"))
        family = str(pair.get("family"))
        if not pair_id or pair_id in seen_pair_ids:
            fail(f"duplicate or empty pair_id: {pair_id}")
        if not factor_id or factor_id in seen_factor_ids:
            fail(f"duplicate or empty factor_id: {factor_id}")
        seen_pair_ids.add(pair_id)
        seen_factor_ids.add(factor_id)
        family_counts[family] += 1

        member_ids = pair.get("member_ids")
        if not isinstance(member_ids, list) or len(member_ids) != 2:
            fail(f"{pair_id} must contain exactly two member_ids")
        member_ids = [str(value) for value in member_ids]
        if len(set(member_ids)) != 2 or not set(member_ids) <= set(input_by_id):
            fail(f"{pair_id} contains invalid member IDs")
        invalid_id = str(pair.get("invalid_id"))
        valid_id = str(pair.get("valid_id"))
        if {invalid_id, valid_id} != set(member_ids):
            fail(f"{pair_id} valid/invalid IDs do not partition its members")

        invalid_side = invalid_id.rsplit("-", 1)[-1].upper()
        if invalid_side not in {"A", "B"}:
            fail(f"{pair_id} has an invalid side identifier")
        invalid_side_counts[invalid_side] += 1

        registered = pair.get("controlled_json_pointers")
        if not isinstance(registered, list) or not registered:
            fail(f"{pair_id} lacks controlled_json_pointers")
        registered = [str(value) for value in registered]
        if len(set(registered)) != len(registered):
            fail(f"{pair_id} repeats a controlled JSON pointer")

        left = input_by_id[member_ids[0]]
        right = input_by_id[member_ids[1]]
        if left.get("pair_id") != pair_id or right.get("pair_id") != pair_id:
            fail(f"{pair_id} member pair_id binding is wrong")
        if left.get("family") != family or right.get("family") != family:
            fail(f"{pair_id} member family binding is wrong")

        differences = sorted(diff_pointers(comparable_item(left), comparable_item(right)))
        if not differences:
            fail(f"{pair_id} members are identical after removing item ID")
        unregistered = [
            pointer for pointer in differences if not pointer_is_registered(pointer, registered)
        ]
        if unregistered:
            fail(f"{pair_id} has unregistered member differences: {unregistered}")

        recomputed: dict[str, Json] = {}
        for item_id in member_ids:
            decision = evaluate(input_by_id[item_id], policy, evaluation_time)
            recomputed[item_id] = decision
            if decision != exact_gold_decision(gold_by_id[item_id]):
                fail(f"{pair_id} gold decision does not match the versioned oracle for {item_id}")

        valid_decision = recomputed[valid_id]
        invalid_decision = recomputed[invalid_id]
        if valid_decision.get("action") != "ALLOW":
            fail(f"{pair_id} registered valid member is not ALLOW")
        if valid_decision.get("reason_codes") != ["POLICY_SATISFIED"]:
            fail(f"{pair_id} valid member lacks the canonical allow reason")
        invalid_action = str(invalid_decision.get("action"))
        if invalid_action == "ALLOW":
            fail(f"{pair_id} registered invalid member is ALLOW")
        invalid_reasons = invalid_decision.get("reason_codes")
        if not isinstance(invalid_reasons, list) or not invalid_reasons:
            fail(f"{pair_id} invalid member lacks policy reasons")
        invalid_actions[invalid_action] += 1

        contracts.append(
            {
                "pair_id": pair_id,
                "factor_id": factor_id,
                "family": family,
                "member_ids": member_ids,
                "valid_id": valid_id,
                "invalid_id": invalid_id,
                "controlled_json_pointers": registered,
                "observed_difference_pointers": differences,
                "valid_action": "ALLOW",
                "valid_reason_codes": valid_decision["reason_codes"],
                "invalid_action": invalid_action,
                "invalid_reason_codes": invalid_reasons,
                "oracle_exact_match": True,
            }
        )

    expected_family_counts = manifest.get("family_pair_counts")
    if dict(sorted(family_counts.items())) != expected_family_counts:
        fail("observed family counts differ from the manifest")
    expected_invalid_sides = manifest.get("invalid_side_counts")
    if dict(sorted(invalid_side_counts.items())) != expected_invalid_sides:
        fail("observed invalid-side counts differ from the manifest")
    if len(seen_factor_ids) != 20:
        fail("public alpha must contain 20 distinct policy factors")

    return {
        "schema_version": "1.0.0",
        "status": "PASS",
        "audit_kind": "MACHINE_CHECKABLE_PUBLIC_PAIR_CONTRACT",
        "interpretation_boundary": (
            "This report verifies construction consistency under the published versioned policy. "
            "It is not an independent human annotation study or a claim of universal ground truth."
        ),
        "dataset_id": manifest["dataset_id"],
        "policy_id": manifest["policy_id"],
        "policy_version": manifest["policy_version"],
        "evaluation_time": evaluation_time,
        "pairs": len(pairs),
        "instances": len(inputs),
        "distinct_policy_factors": len(seen_factor_ids),
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_side_counts.items())),
        "valid_action_counts": {"ALLOW": len(pairs)},
        "invalid_action_counts": dict(sorted(invalid_actions.items())),
        "source_sha256": {
            "inputs": sha256_file(dataset_dir / "inputs.jsonl"),
            "gold": sha256_file(dataset_dir / "gold.jsonl"),
            "pairs": sha256_file(dataset_dir / "pairs.json"),
            "manifest": sha256_file(dataset_dir / "manifest.json"),
            "policy": sha256_file(policy_path),
        },
        "contracts": contracts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "alpha")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = audit(args.dataset.resolve())
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "pairs": report["pairs"],
                "factors": report["distinct_policy_factors"],
                "invalid_actions": report["invalid_action_counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
