#!/usr/bin/env python3
"""Build paired items that differ only in the active author policy profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from policy_switch import evaluate_policy_switch, load_switch_policy  # noqa: E402
from slsa_policy import candidate_state, load_slsa_policy  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
Split = Literal["development", "evaluation"]

BASE_POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"
SWITCH_POLICY_PATH = ROOT / "v2" / "policy-switch-v1" / "policy-contract.json"
SOURCE_REGISTRY = ROOT / "v2" / "slsa-portability-v1" / "source-registry.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"
STUDY_ID = "claimpromotebench-policy-profile-switch-2026-08-v1"


@dataclass(frozen=True)
class Factor:
    factor_id: str
    family: str
    non_allow_action: str
    observed_field: str
    invalid_value: bool | str


FACTORS = (
    Factor(
        "candidate_provenance_profile", "candidate_admission", "HOLD", "provenance_present", False
    ),
    Factor(
        "candidate_signature_profile",
        "candidate_admission",
        "HOLD",
        "envelope_signature_verified",
        False,
    ),
    Factor(
        "candidate_subject_profile",
        "candidate_admission",
        "HOLD",
        "subject_digest_matches",
        False,
    ),
    Factor(
        "candidate_attester_profile",
        "candidate_admission",
        "HOLD",
        "attester_recognized",
        False,
    ),
    Factor(
        "current_builder_profile",
        "current_basis",
        "DEMOTE",
        "builder_id_matches_policy",
        False,
    ),
    Factor(
        "current_source_uri_profile",
        "current_basis",
        "DEMOTE",
        "source_uri_matches",
        False,
    ),
    Factor(
        "current_source_ref_profile",
        "current_basis",
        "DEMOTE",
        "source_ref_matches",
        False,
    ),
    Factor(
        "current_policy_digest_profile",
        "current_basis",
        "DEMOTE",
        "policy_digest_matches",
        False,
    ),
    Factor(
        "source_revision_conflict_profile",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "SOURCE_REVISION_CONFLICT",
    ),
    Factor(
        "build_parameters_conflict_profile",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "BUILD_PARAMETERS_CONFLICT",
    ),
    Factor(
        "vsa_policy_conflict_profile",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "VSA_POLICY_CONFLICT",
    ),
    Factor(
        "verification_result_conflict_profile",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "VERIFICATION_RESULT_CONFLICT",
    ),
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
    raise SystemExit(f"policy-switch-build: {message}")


def stable_hex(label: str, length: int = 64) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:length]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def changed_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix or "/"]
    if isinstance(left, dict):
        if set(left) != set(right):
            return [prefix or "/"]
        paths: list[str] = []
        for key in left:
            paths.extend(changed_paths(left[key], right[key], f"{prefix}/{key}"))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [prefix or "/"]
        paths = []
        for index, (left_value, right_value) in enumerate(zip(left, right, strict=True)):
            paths.extend(changed_paths(left_value, right_value, f"{prefix}/{index}"))
        return paths
    return [] if left == right else [prefix or "/"]


def valid_observed(base_policy: Json, target_level: int) -> Json:
    observed: Json = {str(check["field"]): True for check in base_policy["boolean_checks"]}
    observed["build_level_verified"] = target_level
    observed["authenticated_conflicts"] = []
    return observed


def make_shared_item(
    split: Split,
    factor: Factor,
    factor_index: int,
    variant: int,
    base_policy: Json,
) -> Json:
    seed = f"{STUDY_ID}:{split}:{factor.factor_id}:{variant}"
    artifact_name = ARTIFACT_STEMS[(factor_index + variant) % len(ARTIFACT_STEMS)]
    target_level = 1 + ((factor_index + variant) % 3)
    current = candidate_state()
    if factor.non_allow_action == "DEMOTE":
        current = {
            "release_status": "ADMITTED",
            "accepted_build_level": target_level,
            "incident_review_required": False,
        }
    digest = stable_hex(seed)
    observed = valid_observed(base_policy, target_level)
    if factor.observed_field == "authenticated_conflicts":
        observed[factor.observed_field] = [factor.invalid_value]
    else:
        observed[factor.observed_field] = factor.invalid_value
    return {
        "schema_version": "1.0.0",
        "active_policy_profile": "POLICY_BLUE",
        "claim_text": (
            f"Artifact {artifact_name} with sha256 digest {digest} may enter the protected "
            f"release channel at verified SLSA Build L{target_level}."
        ),
        "artifact": {
            "name": artifact_name,
            "sha256": digest,
            "expected_source_uri": f"https://code.example/policy-switch/{artifact_name}",
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


def binding_profile(factor: Factor, switch_policy: Json) -> str:
    key = (
        "escalated_conflict_codes"
        if factor.observed_field == "authenticated_conflicts"
        else "enforced_boolean_fields"
    )
    matches = [
        profile_id
        for profile_id in switch_policy["profile_order"]
        if factor.invalid_value in switch_policy["profiles"][profile_id][key]
        or factor.observed_field in switch_policy["profiles"][profile_id][key]
    ]
    if len(matches) != 1:
        fail(f"factor does not bind exactly one profile: {factor.factor_id}")
    return str(matches[0])


def public_base_contract(base_policy: Json) -> Json:
    return {
        key: deepcopy(base_policy[key])
        for key in (
            "schema_version",
            "policy_id",
            "interpretation_boundary",
            "action_precedence",
            "action_semantics",
            "boolean_checks",
            "level_check",
            "authenticated_conflict_codes",
            "reason_order",
        )
    }


def public_switch_contract(switch_policy: Json) -> Json:
    return {
        key: deepcopy(switch_policy[key])
        for key in (
            "schema_version",
            "policy_id",
            "interpretation_boundary",
            "action_precedence",
            "profile_order",
            "profiles",
        )
    }


def render_prompt(item: Json, base_policy: Json, switch_policy: Json) -> str:
    schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
    return (
        "Apply the active counterfactual policy profile to one typed evidence snapshot.\n"
        "Only boolean fields listed by the active profile are binding. Only conflict codes listed "
        "by the active profile trigger escalation. Other false fields or conflicts do not block "
        "the requested transition.\n"
        "Verifier fields are passive observations and contain no transition decision.\n"
        "Return one JSON object and no surrounding text. It must satisfy DECISION_JSON_SCHEMA "
        "exactly. p_admissible must be a JSON number in [0,1], never true or false.\n"
        "Use only published action and reason-code strings, and preserve policy reason order.\n\n"
        "DECISION_JSON_SCHEMA\n"
        + canonical_json(schema)
        + "\n\nBASE_EVIDENCE_CONTRACT\n"
        + canonical_json(public_base_contract(base_policy))
        + "\n\nCOUNTERFACTUAL_PROFILE_CONTRACT\n"
        + canonical_json(public_switch_contract(switch_policy))
        + "\n\nITEM\n"
        + canonical_json(item)
    )


def build_split(
    split: Split,
    variants: int,
    base_policy: Json,
    switch_policy: Json,
) -> tuple[list[Json], list[Json], list[Json]]:
    items: list[Json] = []
    gold: list[Json] = []
    pairs: list[Json] = []
    for factor_index, factor in enumerate(FACTORS):
        enforced_profile = binding_profile(factor, switch_policy)
        for variant in range(variants):
            pair_number = factor_index * variants + variant + 1
            pair_id = f"psw-{split[:3]}-{pair_number:03d}"
            shared = make_shared_item(split, factor, factor_index, variant, base_policy)
            members: list[tuple[Json, Json]] = []
            for profile_id in switch_policy["profile_order"]:
                item = deepcopy(shared)
                item["active_policy_profile"] = profile_id
                decision = evaluate_policy_switch(item, switch_policy, base_policy)
                expected = factor.non_allow_action if profile_id == enforced_profile else "ALLOW"
                if decision["action"] != expected:
                    fail(f"unexpected action for {pair_id}/{profile_id}: {decision['action']}")
                members.append((item, decision))
            if changed_paths(members[0][0], members[1][0]) != ["/active_policy_profile"]:
                fail(f"pair is not isolated at active_policy_profile: {pair_id}")
            if {str(value[1]["action"]) for value in members} != {
                "ALLOW",
                factor.non_allow_action,
            }:
                fail(f"pair does not change the action: {pair_id}")

            reverse = int(stable_hex(pair_id, 2), 16) % 2 == 0
            ordered = list(reversed(members)) if reverse else members
            member_ids: list[str] = []
            expected_actions: list[str] = []
            active_profiles: list[str] = []
            for suffix, (model_visible, decision) in zip(("a", "b"), ordered, strict=True):
                item_id = f"{pair_id}-{suffix}"
                member_ids.append(item_id)
                expected_actions.append(str(decision["action"]))
                active_profiles.append(str(model_visible["active_policy_profile"]))
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
                        "factor_id": factor.factor_id,
                        "family": factor.family,
                        "binding_profile": enforced_profile,
                        "decision": decision,
                    }
                )
            pairs.append(
                {
                    "pair_id": pair_id,
                    "split": split,
                    "factor_id": factor.factor_id,
                    "family": factor.family,
                    "controlled_path": "/active_policy_profile",
                    "binding_profile": enforced_profile,
                    "member_ids": member_ids,
                    "active_profiles": active_profiles,
                    "expected_actions": expected_actions,
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
    evaluation = build_split("evaluation", 5, base_policy, switch_policy)
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
    packet_records: list[Json] = []
    for row in sorted(evaluation[0], key=lambda value: str(value["id"])):
        prompt = render_prompt(row["model_visible"], base_policy, switch_policy)
        packet_records.append(
            {
                "item_id": row["id"],
                "pair_id": row["pair_id"],
                "prompt": prompt,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "utf8_bytes": len(prompt.encode("utf-8")),
            }
        )
    packet: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_CREDENTIAL_FREE_PROMPT_PACKET",
        "contains_gold": False,
        "contains_credentials": False,
        "dataset_fingerprint": fingerprint,
        "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
        "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "records": packet_records,
    }
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode("utf-8"))
    write_json(out_root / "evaluation-prompt-packet.json", packet)

    expected_dev = Counter({"ALLOW": 36, "HOLD": 12, "DEMOTE": 12, "ESCALATE": 12})
    expected_eval = Counter({"ALLOW": 60, "HOLD": 20, "DEMOTE": 20, "ESCALATE": 20})
    dev_actions = Counter(str(row["decision"]["action"]) for row in development[1])
    eval_actions = Counter(str(row["decision"]["action"]) for row in evaluation[1])
    if dev_actions != expected_dev or eval_actions != expected_eval:
        fail(f"unexpected action support: development={dev_actions}, evaluation={eval_actions}")
    profile_support = Counter(
        str(row["model_visible"]["active_policy_profile"]) for row in evaluation[0]
    )
    if profile_support != Counter({"POLICY_BLUE": 60, "POLICY_AMBER": 60}):
        fail(f"unexpected profile support: {profile_support}")

    manifest: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "SYNTHETIC_COUNTERFACTUAL_POLICY_SWITCH_DATASET",
        "interpretation_boundary": switch_policy["interpretation_boundary"],
        "development": {
            "pairs": len(development[2]),
            "items": len(development[0]),
            "factors": len(FACTORS),
            "action_counts": dict(sorted(dev_actions.items())),
        },
        "evaluation": {
            "pairs": len(evaluation[2]),
            "items": len(evaluation[0]),
            "factors": len(FACTORS),
            "action_counts": dict(sorted(eval_actions.items())),
            "profile_counts": dict(sorted(profile_support.items())),
        },
        "pair_contract": switch_policy["pair_contract"],
        "shortcut_hypothesis": switch_policy["shortcut_hypothesis"],
        "dataset_fingerprint": fingerprint,
        "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
        "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
        "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "data_file_sha256": file_hashes,
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": sha256_file(out_root / "evaluation-prompt-packet.json"),
        "factor_inventory": [
            {
                "factor_id": factor.factor_id,
                "family": factor.family,
                "non_allow_action": factor.non_allow_action,
                "isolated_evidence_feature": factor.observed_field,
                "binding_profile": binding_profile(factor, switch_policy),
            }
            for factor in FACTORS
        ],
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
                "dataset_fingerprint": result["dataset_fingerprint"],
                "development_items": result["development"]["items"],
                "evaluation_items": result["evaluation"]["items"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
