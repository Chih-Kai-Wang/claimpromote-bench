#!/usr/bin/env python3
"""Derive policy-difference coverage from the frozen policy-switch dataset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
PROFILE_ORDER = ("POLICY_BLUE", "POLICY_AMBER")
DEFAULT_DATASET_ROOT = ROOT / "v2" / "policy-switch-v1" / "frozen" / "dataset"
DEFAULT_POLICY = ROOT / "v2" / "policy-switch-v1" / "policy-contract.json"
DEFAULT_OUT = ROOT / "v2" / "policy-switch-v1" / "policy-difference-coverage.json"


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(row, dict) for row in rows):
        fail(f"JSONL contains a non-object row: {path}")
    return rows


def without_active_profile(item: Json) -> Json:
    return {key: value for key, value in item.items() if key != "active_policy_profile"}


def derive(dataset_root: Path, policy_path: Path) -> Json:
    item_rows = load_jsonl(dataset_root / "evaluation-items.jsonl")
    gold_rows = load_jsonl(dataset_root / "evaluation-gold.jsonl")
    pairs = load_json(dataset_root / "evaluation-pairs.json")
    policy = load_json(policy_path)
    if not isinstance(pairs, list) or any(not isinstance(row, dict) for row in pairs):
        fail("evaluation-pairs.json must contain an array of objects")
    if not isinstance(policy, dict) or tuple(policy.get("profile_order", [])) != PROFILE_ORDER:
        fail("policy profile order changed")

    items = {str(row["id"]): row["model_visible"] for row in item_rows}
    gold = {str(row["id"]): row for row in gold_rows}
    if len(items) != len(item_rows) or len(gold) != len(gold_rows) or set(items) != set(gold):
        fail("evaluation item or gold identifiers are not one-to-one")

    factor_pairs: Counter[str] = Counter()
    factor_binding: dict[str, str] = {}
    factor_transitions: dict[str, set[str]] = defaultdict(set)
    transition_counts: Counter[str] = Counter()
    profile_action_support: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILE_ORDER
    }

    for pair in pairs:
        member_ids = pair.get("member_ids")
        if not isinstance(member_ids, list) or len(member_ids) != 2:
            fail("every pair must contain exactly two member identifiers")
        left_id, right_id = (str(value) for value in member_ids)
        if left_id not in items or right_id not in items:
            fail("pair references an unknown item")
        left = items[left_id]
        right = items[right_id]
        if not isinstance(left, dict) or not isinstance(right, dict):
            fail("model-visible item must be an object")
        if canonical_json(without_active_profile(left)) != canonical_json(
            without_active_profile(right)
        ):
            fail(f"pair changes more than the active policy profile: {pair.get('pair_id')}")

        members_by_profile: dict[str, tuple[str, Json]] = {}
        for item_id, item in ((left_id, left), (right_id, right)):
            profile = str(item.get("active_policy_profile"))
            if profile not in PROFILE_ORDER or profile in members_by_profile:
                fail(f"pair profile membership is malformed: {pair.get('pair_id')}")
            members_by_profile[profile] = (item_id, item)
        if set(members_by_profile) != set(PROFILE_ORDER):
            fail(f"pair does not cover both profiles: {pair.get('pair_id')}")

        actions: list[str] = []
        factor_ids: set[str] = set()
        binding_profiles: set[str] = set()
        for profile in PROFILE_ORDER:
            item_id, _ = members_by_profile[profile]
            row = gold[item_id]
            decision = row.get("decision")
            if not isinstance(decision, dict) or decision.get("action") not in ACTIONS:
                fail(f"gold action is malformed: {item_id}")
            action = str(decision["action"])
            actions.append(action)
            factor_ids.add(str(row.get("factor_id")))
            binding_profiles.add(str(row.get("binding_profile")))
            profile_action_support[profile][action] += 1
        if len(factor_ids) != 1 or len(binding_profiles) != 1:
            fail(f"pair factor metadata differs: {pair.get('pair_id')}")
        if actions[0] == actions[1]:
            fail(f"pair does not distinguish the policies: {pair.get('pair_id')}")

        factor_id = next(iter(factor_ids))
        binding_profile = next(iter(binding_profiles))
        transition = f"{actions[0]}->{actions[1]}"
        factor_pairs[factor_id] += 1
        factor_transitions[factor_id].add(transition)
        transition_counts[transition] += 1
        prior_binding = factor_binding.setdefault(factor_id, binding_profile)
        if prior_binding != binding_profile:
            fail(f"factor binding profile changes across contexts: {factor_id}")

    policy_fields = {
        str(field)
        for profile in policy["profiles"].values()
        for field in profile["enforced_boolean_fields"]
    }
    policy_conflicts = {
        str(code)
        for profile in policy["profiles"].values()
        for code in profile["escalated_conflict_codes"]
    }
    authored_difference_factors = len(policy_fields) + len(policy_conflicts)
    expected_transitions = {
        "ALLOW->HOLD",
        "HOLD->ALLOW",
        "ALLOW->DEMOTE",
        "DEMOTE->ALLOW",
        "ALLOW->ESCALATE",
        "ESCALATE->ALLOW",
    }
    if (
        len(pairs) != 60
        or len(factor_pairs) != authored_difference_factors
        or set(factor_pairs.values()) != {5}
        or set(transition_counts) != expected_transitions
        or set(transition_counts.values()) != {10}
    ):
        fail("frozen policy-difference coverage no longer matches the registered balance")

    factors = [
        {
            "factor_id": factor_id,
            "binding_profile": factor_binding[factor_id],
            "evaluation_pairs": factor_pairs[factor_id],
            "blue_to_amber_transition": next(iter(factor_transitions[factor_id])),
        }
        for factor_id in sorted(factor_pairs)
    ]
    record: Json = {
        "schema_version": "1.0.0",
        "status": "POLICY_DIFFERENCE_COVERAGE_COMPLETE",
        "source_bindings": {
            "evaluation_items_sha256": sha256_file(dataset_root / "evaluation-items.jsonl"),
            "evaluation_gold_sha256": sha256_file(dataset_root / "evaluation-gold.jsonl"),
            "evaluation_pairs_sha256": sha256_file(dataset_root / "evaluation-pairs.json"),
            "dataset_manifest_sha256": sha256_file(dataset_root / "manifest.json"),
            "policy_contract_sha256": sha256_file(policy_path),
        },
        "construction": {
            "fixed_profile_direction": list(PROFILE_ORDER),
            "evaluation_pairs": len(pairs),
            "evaluation_items": len(items),
            "all_pairs_change_only_active_policy_profile": True,
            "all_pairs_change_definitional_action": True,
            "client_or_model_calls": 0,
        },
        "coverage": {
            "authored_profile_difference_factors_covered": len(factor_pairs),
            "authored_profile_difference_factors_total": authored_difference_factors,
            "contexts_per_factor": 5,
            "directed_nonself_action_transitions_covered": len(transition_counts),
            "directed_nonself_action_transitions_possible_over_four_actions": 12,
            "transition_scope": "ADMISSION_CENTERED_STAR_NOT_COMPLETE_ACTION_GRAPH",
            "blue_to_amber_transition_counts": dict(sorted(transition_counts.items())),
            "profile_action_support": {
                profile: {action: profile_action_support[profile][action] for action in ACTIONS}
                for profile in PROFILE_ORDER
            },
            "factors": factors,
        },
        "interpretation_boundary": (
            "The suite distinguishes every rule difference authored into POLICY_BLUE and "
            "POLICY_AMBER on five contexts. It covers only ALLOW-to-or-from-non-ALLOW action "
            "changes, not the complete four-action transition graph or unseen policies."
        ),
    }
    record["record_sha256"] = sha256_bytes(canonical_json(record).encode("utf-8"))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    record = derive(args.dataset_root.resolve(), args.policy.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": record["status"],
                "pairs": record["construction"]["evaluation_pairs"],
                "factors": record["coverage"]["authored_profile_difference_factors_covered"],
                "directed_transitions": record["coverage"][
                    "directed_nonself_action_transitions_covered"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
