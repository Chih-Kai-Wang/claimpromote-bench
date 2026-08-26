#!/usr/bin/env python3
"""Build the synthetic SLSA-derived policy-portability dataset and prompt packet."""

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

from slsa_policy import (  # noqa: E402
    candidate_state,
    evaluate_slsa,
    load_slsa_policy,
)

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
Split = Literal["development", "evaluation"]

POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"
SOURCE_REGISTRY = ROOT / "v2" / "slsa-portability-v1" / "source-registry.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"


@dataclass(frozen=True)
class Protocol:
    version: str
    study_id: str
    pair_prefix: str
    variant_offset: int
    include_decision_schema_in_prompt: bool


PROTOCOLS = {
    "v1": Protocol(
        version="v1",
        study_id="claimpromotebench-slsa-policy-portability-2026-08-v1",
        pair_prefix="slsa",
        variant_offset=0,
        include_decision_schema_in_prompt=False,
    ),
    "v2": Protocol(
        version="v2",
        study_id="claimpromotebench-slsa-policy-portability-2026-08-v2",
        pair_prefix="slsa2",
        variant_offset=1000,
        include_decision_schema_in_prompt=True,
    ),
}


@dataclass(frozen=True)
class Factor:
    factor_id: str
    family: str
    invalid_action: str
    mutation_field: str
    mutation_value: bool | str


FACTORS = (
    Factor(
        "candidate_provenance_presence",
        "candidate_admission",
        "HOLD",
        "provenance_present",
        False,
    ),
    Factor(
        "candidate_signature_verification",
        "candidate_admission",
        "HOLD",
        "envelope_signature_verified",
        False,
    ),
    Factor(
        "candidate_subject_binding",
        "candidate_admission",
        "HOLD",
        "subject_digest_matches",
        False,
    ),
    Factor(
        "candidate_build_level",
        "candidate_admission",
        "HOLD",
        "build_level_verified",
        "BELOW_TARGET",
    ),
    Factor("current_provenance_presence", "current_basis", "DEMOTE", "provenance_present", False),
    Factor(
        "current_signature_verification",
        "current_basis",
        "DEMOTE",
        "envelope_signature_verified",
        False,
    ),
    Factor("current_subject_binding", "current_basis", "DEMOTE", "subject_digest_matches", False),
    Factor("current_builder_trust", "current_basis", "DEMOTE", "builder_id_matches_policy", False),
    Factor(
        "authenticated_source_revision_conflict",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "SOURCE_REVISION_CONFLICT",
    ),
    Factor(
        "authenticated_build_parameters_conflict",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "BUILD_PARAMETERS_CONFLICT",
    ),
    Factor(
        "authenticated_vsa_policy_conflict",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "VSA_POLICY_CONFLICT",
    ),
    Factor(
        "authenticated_verification_result_conflict",
        "authenticated_conflict",
        "ESCALATE",
        "authenticated_conflicts",
        "VERIFICATION_RESULT_CONFLICT",
    ),
)

ARTIFACT_STEMS = (
    "cli-darwin-arm64",
    "worker-linux-amd64",
    "controller-image",
    "policy-bundle",
    "sdk-wheel",
    "runtime-archive",
    "verifier-binary",
    "release-manifest",
)
SOURCE_STEMS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")


def fail(message: str) -> None:
    raise SystemExit(f"slsa-portability-build: {message}")


def stable_hex(label: str, length: int = 64) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:length]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def valid_observed(policy: Json, target_level: int) -> Json:
    observed: Json = {str(check["field"]): True for check in policy["boolean_checks"]}
    observed["build_level_verified"] = target_level
    observed["authenticated_conflicts"] = []
    return observed


def model_visible_item(
    split: Split,
    factor: Factor,
    factor_index: int,
    variant: int,
    policy: Json,
    protocol: Protocol,
) -> Json:
    prompt_variant = variant + protocol.variant_offset
    seed = f"{protocol.study_id}:{split}:{factor.factor_id}:{prompt_variant}"
    artifact_name = ARTIFACT_STEMS[(factor_index + prompt_variant) % len(ARTIFACT_STEMS)]
    source_name = SOURCE_STEMS[(factor_index * 2 + prompt_variant) % len(SOURCE_STEMS)]
    target_level = 1 + ((factor_index + prompt_variant) % 3)
    current = candidate_state()
    if factor.invalid_action == "DEMOTE":
        current = {
            "release_status": "ADMITTED",
            "accepted_build_level": target_level,
            "incident_review_required": False,
        }
    requested = {
        "release_status": "ADMITTED",
        "accepted_build_level": target_level,
        "incident_review_required": False,
    }
    digest = stable_hex(seed)
    source_ref = stable_hex(seed + ":source", 40)
    evidence_id = "att-" + stable_hex(seed + ":evidence", 16)
    return {
        "schema_version": "1.0.0",
        "claim_text": (
            f"Artifact {artifact_name} with sha256 digest {digest} may enter the protected "
            f"release channel at verified SLSA Build L{target_level}."
        ),
        "artifact": {
            "name": artifact_name,
            "sha256": digest,
            "expected_source_uri": f"https://code.example/{source_name}/{artifact_name}",
            "expected_source_ref": source_ref,
        },
        "current_state": current,
        "requested_state": requested,
        "evidence": [
            {
                "evidence_id": evidence_id,
                "evidence_type": "SLSA_PROVENANCE_AND_VERIFICATION_SUMMARY",
                "attestation_subject_sha256": digest,
                "observed": valid_observed(policy, target_level),
            }
        ],
    }


def mutate_invalid(item: Json, factor: Factor) -> Json:
    changed = deepcopy(item)
    observed = changed["evidence"][0]["observed"]
    if factor.mutation_field == "build_level_verified":
        target = int(changed["requested_state"]["accepted_build_level"])
        observed[factor.mutation_field] = target - 1
    elif factor.mutation_field == "authenticated_conflicts":
        observed[factor.mutation_field] = [factor.mutation_value]
    else:
        observed[factor.mutation_field] = factor.mutation_value
    return changed


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


def public_contract(policy: Json) -> Json:
    return {
        key: deepcopy(policy[key])
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


def render_prompt(item: Json, policy: Json, protocol: Protocol) -> str:
    prefix = (
        "Apply the complete versioned artifact-admission policy to one typed evidence snapshot.\n"
        "Verifier fields are passive observations; they do not contain a transition decision.\n"
        "Return one JSON object and no surrounding text. The object must have exactly six fields:\n"
        "action, proposed_state, p_admissible, used_evidence_ids, reason_codes, "
        "missing_evidence_ids.\n"
        "Use only policy action and reason-code strings. Preserve policy reason order.\n"
    )
    if protocol.include_decision_schema_in_prompt:
        schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
        prefix += (
            "The object must satisfy DECISION_JSON_SCHEMA exactly. p_admissible must be a JSON "
            "number in [0,1], never true or false.\n\n"
            "DECISION_JSON_SCHEMA\n" + canonical_json(schema) + "\n\n"
        )
    return (
        prefix
        + "POLICY_CONTRACT\n"
        + canonical_json(public_contract(policy))
        + "\n\nITEM\n"
        + canonical_json(item)
    )


def build_split(
    split: Split, variants: int, policy: Json, protocol: Protocol
) -> tuple[list[Json], list[Json], list[Json]]:
    items: list[Json] = []
    gold: list[Json] = []
    pairs: list[Json] = []
    for factor_index, factor in enumerate(FACTORS):
        for variant in range(variants):
            pair_number = factor_index * variants + variant + 1
            pair_id = f"{protocol.pair_prefix}-{split[:3]}-{pair_number:03d}"
            valid = model_visible_item(split, factor, factor_index, variant, policy, protocol)
            invalid = mutate_invalid(valid, factor)
            expected_path = f"/evidence/0/observed/{factor.mutation_field}"
            if changed_paths(valid, invalid) != [expected_path]:
                fail(f"pair {pair_id} is not isolated at {expected_path}")
            valid_decision = evaluate_slsa(valid, policy)
            invalid_decision = evaluate_slsa(invalid, policy)
            if valid_decision["action"] != "ALLOW":
                fail(f"valid member is not ALLOW: {pair_id}")
            if invalid_decision["action"] != factor.invalid_action:
                fail(f"invalid member action differs from factor contract: {pair_id}")

            invalid_first = int(stable_hex(pair_id, 2), 16) % 2 == 0
            ordered = (
                [(invalid, invalid_decision), (valid, valid_decision)]
                if invalid_first
                else [
                    (valid, valid_decision),
                    (invalid, invalid_decision),
                ]
            )
            member_ids: list[str] = []
            expected_actions: list[str] = []
            for suffix, (model_visible, decision) in zip(("a", "b"), ordered, strict=True):
                item_id = f"{pair_id}-{suffix}"
                member_ids.append(item_id)
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
                        "factor_id": factor.factor_id,
                        "family": factor.family,
                        "decision": decision,
                    }
                )
            pairs.append(
                {
                    "pair_id": pair_id,
                    "split": split,
                    "factor_id": factor.factor_id,
                    "family": factor.family,
                    "controlled_path": expected_path,
                    "member_ids": member_ids,
                    "expected_actions": expected_actions,
                }
            )
    return items, gold, pairs


def build(out_root: Path, protocol_version: str = "v2") -> Json:
    if out_root.exists():
        fail(f"output root already exists: {out_root}")
    try:
        protocol = PROTOCOLS[protocol_version]
    except KeyError:
        fail(f"unsupported protocol version: {protocol_version}")
    out_root.mkdir(parents=True)
    policy = load_slsa_policy(POLICY_PATH)
    source_registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    if source_registry.get("status") != "PINNED_PRIMARY_SOURCES":
        fail("source registry is not pinned")

    development = build_split("development", 3, policy, protocol)
    evaluation = build_split("evaluation", 5, policy, protocol)
    names_and_rows = {
        "development-items.jsonl": development[0],
        "development-gold.jsonl": development[1],
        "development-pairs.json": development[2],
        "evaluation-items.jsonl": evaluation[0],
        "evaluation-gold.jsonl": evaluation[1],
        "evaluation-pairs.json": evaluation[2],
    }
    for name, rows in names_and_rows.items():
        path = out_root / name
        write_json(path, rows) if name.endswith(".json") else write_jsonl(path, rows)

    data_hashes = {name: sha256_file(out_root / name) for name in sorted(names_and_rows)}
    dataset_fingerprint = sha256_bytes(
        canonical_json(
            {
                "policy_sha256": sha256_file(POLICY_PATH),
                "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "data_file_sha256": data_hashes,
            }
        ).encode("utf-8")
    )

    packet_records = []
    for item in sorted(evaluation[0], key=lambda row: str(row["id"])):
        prompt = render_prompt(item["model_visible"], policy, protocol)
        packet_records.append(
            {
                "item_id": item["id"],
                "pair_id": item["pair_id"],
                "prompt": prompt,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "utf8_bytes": len(prompt.encode("utf-8")),
            }
        )
    packet: Json = {
        "schema_version": "1.0.0",
        "study_id": protocol.study_id,
        "protocol_version": protocol.version,
        "status": "FROZEN_CREDENTIAL_FREE_PROMPT_PACKET",
        "contains_gold": False,
        "contains_credentials": False,
        "dataset_fingerprint": dataset_fingerprint,
        "policy_sha256": sha256_file(POLICY_PATH),
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "records": packet_records,
    }
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode("utf-8"))
    packet_path = out_root / "evaluation-prompt-packet.json"
    write_json(packet_path, packet)

    dev_actions = Counter(str(row["decision"]["action"]) for row in development[1])
    eval_actions = Counter(str(row["decision"]["action"]) for row in evaluation[1])
    if dev_actions != Counter({"ALLOW": 36, "HOLD": 12, "DEMOTE": 12, "ESCALATE": 12}):
        fail(f"unexpected development action distribution: {dev_actions}")
    if eval_actions != Counter({"ALLOW": 60, "HOLD": 20, "DEMOTE": 20, "ESCALATE": 20}):
        fail(f"unexpected evaluation action distribution: {eval_actions}")

    manifest: Json = {
        "schema_version": "1.0.0",
        "study_id": protocol.study_id,
        "protocol_version": protocol.version,
        "status": "SYNTHETIC_POLICY_PORTABILITY_DATASET",
        "policy_scope": "AUTHOR_OPERATIONALIZATION_GROUNDED_IN_SLSA_AND_IN_TOTO",
        "interpretation_boundary": (
            "This dataset evaluates conformance to the published author policy. It does not "
            "certify SLSA compliance, software security, or external policy consensus."
        ),
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
        },
        "pair_contract": "Each pair changes one model-visible verifier field.",
        "prompt_contract": {
            "complete_decision_schema_visible": protocol.include_decision_schema_in_prompt,
            "same_prompt_bytes_for_every_lane": True,
            "fresh_relative_to_v1": protocol.version == "v2",
        },
        "dataset_fingerprint": dataset_fingerprint,
        "policy_sha256": sha256_file(POLICY_PATH),
        "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "data_file_sha256": data_hashes,
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": sha256_file(packet_path),
        "factor_inventory": [
            {
                "factor_id": factor.factor_id,
                "family": factor.family,
                "invalid_action": factor.invalid_action,
                "controlled_field": factor.mutation_field,
            }
            for factor in FACTORS
        ],
    }
    write_json(out_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--protocol-version", choices=sorted(PROTOCOLS), default="v2")
    args = parser.parse_args()
    result = build(args.out_root.resolve(), args.protocol_version)
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
