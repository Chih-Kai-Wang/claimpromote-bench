"""Cross-fitted audits for non-semantic and shallow structural shortcuts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from .dataset import load_jsonl, verify_manifest
from .errors import ClaimPromoteBenchError
from .hashing import canonical_json
from .metrics import evaluate_records
from .state import STATE_ORDER

TIERS = ("metadata_only", "shallow_structure")

_EXCLUDED_FIELDS = {
    "_artifact_hash",
    "family",
    "gold",
    "id",
    "pair_id",
    "split",
}
_EVIDENCE_TYPES = (
    "COMPUTATION",
    "CONTRADICTION",
    "DEPENDENCY",
    "FORMAL_CERTIFICATE",
    "REVIEW",
)
_SCOPE_KEYS = (
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
    return {key: value for key, value in item.items() if key not in _EXCLUDED_FIELDS}


def _changed_axes(item: dict[str, Any]) -> tuple[str, ...]:
    current = item["current_state"]
    target = item["requested_transition"]["target_state"]
    return tuple(axis for axis in STATE_ORDER if current[axis] != target[axis])


def _metadata_features(item: dict[str, Any]) -> dict[str, float]:
    evidence = list(item.get("evidence", []))
    dependencies = [
        dependency
        for record in evidence
        for dependency in record.get("dependencies", [])
    ]
    view = _model_view(item)
    return {
        "serialized_chars": float(len(canonical_json(view))),
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

    maximum = max((depth(node) for node in graph), default=0)
    return maximum, cycle


def _shallow_features(item: dict[str, Any]) -> dict[str, float]:
    features = _metadata_features(item)
    evidence = list(item.get("evidence", []))
    evidence_ids = {str(record.get("id")) for record in evidence}
    referenced = {
        str(value)
        for record in evidence
        for value in record.get("dependencies", [])
    }
    basis = {
        str(value)
        for value in item.get("requested_transition", {}).get("basis_evidence_ids", [])
    }
    maximum_depth, has_cycle = _dependency_shape(evidence)

    for evidence_type in _EVIDENCE_TYPES:
        features[f"type_{evidence_type.lower()}"] = float(
            sum(record.get("type") == evidence_type for record in evidence)
        )
    for key in _SCOPE_KEYS:
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
    """Extract a fixed, policy-blind feature vector for one public input."""

    if tier == "metadata_only":
        return _metadata_features(item)
    if tier == "shallow_structure":
        return _shallow_features(item)
    raise ValueError(f"unknown shortcut tier: {tier}")


def _joined_items(
    inputs: list[dict[str, Any]],
    gold: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    input_by_id = {str(record["id"]): record for record in inputs}
    gold_by_id = {str(record["id"]): record for record in gold}
    if set(input_by_id) != set(gold_by_id):
        raise ValueError("shortcut audit requires identical input and gold IDs")

    joined = [
        {
            "id": record_id,
            "pair_id": str(gold_by_id[record_id]["pair_id"]),
            "family": str(gold_by_id[record_id].get("family", "UNKNOWN")),
            "item": input_by_id[record_id],
            "gold": gold_by_id[record_id]["decision"],
        }
        for record_id in sorted(input_by_id)
    ]
    pair_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in joined:
        pair_records[record["pair_id"]].append(record)
    if len(pair_records) < 2:
        raise ValueError("shortcut audit requires at least two controlled pairs")
    for pair in pair_records.values():
        if len(pair) != 2:
            raise ValueError("every shortcut-audit pair must contain exactly two members")
        positives = sum(record["gold"]["action"] == "ALLOW" for record in pair)
        if positives != 1:
            raise ValueError("every shortcut-audit pair must contain one gold ALLOW")
    return joined


def _pair_records(
    joined: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in joined:
        pairs[str(record["pair_id"])].append(record)
    return dict(pairs)


def _standardization(
    records: list[dict[str, Any]],
    feature_names: list[str],
) -> tuple[dict[str, float], dict[str, float]]:
    centers: dict[str, float] = {}
    scales: dict[str, float] = {}
    for name in feature_names:
        values = [float(record["features"][name]) for record in records]
        centers[name] = mean(values)
        deviation = pstdev(values)
        scales[name] = deviation if deviation > 0 else 1.0
    return centers, scales


def _standardized(
    features: dict[str, float],
    names: list[str],
    centers: dict[str, float],
    scales: dict[str, float],
) -> list[float]:
    return [(features[name] - centers[name]) / scales[name] for name in names]


def _sigmoid(value: float) -> float:
    clipped = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + math.exp(-clipped))


def _cross_fitted_predictions(
    joined: list[dict[str, Any]],
    tier: str,
) -> list[dict[str, Any]]:
    enriched = [
        {**record, "features": extract_features(record["item"], tier)}
        for record in joined
    ]
    pairs = _pair_records(enriched)
    feature_names = sorted(enriched[0]["features"])
    if any(sorted(record["features"]) != feature_names for record in enriched):
        raise ValueError("shortcut feature vectors are inconsistent")

    predictions: dict[str, dict[str, Any]] = {}
    for held_pair_id, held_pair in sorted(pairs.items()):
        training = [
            record
            for pair_id, pair in pairs.items()
            if pair_id != held_pair_id
            for record in pair
        ]
        centers, scales = _standardization(training, feature_names)

        pair_deltas: list[list[float]] = []
        for pair_id, pair in pairs.items():
            if pair_id == held_pair_id:
                continue
            valid = next(record for record in pair if record["gold"]["action"] == "ALLOW")
            invalid = next(record for record in pair if record["gold"]["action"] != "ALLOW")
            valid_vector = _standardized(valid["features"], feature_names, centers, scales)
            invalid_vector = _standardized(
                invalid["features"], feature_names, centers, scales
            )
            pair_deltas.append(
                [
                    left - right
                    for left, right in zip(valid_vector, invalid_vector, strict=True)
                ]
            )

        weights = [
            mean(delta[index] for delta in pair_deltas)
            for index in range(len(feature_names))
        ]
        norm = math.sqrt(sum(weight * weight for weight in weights))
        if norm > 0:
            weights = [weight / norm for weight in weights]

        training_scores: list[float] = []
        valid_scores: list[float] = []
        invalid_scores: list[float] = []
        for record in training:
            vector = _standardized(record["features"], feature_names, centers, scales)
            score = sum(
                weight * value for weight, value in zip(weights, vector, strict=True)
            )
            training_scores.append(score)
            if record["gold"]["action"] == "ALLOW":
                valid_scores.append(score)
            else:
                invalid_scores.append(score)
        midpoint = (mean(valid_scores) + mean(invalid_scores)) / 2
        score_scale = pstdev(training_scores)
        if score_scale == 0:
            score_scale = 1.0

        for record in held_pair:
            vector = _standardized(record["features"], feature_names, centers, scales)
            score = sum(
                weight * value for weight, value in zip(weights, vector, strict=True)
            )
            probability = _sigmoid((score - midpoint) / score_scale)
            action = "ALLOW" if probability > 0.5 else "HOLD"
            predictions[str(record["id"])] = {
                "action": action,
                "proposed_state": (
                    record["item"]["requested_transition"]["target_state"]
                    if action == "ALLOW"
                    else record["item"]["current_state"]
                ),
                "p_admissible": probability,
                "used_evidence_ids": [],
                "reason_codes": [f"SHORTCUT_{tier.upper()}"],
                "missing_evidence_ids": [],
            }

    return [
        {
            "id": record["id"],
            "pair_id": record["pair_id"],
            "family": record["family"],
            "gold": record["gold"],
            "prediction": predictions[str(record["id"])],
        }
        for record in joined
    ]


def _pair_difference_report(
    joined: list[dict[str, Any]],
    tier: str,
) -> dict[str, Any]:
    enriched = [
        {**record, "features": extract_features(record["item"], tier)}
        for record in joined
    ]
    pairs = _pair_records(enriched)
    feature_names = sorted(enriched[0]["features"])
    differences: dict[str, dict[str, float | int]] = {}
    exposed_pairs: set[str] = set()

    for name in feature_names:
        valid_higher = 0
        invalid_higher = 0
        tied = 0
        absolute_deltas: list[float] = []
        for pair_id, pair in pairs.items():
            valid = next(record for record in pair if record["gold"]["action"] == "ALLOW")
            invalid = next(record for record in pair if record["gold"]["action"] != "ALLOW")
            delta = float(valid["features"][name]) - float(invalid["features"][name])
            absolute_deltas.append(abs(delta))
            if delta > 0:
                valid_higher += 1
                exposed_pairs.add(pair_id)
            elif delta < 0:
                invalid_higher += 1
                exposed_pairs.add(pair_id)
            else:
                tied += 1
        differences[name] = {
            "pairs_changed": valid_higher + invalid_higher,
            "valid_higher": valid_higher,
            "invalid_higher": invalid_higher,
            "tied": tied,
            "mean_absolute_delta": mean(absolute_deltas),
        }
    return {
        "pair_exposure_rate": len(exposed_pairs) / len(pairs),
        "pairs_exposed": len(exposed_pairs),
        "features": differences,
    }


def _univariate_cross_fit(
    joined: list[dict[str, Any]],
    tier: str,
) -> list[dict[str, Any]]:
    enriched = [
        {**record, "features": extract_features(record["item"], tier)}
        for record in joined
    ]
    pairs = _pair_records(enriched)
    feature_names = sorted(enriched[0]["features"])
    reports: list[dict[str, Any]] = []

    for name in feature_names:
        wins = 0
        ties = 0
        losses = 0
        for held_pair_id, held_pair in pairs.items():
            training_deltas: list[float] = []
            for pair_id, pair in pairs.items():
                if pair_id == held_pair_id:
                    continue
                valid = next(
                    record for record in pair if record["gold"]["action"] == "ALLOW"
                )
                invalid = next(
                    record for record in pair if record["gold"]["action"] != "ALLOW"
                )
                training_deltas.append(
                    float(valid["features"][name])
                    - float(invalid["features"][name])
                )
            orientation_value = mean(training_deltas)
            orientation = 1 if orientation_value > 0 else -1 if orientation_value < 0 else 0
            valid = next(
                record for record in held_pair if record["gold"]["action"] == "ALLOW"
            )
            invalid = next(
                record for record in held_pair if record["gold"]["action"] != "ALLOW"
            )
            margin = orientation * (
                float(valid["features"][name])
                - float(invalid["features"][name])
            )
            if margin > 0:
                wins += 1
            elif margin < 0:
                losses += 1
            else:
                ties += 1
        total = len(pairs)
        reports.append(
            {
                "feature": name,
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "strict_accuracy": wins / total,
                "tie_adjusted_accuracy": (wins + 0.5 * ties) / total,
            }
        )

    return sorted(
        reports,
        key=lambda report: (
            -float(report["tie_adjusted_accuracy"]),
            -float(report["strict_accuracy"]),
            str(report["feature"]),
        ),
    )


def audit_shortcuts(
    inputs: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    *,
    bootstrap_samples: int = 0,
) -> dict[str, Any]:
    """Audit two policy-blind feature tiers with leave-one-pair-out scoring."""

    if bootstrap_samples < 0:
        raise ValueError("bootstrap samples must be non-negative")
    joined = _joined_items(inputs, gold)
    pairs = _pair_records(joined)
    tier_reports: dict[str, Any] = {}

    for tier in TIERS:
        predictions = _cross_fitted_predictions(joined, tier)
        tier_reports[tier] = {
            "feature_names": sorted(extract_features(joined[0]["item"], tier)),
            "pair_differences": _pair_difference_report(joined, tier),
            "univariate_cross_fit": _univariate_cross_fit(joined, tier),
            "evaluation": evaluate_records(
                predictions,
                bootstrap_samples=bootstrap_samples,
            ),
        }

    return {
        "protocol": {
            "positive_class": "gold action ALLOW",
            "cross_fit": "leave_one_controlled_pair_out",
            "excluded_fields": sorted(_EXCLUDED_FIELDS),
            "decision_rule": "ALLOW only when cross-fitted p_admissible > 0.5",
            "metadata_only": "lengths and counts; no string contents or policy comparisons",
            "shallow_structure": (
                "metadata plus evidence types, field presence, and graph shape; "
                "no hash, timestamp, scope, provenance, or policy-value comparison"
            ),
        },
        "instances": len(joined),
        "pairs": len(pairs),
        "tiers": tier_reports,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    tiers: dict[str, Any] = {}
    for tier, tier_report in report["tiers"].items():
        evaluation = tier_report["evaluation"]
        tiers[tier] = {
            "auprc_stepwise": evaluation["secondary"]["precision_recall"][
                "auprc_stepwise"
            ]["value"],
            "paired_score_strict_accuracy": evaluation["secondary"][
                "paired_score_ranking"
            ]["strict_accuracy"]["value"],
            "pair_exposure_rate": tier_report["pair_differences"][
                "pair_exposure_rate"
            ],
        }
    return {
        "instances": report["instances"],
        "pairs": report["pairs"],
        "tiers": tiers,
    }


def main(argv: list[str] | None = None) -> int:
    """Run a deterministic shortcut audit over one complete dataset."""

    parser = argparse.ArgumentParser(
        prog="cpb-audit-shortcuts",
        description=__doc__,
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/alpha"),
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        verify_manifest(args.dataset)
        report = audit_shortcuts(
            load_jsonl(args.dataset / "inputs.jsonl"),
            load_jsonl(args.dataset / "gold.jsonl"),
            bootstrap_samples=args.bootstrap_samples,
        )
        if args.out:
            _write_json(args.out, report)
            result = {"out": str(args.out), **_summary(report)}
        else:
            result = report
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
