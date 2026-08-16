"""Policy-blind feature extraction for shortcut audits."""

from __future__ import annotations

from typing import Any

from .hashing import canonical_json
from .state import STATE_ORDER

TIERS = ("metadata_only", "shallow_structure")

EXCLUDED_FIELDS = {
    "_artifact_hash",
    "family",
    "gold",
    "id",
    "pair_id",
    "split",
}
EVIDENCE_TYPES = (
    "COMPUTATION",
    "CONTRADICTION",
    "DEPENDENCY",
    "FORMAL_CERTIFICATE",
    "REVIEW",
)
SCOPE_KEYS = (
    "claim_id",
    "contradiction_status",
    "domain",
    "precision_bits",
    "preregistered",
    "protocol_id",
    "protocol_version",
    "repetitions",
    "statement_sha256",
    "toolchain_lock_sha256",
    "verifier",
)


def _model_view(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in EXCLUDED_FIELDS}


def _changed_axes(item: dict[str, Any]) -> tuple[str, ...]:
    current = item["current_state"]
    target = item["requested_transition"]["target_state"]
    return tuple(axis for axis in STATE_ORDER if current[axis] != target[axis])


def _metadata_features(item: dict[str, Any]) -> dict[str, float]:
    evidence = list(item.get("evidence", []))
    dependencies = [
        dependency for record in evidence for dependency in record.get("dependencies", [])
    ]
    return {
        "serialized_chars": float(len(canonical_json(_model_view(item)))),
        "claim_chars": float(len(str(item.get("claim_text", "")))),
        "evidence_count": float(len(evidence)),
        "dependency_edge_count": float(len(dependencies)),
        "basis_count": float(
            len(item.get("requested_transition", {}).get("basis_evidence_ids", []))
        ),
        "artifact_path_chars": float(
            sum(len(str(record.get("artifact_path", ""))) for record in evidence)
        ),
        "evidence_id_chars": float(
            sum(len(str(record.get("id", ""))) for record in evidence)
        ),
        "dependency_id_chars": float(sum(len(str(value)) for value in dependencies)),
        "scope_field_count": float(
            sum(len(record.get("scope", {})) for record in evidence)
        ),
        "provenance_field_count": float(
            sum(len(record.get("provenance", {})) for record in evidence)
        ),
        "changed_axis_count": float(len(_changed_axes(item))),
    }


def _dependency_shape(evidence: list[dict[str, Any]]) -> tuple[int, bool]:
    evidence_ids = {str(record.get("id")) for record in evidence}
    graph = {
        str(record.get("id")): [
            str(value)
            for value in record.get("dependencies", [])
            if str(value) in evidence_ids
        ]
        for record in evidence
    }
    visiting: set[str] = set()
    memo: dict[str, int] = {}
    cycle = False

    def depth(node: str) -> int:
        nonlocal cycle
        if node in memo:
            return memo[node]
        if node in visiting:
            cycle = True
            return 0
        visiting.add(node)
        value = 1 + max((depth(child) for child in graph.get(node, [])), default=0)
        visiting.remove(node)
        memo[node] = value
        return value

    return max((depth(node) for node in graph), default=0), cycle


def _shallow_features(item: dict[str, Any]) -> dict[str, float]:
    features = _metadata_features(item)
    evidence = list(item.get("evidence", []))
    evidence_ids = {str(record.get("id")) for record in evidence}
    referenced = {
        str(value) for record in evidence for value in record.get("dependencies", [])
    }
    basis = {
        str(value)
        for value in item.get("requested_transition", {}).get("basis_evidence_ids", [])
    }
    maximum_depth, has_cycle = _dependency_shape(evidence)

    for evidence_type in EVIDENCE_TYPES:
        features[f"type_{evidence_type.lower()}"] = float(
            sum(record.get("type") == evidence_type for record in evidence)
        )
    for key in SCOPE_KEYS:
        features[f"scope_has_{key}"] = float(
            sum(key in record.get("scope", {}) for record in evidence)
        )
    changed_axes = _changed_axes(item)
    for axis in STATE_ORDER:
        features[f"changes_{axis}"] = float(axis in changed_axes)

    features.update(
        {
            "basis_present_count": float(len(basis & evidence_ids)),
            "basis_missing_count": float(len(basis - evidence_ids)),
            "referenced_dependency_present_count": float(len(referenced & evidence_ids)),
            "referenced_dependency_missing_count": float(len(referenced - evidence_ids)),
            "dependency_max_depth": float(maximum_depth),
            "dependency_cycle_present": float(has_cycle),
            "tool_exit_present_count": float(
                sum(record.get("tool_exit") is not None for record in evidence)
            ),
            "verifier_result_present_count": float(
                sum(record.get("verifier_result") is not None for record in evidence)
            ),
        }
    )
    return features


def extract_features(item: dict[str, Any], tier: str) -> dict[str, float]:
    """Extract one fixed, policy-blind feature vector."""

    if tier == "metadata_only":
        return _metadata_features(item)
    if tier == "shallow_structure":
        return _shallow_features(item)
    raise ValueError(f"unknown shortcut tier: {tier}")
