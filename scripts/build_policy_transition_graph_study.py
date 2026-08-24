#!/usr/bin/env python3
"""Build a policy-switch suite covering every reachable directed action transition."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

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
    valid_observed,
)
from policy_switch import evaluate_policy_switch, load_switch_policy  # noqa: E402
from slsa_policy import candidate_state, load_slsa_policy  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
Split = Literal["development", "evaluation"]
STUDY_ID = "claimpromotebench-policy-transition-graph-2026-08-v1"
PROFILE_ORDER = ("POLICY_BLUE", "POLICY_AMBER")
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
UNREACHABLE_TRANSITIONS = ("HOLD->DEMOTE", "DEMOTE->HOLD")
REACHABLE_TRANSITIONS = tuple(
    f"{left}->{right}"
    for left in ACTIONS
    for right in ACTIONS
    if left != right and f"{left}->{right}" not in UNREACHABLE_TRANSITIONS
)
ARTIFACT_STEMS = (
    "attestor-cli",
    "build-worker",
    "release-controller",
    "policy-archive",
    "runtime-wheel",
    "verification-bundle",
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-graph-build: {message}")


def stable_hex(label: str, length: int = 64) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:length]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def action_recipe(
    action: str,
    profile_id: str,
    variant: int,
    switch_policy: Json,
) -> tuple[str | None, str | None]:
    profile = switch_policy["profiles"][profile_id]
    if action in {"HOLD", "DEMOTE"}:
        fields = [str(value) for value in profile["enforced_boolean_fields"]]
        return fields[variant % len(fields)], None
    if action == "ESCALATE":
        conflicts = [str(value) for value in profile["escalated_conflict_codes"]]
        return None, conflicts[variant % len(conflicts)]
    if action == "ALLOW":
        return None, None
    fail(f"unknown action: {action}")


def make_shared_item(
    split: Split,
    transition_index: int,
    transition: str,
    variant: int,
    base_policy: Json,
    switch_policy: Json,
) -> tuple[Json, Json]:
    blue_action, amber_action = transition.split("->")
    if {blue_action, amber_action} == {"HOLD", "DEMOTE"}:
        fail(f"structurally unreachable transition requested: {transition}")
    current_admitted = "DEMOTE" in {blue_action, amber_action}
    if current_admitted and "HOLD" in {blue_action, amber_action}:
        fail(f"one shared current state cannot realize transition: {transition}")

    seed = f"{STUDY_ID}:{split}:{transition}:{variant}"
    artifact_name = ARTIFACT_STEMS[(transition_index + variant) % len(ARTIFACT_STEMS)]
    target_level = 1 + ((transition_index + variant) % 3)
    digest = stable_hex(seed)
    observed = valid_observed(base_policy, target_level)
    rules: Json = {}
    for profile_id, action in zip(PROFILE_ORDER, (blue_action, amber_action), strict=True):
        field, conflict = action_recipe(
            action,
            profile_id,
            variant + transition_index,
            switch_policy,
        )
        if field is not None:
            observed[field] = False
            rules[profile_id] = {"kind": "boolean_field", "rule": field}
        elif conflict is not None:
            observed["authenticated_conflicts"].append(conflict)
            rules[profile_id] = {"kind": "authenticated_conflict", "rule": conflict}
        else:
            rules[profile_id] = {"kind": "none", "rule": None}
    current = candidate_state()
    if current_admitted:
        current = {
            "release_status": "ADMITTED",
            "accepted_build_level": target_level,
            "incident_review_required": False,
        }
    item: Json = {
        "schema_version": "1.0.0",
        "active_policy_profile": "POLICY_BLUE",
        "claim_text": (
            f"Artifact {artifact_name} with sha256 digest {digest} may enter the protected "
            f"release channel at verified SLSA Build L{target_level}."
        ),
        "artifact": {
            "name": artifact_name,
            "sha256": digest,
            "expected_source_uri": f"https://code.example/policy-transition/{artifact_name}",
            "expected_source_ref": stable_hex(seed + ":source", 40),
        },
        "current_state": current,
        "requested_state": {
            "release_status": "ADMITTED",
            "accepted_build_level": target_level,
            "incident_review_required": False,
        },
        "evidence": [
            {
                "evidence_id": "att-" + stable_hex(seed + ":evidence", 16),
                "evidence_type": "SLSA_PROVENANCE_AND_VERIFICATION_SUMMARY",
                "attestation_subject_sha256": digest,
                "observed": observed,
            }
        ],
    }
    return item, rules


def build_split(
    split: Split,
    variants: int,
    base_policy: Json,
    switch_policy: Json,
) -> tuple[list[Json], list[Json], list[Json]]:
    items: list[Json] = []
    gold: list[Json] = []
    pairs: list[Json] = []
    prefix = "dev" if split == "development" else "eva"
    for transition_index, transition in enumerate(REACHABLE_TRANSITIONS):
        expected_by_profile = dict(zip(PROFILE_ORDER, transition.split("->"), strict=True))
        for variant in range(variants):
            pair_number = transition_index * variants + variant + 1
            pair_id = f"ptg-{prefix}-{pair_number:03d}"
            shared, binding_rules = make_shared_item(
                split,
                transition_index,
                transition,
                variant,
                base_policy,
                switch_policy,
            )
            members: list[tuple[Json, Json]] = []
            for profile_id in PROFILE_ORDER:
                item = deepcopy(shared)
                item["active_policy_profile"] = profile_id
                decision = evaluate_policy_switch(item, switch_policy, base_policy)
                if decision["action"] != expected_by_profile[profile_id]:
                    fail(f"unexpected action for {pair_id}/{profile_id}: {decision['action']}")
                members.append((item, decision))
            if changed_paths(members[0][0], members[1][0]) != ["/active_policy_profile"]:
                fail(f"pair changes more than active_policy_profile: {pair_id}")

            reverse = int(stable_hex(pair_id, 2), 16) % 2 == 0
            ordered = list(reversed(members)) if reverse else members
            member_ids: list[str] = []
            active_profiles: list[str] = []
            expected_actions: list[str] = []
            for suffix, (model_visible, decision) in zip(("a", "b"), ordered, strict=True):
                item_id = f"{pair_id}-{suffix}"
                profile_id = str(model_visible["active_policy_profile"])
                member_ids.append(item_id)
                active_profiles.append(profile_id)
                expected_actions.append(str(decision["action"]))
                items.append(
                    {
                        "id": item_id,
                        "pair_id": pair_id,
                        "split": split,
                        "model_visible": model_visible,
                    }
                )
                gold.append(
                    {
                        "id": item_id,
                        "pair_id": pair_id,
                        "split": split,
                        "factor_id": transition.lower().replace("->", "_to_"),
                        "family": "directed_policy_action_transition",
                        "blue_to_amber_transition": transition,
                        "binding_rule": binding_rules[profile_id],
                        "decision": decision,
                    }
                )
            pairs.append(
                {
                    "pair_id": pair_id,
                    "split": split,
                    "factor_id": transition.lower().replace("->", "_to_"),
                    "family": "directed_policy_action_transition",
                    "controlled_path": "/active_policy_profile",
                    "blue_to_amber_transition": transition,
                    "member_ids": member_ids,
                    "active_profiles": active_profiles,
                    "expected_actions": expected_actions,
                    "binding_rules": binding_rules,
                }
            )
    return items, gold, pairs


def build(out_root: Path) -> Json:
    if out_root.exists():
        fail(f"output root already exists: {out_root}")
    out_root.mkdir(parents=True)
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    switch_policy = load_switch_policy(SWITCH_POLICY_PATH, base_policy)
    development = build_split("development", 3, base_policy, switch_policy)
    evaluation = build_split("evaluation", 6, base_policy, switch_policy)
    named_rows = {
        "development-items.jsonl": development[0],
        "development-gold.jsonl": development[1],
        "development-pairs.json": development[2],
        "evaluation-items.jsonl": evaluation[0],
        "evaluation-gold.jsonl": evaluation[1],
        "evaluation-pairs.json": evaluation[2],
    }
    for name, rows in named_rows.items():
        path = out_root / name
        write_json(path, rows) if name.endswith(".json") else write_jsonl(path, rows)

    file_hashes = {name: sha256_file(out_root / name) for name in sorted(named_rows)}
    fingerprint = sha256_bytes(
        canonical_json(
            {
                "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
                "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
                "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "data_file_sha256": file_hashes,
            }
        ).encode("utf-8")
    )
    packet: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "dataset_fingerprint": fingerprint,
        "contains_gold": False,
        "contains_pair_or_factor_metadata_in_prompt": False,
        "contains_credentials": False,
        "records": [],
    }
    for row in evaluation[0]:
        prompt = render_prompt(row["model_visible"], base_policy, switch_policy)
        packet["records"].append(
            {
                "item_id": row["id"],
                "pair_id": row["pair_id"],
                "prompt": prompt,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            }
        )
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode("utf-8"))
    write_json(out_root / "evaluation-prompt-packet.json", packet)

    action_counts = {
        split: Counter(str(row["decision"]["action"]) for row in rows)
        for split, rows in (("development", development[1]), ("evaluation", evaluation[1]))
    }
    profile_counts: dict[str, Counter[str]] = {profile: Counter() for profile in PROFILE_ORDER}
    items_by_id = {str(row["id"]): row for row in evaluation[0]}
    gold_by_id = {str(row["id"]): row for row in evaluation[1]}
    for item_id, item in items_by_id.items():
        profile_counts[str(item["model_visible"]["active_policy_profile"])][
            str(gold_by_id[item_id]["decision"]["action"])
        ] += 1
    expected_profile = Counter({"ALLOW": 18, "ESCALATE": 18, "HOLD": 12, "DEMOTE": 12})
    if any(profile_counts[profile] != expected_profile for profile in PROFILE_ORDER):
        fail(f"profile action support differs: {profile_counts}")

    manifest: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "SYNTHETIC_POLICY_TRANSITION_GRAPH_DATASET",
        "interpretation_boundary": switch_policy["interpretation_boundary"],
        "development": {
            "pairs": len(development[2]),
            "items": len(development[0]),
            "factors": len(REACHABLE_TRANSITIONS),
            "action_counts": dict(sorted(action_counts["development"].items())),
        },
        "evaluation": {
            "pairs": len(evaluation[2]),
            "items": len(evaluation[0]),
            "factors": len(REACHABLE_TRANSITIONS),
            "action_counts": dict(sorted(action_counts["evaluation"].items())),
            "profile_action_counts": {
                profile: dict(sorted(profile_counts[profile].items())) for profile in PROFILE_ORDER
            },
        },
        "pair_contract": switch_policy["pair_contract"],
        "shortcut_hypothesis": switch_policy["shortcut_hypothesis"],
        "transition_graph": {
            "directed_nonself_transitions_possible": 12,
            "directed_transitions_semantically_reachable": len(REACHABLE_TRANSITIONS),
            "reachable_transitions": list(REACHABLE_TRANSITIONS),
            "structurally_unreachable_transitions": list(UNREACHABLE_TRANSITIONS),
            "contexts_per_evaluation_transition": 6,
            "unreachability_reason": (
                "Under the shared-state pair contract, DEMOTE is available only on an ADMITTED "
                "current state with a failed enforced check. On that state, the same failure "
                "reaches DEMOTE before HOLD; on a non-ADMITTED state, DEMOTE is unavailable."
            ),
        },
        "dataset_fingerprint": fingerprint,
        "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
        "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
        "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "data_file_sha256": file_hashes,
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": sha256_file(out_root / "evaluation-prompt-packet.json"),
        "client_or_model_calls": 0,
    }
    write_json(out_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.out_root.resolve())
    print(
        canonical_json(
            {
                "status": result["status"],
                "evaluation_pairs": result["evaluation"]["pairs"],
                "reachable_directed_transitions": result["transition_graph"][
                    "directed_transitions_semantically_reachable"
                ],
                "client_or_model_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
