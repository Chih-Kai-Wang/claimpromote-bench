#!/usr/bin/env python3
"""Validate the policy-transition graph and derive its structural coverage receipt."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_policy_switch_study import (  # noqa: E402
    BASE_POLICY_PATH,
    DECISION_SCHEMA,
    SOURCE_REGISTRY,
    SWITCH_POLICY_PATH,
    changed_paths,
    render_prompt,
)
from build_policy_transition_graph_study import (  # noqa: E402
    ACTIONS,
    PROFILE_ORDER,
    REACHABLE_TRANSITIONS,
    STUDY_ID,
    UNREACHABLE_TRANSITIONS,
)
from policy_switch import evaluate_policy_switch, load_switch_policy  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
HISTORICAL_COVERAGE_PATH = (
    ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
)
INTERPRETATION_ADDENDUM_PATH = (
    ROOT / "v2" / "policy-transition-graph-v1" / "transition-coverage-interpretation-addendum.json"
)
EXPLANATION_ONLY_COVERAGE_FIELDS = frozenset({"unreachability_certificate", "self_digest"})
EXPECTED_INTERPRETATION_UPDATE_PATHS = frozenset(
    {
        "scripts/build_policy_transition_graph_study.py",
        "scripts/validate_minimal_policy_migration_hosted_study.py",
        "scripts/validate_policy_transition_graph_hosted_study.py",
        "scripts/validate_policy_transition_graph_local_study.py",
        "scripts/validate_policy_transition_graph_study.py",
    }
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-graph-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        fail(f"{path} contains a non-object row")
    return rows


def self_digest(value: Json, field: str) -> str:
    payload = {key: child for key, child in value.items() if key != field}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def validate_interpretation_addendum() -> Json:
    """Validate the exact post-freeze explanation and validator-source correction."""

    historical = load_object(HISTORICAL_COVERAGE_PATH)
    addendum = load_object(INTERPRETATION_ADDENDUM_PATH)
    updates = addendum.get("authorized_validation_source_updates")
    if (
        addendum.get("status") != "POST_FREEZE_TRANSITION_UNREACHABILITY_EXPLANATION_CORRECTED"
        or addendum.get("source_transition_coverage_sha256")
        != sha256_file(HISTORICAL_COVERAGE_PATH)
        or addendum.get("historical_certificate") != historical.get("unreachability_certificate")
        or addendum.get("self_digest") != self_digest(addendum, "self_digest")
        or addendum.get("conclusions_changed") is not False
        or addendum.get("client_or_model_calls") != 0
        or not isinstance(updates, dict)
        or set(updates) != EXPECTED_INTERPRETATION_UPDATE_PATHS
    ):
        fail("transition-coverage interpretation addendum changed")
    expected_update_fields = {
        "historical_sha256",
        "corrected_sha256",
        "change_scope",
        "affects_frozen_requests_or_scores",
    }
    for relative, update in updates.items():
        if (
            not isinstance(relative, str)
            or not isinstance(update, dict)
            or set(update) != expected_update_fields
            or update.get("affects_frozen_requests_or_scores") is not False
            or update.get("historical_sha256") == update.get("corrected_sha256")
            or not str(update.get("change_scope", "")).strip()
            or sha256_file(ROOT / relative) != update.get("corrected_sha256")
        ):
            fail(f"unauthorized interpretation-source update: {relative}")
    return addendum


def validate_coverage_expectation(
    observed: Json,
    expected: Json,
    expected_path: Path,
) -> None:
    """Accept an exact receipt or its explanation-only, addendum-bound successor."""

    if canonical_json(observed) == canonical_json(expected):
        return
    if expected_path.resolve() != HISTORICAL_COVERAGE_PATH.resolve():
        fail("noncanonical coverage receipt differs from a clean recomputation")
    observed_stable = {
        key: value for key, value in observed.items() if key not in EXPLANATION_ONLY_COVERAGE_FIELDS
    }
    expected_stable = {
        key: value for key, value in expected.items() if key not in EXPLANATION_ONLY_COVERAGE_FIELDS
    }
    addendum = validate_interpretation_addendum()
    if (
        canonical_json(observed_stable) != canonical_json(expected_stable)
        or expected.get("self_digest") != self_digest(expected, "self_digest")
        or observed.get("self_digest") != self_digest(observed, "self_digest")
        or expected.get("unreachability_certificate") != addendum.get("historical_certificate")
        or observed.get("unreachability_certificate") != addendum.get("corrected_certificate")
    ):
        fail("recomputed coverage differs beyond the authorized explanation correction")


def runtime_source_hash_matches(relative: str, expected: str) -> bool:
    """Allow only source updates bound exactly by the interpretation addendum."""

    observed = sha256_file(ROOT / relative)
    if observed == expected:
        return True
    update = validate_interpretation_addendum()["authorized_validation_source_updates"].get(
        relative
    )
    return bool(
        isinstance(update, dict)
        and update.get("historical_sha256") == expected
        and update.get("corrected_sha256") == observed
        and update.get("affects_frozen_requests_or_scores") is False
    )


def validate(dataset_root: Path) -> Json:
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    switch_policy = load_switch_policy(SWITCH_POLICY_PATH, base_policy)
    if (
        manifest.get("study_id") != STUDY_ID
        or manifest.get("status") != "SYNTHETIC_POLICY_TRANSITION_GRAPH_DATASET"
        or packet.get("study_id") != STUDY_ID
        or packet.get("contains_gold") is not False
        or packet.get("contains_pair_or_factor_metadata_in_prompt") is not False
        or packet.get("contains_credentials") is not False
    ):
        fail("study identity or prompt boundary changed")

    named_files = (
        "development-gold.jsonl",
        "development-items.jsonl",
        "development-pairs.json",
        "evaluation-gold.jsonl",
        "evaluation-items.jsonl",
        "evaluation-pairs.json",
    )
    if manifest.get("data_file_sha256") != {
        name: sha256_file(dataset_root / name) for name in named_files
    }:
        fail("data-file hashes changed")
    if (
        manifest.get("base_policy_sha256") != sha256_file(BASE_POLICY_PATH)
        or manifest.get("switch_policy_sha256") != sha256_file(SWITCH_POLICY_PATH)
        or manifest.get("source_registry_sha256") != sha256_file(SOURCE_REGISTRY)
        or manifest.get("decision_schema_sha256") != sha256_file(DECISION_SCHEMA)
        or manifest.get("packet_file_sha256")
        != sha256_file(dataset_root / "evaluation-prompt-packet.json")
        or manifest.get("packet_sha256") != packet.get("packet_sha256")
    ):
        fail("policy, source, schema, or packet binding changed")

    profile_action_counts: dict[str, Counter[str]] = {
        profile: Counter() for profile in PROFILE_ORDER
    }
    evaluation_transition_counts: Counter[str] = Counter()
    development_transition_counts: Counter[str] = Counter()
    authored_rules: set[str] = set()
    evaluation_ids: set[str] = set()
    for split, expected_items, expected_pairs, expected_per_transition in (
        ("development", 60, 30, 3),
        ("evaluation", 120, 60, 6),
    ):
        items = load_jsonl(dataset_root / f"{split}-items.jsonl")
        gold = load_jsonl(dataset_root / f"{split}-gold.jsonl")
        pairs = json.loads((dataset_root / f"{split}-pairs.json").read_text(encoding="utf-8"))
        if (
            len(items) != expected_items
            or len(gold) != expected_items
            or not isinstance(pairs, list)
            or len(pairs) != expected_pairs
            or not all(isinstance(row, dict) for row in pairs)
        ):
            fail(f"{split} size or shape changed")
        items_by_id = {str(row["id"]): row for row in items}
        gold_by_id = {str(row["id"]): row for row in gold}
        if len(items_by_id) != expected_items or set(items_by_id) != set(gold_by_id):
            fail(f"{split} item and gold identifiers changed")
        member_ids: set[str] = set()
        transition_counts: Counter[str] = Counter()
        for pair in pairs:
            ids = [str(value) for value in pair.get("member_ids", [])]
            transition = str(pair.get("blue_to_amber_transition"))
            if (
                len(ids) != 2
                or len(set(ids)) != 2
                or pair.get("controlled_path") != "/active_policy_profile"
                or transition not in REACHABLE_TRANSITIONS
                or set(ids) - set(items_by_id)
                or member_ids & set(ids)
            ):
                fail(f"malformed pair: {pair.get('pair_id')}")
            member_ids.update(ids)
            left = items_by_id[ids[0]]["model_visible"]
            right = items_by_id[ids[1]]["model_visible"]
            if changed_paths(left, right) != ["/active_policy_profile"]:
                fail(f"pair changes more than the active profile: {pair.get('pair_id')}")
            observed_by_profile: dict[str, str] = {}
            for item_id in ids:
                item = items_by_id[item_id]["model_visible"]
                profile = str(item["active_policy_profile"])
                decision = evaluate_policy_switch(item, switch_policy, base_policy)
                gold_row = gold_by_id[item_id]
                if profile in observed_by_profile or gold_row.get("decision") != decision:
                    fail(f"gold or profile membership changed: {item_id}")
                observed_by_profile[profile] = str(decision["action"])
                rule = gold_row.get("binding_rule", {}).get("rule")
                if rule is not None:
                    authored_rules.add(str(rule))
                if split == "evaluation":
                    profile_action_counts[profile][str(decision["action"])] += 1
                    evaluation_ids.add(item_id)
            if set(observed_by_profile) != set(PROFILE_ORDER):
                fail(f"pair lacks one profile: {pair.get('pair_id')}")
            observed_transition = "->".join(
                observed_by_profile[profile] for profile in PROFILE_ORDER
            )
            if observed_transition != transition:
                fail(f"directed transition changed: {pair.get('pair_id')}")
            transition_counts[transition] += 1
        if member_ids != set(items_by_id) or transition_counts != Counter(
            {transition: expected_per_transition for transition in REACHABLE_TRANSITIONS}
        ):
            fail(f"{split} transition coverage changed")
        if split == "evaluation":
            evaluation_transition_counts = transition_counts
        else:
            development_transition_counts = transition_counts

    expected_profile = Counter({"ALLOW": 18, "ESCALATE": 18, "HOLD": 12, "DEMOTE": 12})
    if any(profile_action_counts[profile] != expected_profile for profile in PROFILE_ORDER):
        fail("profile-conditioned action support changed")
    policy_rules = {
        str(field)
        for profile in switch_policy["profiles"].values()
        for field in profile["enforced_boolean_fields"]
    } | {
        str(code)
        for profile in switch_policy["profiles"].values()
        for code in profile["escalated_conflict_codes"]
    }
    if authored_rules != policy_rules or len(policy_rules) != 12:
        fail("authored policy-difference rule coverage changed")

    packet_records = packet.get("records")
    if (
        not isinstance(packet_records, list)
        or len(packet_records) != 120
        or {str(row["item_id"]) for row in packet_records} != evaluation_ids
    ):
        fail("prompt packet coverage changed")
    evaluation_items = {
        str(row["id"]): row for row in load_jsonl(dataset_root / "evaluation-items.jsonl")
    }
    for row in packet_records:
        item_id = str(row["item_id"])
        prompt = render_prompt(
            evaluation_items[item_id]["model_visible"], base_policy, switch_policy
        )
        if row.get("prompt") != prompt or row.get("prompt_sha256") != sha256_bytes(
            prompt.encode("utf-8")
        ):
            fail(f"prompt rendering changed: {item_id}")
    if packet.get("packet_sha256") != self_digest(packet, "packet_sha256"):
        fail("prompt packet self-digest changed")

    coverage: Json = {
        "schema_version": "1.0.0",
        "status": "POLICY_TRANSITION_GRAPH_COVERAGE_COMPLETE",
        "study_id": STUDY_ID,
        "directed_nonself_action_transitions_possible": 12,
        "directed_action_transitions_semantically_reachable": 10,
        "directed_action_transitions_covered": len(evaluation_transition_counts),
        "contexts_per_evaluation_transition": 6,
        "evaluation_transition_counts": dict(sorted(evaluation_transition_counts.items())),
        "development_transition_counts": dict(sorted(development_transition_counts.items())),
        "structurally_unreachable_transitions": list(UNREACHABLE_TRANSITIONS),
        "unreachability_certificate": (
            "Under the published executor and shared-state pair contract, DEMOTE is available "
            "only when current_state.release_status=ADMITTED and an enforced check fails. On an "
            "ADMITTED state, that failure reaches DEMOTE before HOLD under first-match precedence; "
            "on a non-ADMITTED state, DEMOTE is unavailable. Therefore neither HOLD->DEMOTE nor "
            "DEMOTE->HOLD is reachable."
        ),
        "authored_profile_difference_rules_covered": len(authored_rules),
        "authored_profile_difference_rules_total": len(policy_rules),
        "profile_action_support": {
            profile: {action: profile_action_counts[profile][action] for action in ACTIONS}
            for profile in PROFILE_ORDER
        },
        "source_bindings": {
            "manifest_sha256": sha256_file(dataset_root / "manifest.json"),
            "evaluation_items_sha256": sha256_file(dataset_root / "evaluation-items.jsonl"),
            "evaluation_gold_sha256": sha256_file(dataset_root / "evaluation-gold.jsonl"),
            "evaluation_pairs_sha256": sha256_file(dataset_root / "evaluation-pairs.json"),
            "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
            "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
        },
        "client_or_model_calls": 0,
    }
    coverage["self_digest"] = self_digest(coverage, "self_digest")
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--coverage-out", type=Path)
    parser.add_argument("--expect", type=Path)
    args = parser.parse_args()
    coverage = validate(args.dataset_root.resolve())
    if args.expect is not None:
        expected_path = args.expect.resolve()
        validate_coverage_expectation(coverage, load_object(expected_path), expected_path)
    if args.coverage_out is not None:
        args.coverage_out.parent.mkdir(parents=True, exist_ok=True)
        args.coverage_out.write_text(
            json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        canonical_json(
            {
                "status": coverage["status"],
                "reachable": coverage["directed_action_transitions_semantically_reachable"],
                "covered": coverage["directed_action_transitions_covered"],
                "unreachable": coverage["structurally_unreachable_transitions"],
                "client_or_model_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
