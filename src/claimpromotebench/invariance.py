"""Audit oracle, artifact, and prompt behavior under semantics-preserving transformations."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from .dataset import (
    load_json,
    load_jsonl,
    repository_root,
    validate_dataset,
    validate_with_schema,
)
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .executable import verify_dataset_artifact
from .formal import verify_formal_artifact_binding
from .hashing import canonical_json, sha256_bytes, sha256_file, verify_artifact
from .oracle import evaluate
from .policy import load_policy
from .prompts import ARMS, render_prompt

SCHEMA_VERSION = "1.0.0"


class TransformStats(TypedDict):
    """Typed counters for one registered metamorphic transformation."""

    transform_id: str
    description: str
    applicable_items: int
    variants: int
    prompt_identical_variants: int
    prompt_changed_variants: int
    changed_prompt_arms: dict[str, int]


@dataclass(frozen=True)
class Variant:
    """One semantics-preserving item transformation and its comparison metadata."""

    item: dict[str, Any]
    inverse_evidence_ids: dict[str, str]
    expect_prompt_identity: bool


TransformFunction = Callable[[dict[str, Any]], Variant | None]


@dataclass(frozen=True)
class Transform:
    """A registered deterministic metamorphic transformation."""

    transform_id: str
    description: str
    apply: TransformFunction


def _opaque(prefix: str, label: str, length: int = 24) -> str:
    return f"{prefix}{sha256_bytes(label.encode('utf-8'))[7 : 7 + length]}"


def _all_evidence_identifiers(item: dict[str, Any]) -> set[str]:
    identifiers = {str(evidence["id"]) for evidence in item["evidence"]}
    for evidence in item["evidence"]:
        identifiers.update(str(value) for value in evidence.get("dependencies", []))
    identifiers.update(
        str(value) for value in item["requested_transition"].get("basis_evidence_ids", [])
    )
    for basis in item.get("current_state_basis", {}).values():
        if isinstance(basis, dict):
            identifiers.update(str(value) for value in basis.get("evidence_ids", []))
    return identifiers


def _identity_inverse(item: dict[str, Any]) -> dict[str, str]:
    return {value: value for value in _all_evidence_identifiers(item)}


def _reverse_object_key_order(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _reverse_object_key_order(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [_reverse_object_key_order(element) for element in value]
    return deepcopy(value)


def _reverse_key_order(item: dict[str, Any]) -> Variant:
    value = _reverse_object_key_order(item)
    if not isinstance(value, dict):
        raise DatasetIntegrityError("key-order transformation did not produce an object")
    return Variant(value, _identity_inverse(value), True)


def _rename_evidence_ids(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    identifiers = sorted(_all_evidence_identifiers(variant))
    mapping = {old: _opaque("ev-", f"{item['id']}:evidence-id:{old}") for old in identifiers}
    if len(set(mapping.values())) != len(mapping):
        raise DatasetIntegrityError("evidence-ID metamorphic mapping collided")

    for evidence in variant["evidence"]:
        evidence["id"] = mapping[str(evidence["id"])]
        evidence["dependencies"] = [
            mapping[str(value)] for value in evidence.get("dependencies", [])
        ]
    transition = variant["requested_transition"]
    transition["basis_evidence_ids"] = [
        mapping[str(value)] for value in transition["basis_evidence_ids"]
    ]
    for basis in variant.get("current_state_basis", {}).values():
        if isinstance(basis, dict):
            basis["evidence_ids"] = [mapping[str(value)] for value in basis.get("evidence_ids", [])]
    return Variant(
        variant,
        {new: old for old, new in mapping.items()},
        False,
    )


def _rename_principals(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    context = variant["claim_context"]
    values = {str(context["author_id"])}
    values.update(str(evidence["provenance"]["actor_id"]) for evidence in variant["evidence"])
    mapping = {
        old: _opaque("principal-", f"{item['id']}:principal:{old}") for old in sorted(values)
    }
    context["author_id"] = mapping[str(context["author_id"])]
    for evidence in variant["evidence"]:
        provenance = evidence["provenance"]
        provenance["actor_id"] = mapping[str(provenance["actor_id"])]
    return Variant(variant, _identity_inverse(variant), False)


def _rename_environments(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    context = variant["claim_context"]
    values = {str(context["author_environment_sha256"])}
    values.update(
        str(evidence["provenance"]["environment_sha256"]) for evidence in variant["evidence"]
    )
    mapping = {
        old: sha256_bytes(f"{item['id']}:environment:{old}".encode()) for old in sorted(values)
    }
    context["author_environment_sha256"] = mapping[str(context["author_environment_sha256"])]
    for evidence in variant["evidence"]:
        provenance = evidence["provenance"]
        provenance["environment_sha256"] = mapping[str(provenance["environment_sha256"])]
    return Variant(variant, _identity_inverse(variant), False)


def _rename_run_ids(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    values = {str(evidence["provenance"]["run_id"]) for evidence in variant["evidence"]}
    mapping = {old: _opaque("run-", f"{item['id']}:run:{old}") for old in sorted(values)}
    for evidence in variant["evidence"]:
        provenance = evidence["provenance"]
        provenance["run_id"] = mapping[str(provenance["run_id"])]
    return Variant(variant, _identity_inverse(variant), False)


def _reverse_evidence_array(item: dict[str, Any]) -> Variant | None:
    if len(item["evidence"]) < 2:
        return None
    variant = deepcopy(item)
    variant["evidence"] = list(reversed(variant["evidence"]))
    return Variant(variant, _identity_inverse(variant), False)


def _new_unreferenced_evidence(
    item: dict[str, Any],
    transform_id: str,
    *,
    evidence_type: str,
    timestamp: str,
    tool_exit: int,
    verifier_result: str,
    contradiction_status: str | None = None,
) -> dict[str, Any]:
    source = item["evidence"][0]
    context = item["claim_context"]
    evidence_id = _opaque("ev-", f"{item['id']}:{transform_id}:distractor")
    if evidence_id in _all_evidence_identifiers(item):
        raise DatasetIntegrityError("metamorphic distractor evidence ID collided")
    scope: dict[str, Any] = {
        "claim_id": context["claim_id"],
        "statement_sha256": context["statement_sha256"],
    }
    if contradiction_status is not None:
        scope["contradiction_status"] = contradiction_status
    actor_role = "INDEPENDENT_REVIEWER" if evidence_type == "CONTRADICTION" else "TOOL"
    actor_id = _opaque("principal-", f"{item['id']}:{transform_id}:actor")
    environment = sha256_bytes(f"{item['id']}:{transform_id}:environment".encode())
    if actor_id == context["author_id"]:
        actor_id = f"{actor_id}-independent"
    if environment == context["author_environment_sha256"]:
        environment = sha256_bytes(f"{environment}:independent".encode())
    return {
        "id": evidence_id,
        "type": evidence_type,
        "provenance": {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "run_id": _opaque("run-", f"{item['id']}:{transform_id}:run"),
            "environment_sha256": environment,
            "cold_start": True,
        },
        "artifact_path": source["artifact_path"],
        "artifact_hash": source["artifact_hash"],
        "scope": scope,
        "dependencies": [],
        "tool_exit": tool_exit,
        "verifier_result": verifier_result,
        "timestamp": timestamp,
    }


def _append_valid_artifact(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    variant["evidence"].append(
        _new_unreferenced_evidence(
            item,
            "append_valid_unreferenced_artifact",
            evidence_type="ARTIFACT",
            timestamp="2026-08-01T00:00:00Z",
            tool_exit=0,
            verifier_result="PASS",
        )
    )
    return Variant(variant, _identity_inverse(variant), False)


def _prepend_stale_failed_artifact(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    variant["evidence"].insert(
        0,
        _new_unreferenced_evidence(
            item,
            "prepend_stale_failed_unreferenced_artifact",
            evidence_type="ARTIFACT",
            timestamp="2000-01-01T00:00:00Z",
            tool_exit=1,
            verifier_result="FAIL",
        ),
    )
    return Variant(variant, _identity_inverse(variant), False)


def _append_resolved_contradiction(item: dict[str, Any]) -> Variant:
    variant = deepcopy(item)
    variant["evidence"].append(
        _new_unreferenced_evidence(
            item,
            "append_resolved_contradiction",
            evidence_type="CONTRADICTION",
            timestamp="2026-08-01T00:00:00Z",
            tool_exit=0,
            verifier_result="PASS",
            contradiction_status="RESOLVED",
        )
    )
    return Variant(variant, _identity_inverse(variant), False)


TRANSFORMS = (
    Transform(
        "reverse_json_object_key_order",
        "Reverse object insertion order recursively; JSON object semantics "
        "and prompts must remain identical.",
        _reverse_key_order,
    ),
    Transform(
        "rename_evidence_identifiers",
        "Rename all present and referenced evidence identifiers consistently.",
        _rename_evidence_ids,
    ),
    Transform(
        "rename_principal_identifiers",
        "Rename authors and evidence actors consistently while preserving equality relations.",
        _rename_principals,
    ),
    Transform(
        "rename_environment_identifiers",
        "Rename author and evidence environment digests consistently while "
        "preserving equality relations.",
        _rename_environments,
    ),
    Transform(
        "rename_provenance_run_identifiers",
        "Rename provenance run identifiers that are not transition-policy inputs.",
        _rename_run_ids,
    ),
    Transform(
        "reverse_evidence_array",
        "Reverse the evidence array when at least two records exist.",
        _reverse_evidence_array,
    ),
    Transform(
        "append_valid_unreferenced_artifact",
        "Append a fresh passing artifact that is outside the transition dependency closure.",
        _append_valid_artifact,
    ),
    Transform(
        "prepend_stale_failed_unreferenced_artifact",
        "Prepend stale failed evidence outside the transition dependency closure.",
        _prepend_stale_failed_artifact,
    ),
    Transform(
        "append_resolved_contradiction",
        "Append an independently sourced resolved contradiction that must not escalate.",
        _append_resolved_contradiction,
    ),
)


def _normalize_decision(
    decision: dict[str, Any],
    inverse_evidence_ids: dict[str, str],
) -> dict[str, Any]:
    value = deepcopy(decision)
    for field in (
        "used_evidence_ids",
        "missing_evidence_ids",
        "minimal_missing_evidence",
    ):
        identifiers = value.get(field, [])
        if not isinstance(identifiers, list):
            raise DatasetIntegrityError(f"oracle decision field is not an array: {field}")
        value[field] = sorted(
            {
                inverse_evidence_ids.get(str(identifier), str(identifier))
                for identifier in identifiers
            }
        )
    return value


def _validate_variant_artifacts(
    dataset_dir: Path,
    item: dict[str, Any],
    *,
    require_scope_match: bool,
) -> None:
    for evidence in item["evidence"]:
        verify_artifact(dataset_dir, evidence)
        artifact_path = str(evidence["artifact_path"])
        if evidence["type"] == "COMPUTATION" and artifact_path.endswith(".json"):
            verify_dataset_artifact(
                dataset_dir,
                evidence,
                require_scope_match=require_scope_match,
            )
        if item["family"] == "FORMAL" and evidence["type"] == "FORMAL_CERTIFICATE":
            verify_formal_artifact_binding(
                dataset_dir,
                item,
                evidence,
                require_scope_match=require_scope_match,
            )


def _failure(
    item_id: str,
    transform_id: str,
    stage: str,
    error: BaseException | str,
) -> dict[str, str]:
    message = str(error)
    if not message and isinstance(error, BaseException):
        message = error.__class__.__name__
    return {
        "item_id": item_id,
        "transform_id": transform_id,
        "stage": stage,
        "message": message,
    }


def _report_identity(report: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(report)
    value.pop("report_id", None)
    return value


def audit_invariance(dataset_dir: Path) -> dict[str, Any]:
    """Run every registered transformation over the complete manifest-bound dataset."""

    validate_dataset(dataset_dir)
    root = repository_root()
    manifest = load_json(dataset_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("dataset manifest must be an object")
    policy_path = root / "policies" / str(manifest["policy_file"])
    policy = load_policy(policy_path)
    evaluation_time = str(manifest["evaluation_time"])
    items = load_jsonl(dataset_dir / "inputs.jsonl")
    input_schema = root / "schemas" / "benchmark-input.schema.json"

    stats: dict[str, TransformStats] = {
        transform.transform_id: {
            "transform_id": transform.transform_id,
            "description": transform.description,
            "applicable_items": 0,
            "variants": 0,
            "prompt_identical_variants": 0,
            "prompt_changed_variants": 0,
            "changed_prompt_arms": {arm: 0 for arm in ARMS},
        }
        for transform in TRANSFORMS
    }
    failures: list[dict[str, str]] = []
    total_variants = 0
    oracle_equivalent = 0
    schema_validated = 0
    artifact_validated = 0
    prompt_renderings = 0

    for item in items:
        item_id = str(item["id"])
        base_decision = evaluate(item, policy, evaluation_time)
        base_normalized = _normalize_decision(base_decision, _identity_inverse(item))
        base_prompts = {
            arm: render_prompt(
                item,
                arm,
                dataset_dir,
                policy=policy,
                evaluation_time=evaluation_time,
            )
            for arm in ARMS
        }
        for transform in TRANSFORMS:
            transform_stats = stats[transform.transform_id]
            try:
                variant = transform.apply(item)
            except Exception as exc:
                failures.append(_failure(item_id, transform.transform_id, "TRANSFORM", exc))
                continue
            if variant is None:
                continue
            transform_stats["applicable_items"] += 1
            transform_stats["variants"] += 1
            total_variants += 1

            try:
                validate_with_schema(
                    variant.item,
                    input_schema,
                    f"{item_id}:{transform.transform_id}",
                )
                schema_validated += 1
            except Exception as exc:
                failures.append(_failure(item_id, transform.transform_id, "SCHEMA", exc))
                continue

            try:
                _validate_variant_artifacts(
                    dataset_dir,
                    variant.item,
                    require_scope_match=base_decision["action"] == "ALLOW",
                )
                artifact_validated += 1
            except Exception as exc:
                failures.append(_failure(item_id, transform.transform_id, "ARTIFACT", exc))
                continue

            try:
                variant_decision = evaluate(variant.item, policy, evaluation_time)
                variant_normalized = _normalize_decision(
                    variant_decision,
                    variant.inverse_evidence_ids,
                )
                if canonical_json(variant_normalized) != canonical_json(base_normalized):
                    raise DatasetIntegrityError(
                        "normalized oracle decision changed: "
                        f"base={canonical_json(base_normalized)}; "
                        f"variant={canonical_json(variant_normalized)}"
                    )
                oracle_equivalent += 1
            except Exception as exc:
                failures.append(_failure(item_id, transform.transform_id, "ORACLE", exc))
                continue

            try:
                changed_arms: list[str] = []
                for arm in ARMS:
                    variant_prompt = render_prompt(
                        variant.item,
                        arm,
                        dataset_dir,
                        policy=policy,
                        evaluation_time=evaluation_time,
                    )
                    prompt_renderings += 1
                    if variant_prompt != base_prompts[arm]:
                        changed_arms.append(arm)
                        transform_stats["changed_prompt_arms"][arm] += 1
                if changed_arms:
                    transform_stats["prompt_changed_variants"] += 1
                else:
                    transform_stats["prompt_identical_variants"] += 1
                if variant.expect_prompt_identity and changed_arms:
                    raise DatasetIntegrityError(
                        f"prompt changed under object-key reordering: {changed_arms}"
                    )
                if not variant.expect_prompt_identity and not changed_arms:
                    raise DatasetIntegrityError(
                        "model-facing transformation did not change any rendered prompt"
                    )
            except Exception as exc:
                stage = "PROMPT_EXPECTATION" if isinstance(exc, DatasetIntegrityError) else "PROMPT"
                failures.append(_failure(item_id, transform.transform_id, stage, exc))

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
        "policy_sha256": sha256_file(policy_path),
        "evaluation_time": evaluation_time,
        "base_items": len(items),
        "total_variants": total_variants,
        "oracle_equivalent_variants": oracle_equivalent,
        "schema_validated_variants": schema_validated,
        "artifact_validated_variants": artifact_validated,
        "prompt_renderings": prompt_renderings,
        "transformations": [stats[transform.transform_id] for transform in TRANSFORMS],
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }
    report["report_id"] = sha256_bytes(canonical_json(_report_identity(report)).encode("utf-8"))
    validate_with_schema(
        report,
        root / "schemas" / "invariance-report.schema.json",
        "metamorphic-invariance-report",
    )
    return report


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the model-free metamorphic invariance audit."""

    parser = argparse.ArgumentParser(prog="cpb-audit-invariance", description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit_invariance(args.dataset)
        if args.out:
            _write_json(args.out, report)
            output = {
                "status": report["status"],
                "base_items": report["base_items"],
                "total_variants": report["total_variants"],
                "failures": len(report["failures"]),
                "out": str(args.out),
            }
        else:
            output = report
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
