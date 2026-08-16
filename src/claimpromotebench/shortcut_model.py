"""Leave-one-pair-out model used by shortcut audits."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, pstdev
from typing import Any

from .shortcut_features import extract_features

Record = dict[str, Any]
Pairs = dict[str, list[Record]]


def join_items(inputs: list[Record], gold: list[Record]) -> list[Record]:
    """Join public inputs to labels and validate controlled-pair structure."""

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
    pairs = pair_records(joined)
    if len(pairs) < 2:
        raise ValueError("shortcut audit requires at least two controlled pairs")
    for pair in pairs.values():
        if len(pair) != 2:
            raise ValueError("every shortcut-audit pair must contain exactly two members")
        positives = sum(record["gold"]["action"] == "ALLOW" for record in pair)
        if positives != 1:
            raise ValueError("every shortcut-audit pair must contain one gold ALLOW")
    return joined


def pair_records(records: list[Record]) -> Pairs:
    """Group records by controlled-pair ID."""

    pairs: defaultdict[str, list[Record]] = defaultdict(list)
    for record in records:
        pairs[str(record["pair_id"])].append(record)
    return dict(pairs)


def enriched_records(joined: list[Record], tier: str) -> list[Record]:
    """Attach one policy-blind feature vector to every joined record."""

    return [{**record, "features": extract_features(record["item"], tier)} for record in joined]


def _standardization(
    records: list[Record],
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


def _member(pair: list[Record], allow: bool) -> Record:
    return next(record for record in pair if (record["gold"]["action"] == "ALLOW") is allow)


def _weights(
    pairs: Pairs,
    held_pair_id: str,
    feature_names: list[str],
    centers: dict[str, float],
    scales: dict[str, float],
) -> list[float]:
    deltas: list[list[float]] = []
    for pair_id, pair in pairs.items():
        if pair_id == held_pair_id:
            continue
        valid = _standardized(
            _member(pair, True)["features"],
            feature_names,
            centers,
            scales,
        )
        invalid = _standardized(
            _member(pair, False)["features"],
            feature_names,
            centers,
            scales,
        )
        deltas.append([left - right for left, right in zip(valid, invalid, strict=True)])

    weights = [mean(delta[index] for delta in deltas) for index in range(len(feature_names))]
    norm = math.sqrt(sum(weight * weight for weight in weights))
    return [weight / norm for weight in weights] if norm > 0 else weights


def cross_fitted_predictions(joined: list[Record], tier: str) -> list[Record]:
    """Score each pair using a direction learned only from other pairs."""

    enriched = enriched_records(joined, tier)
    pairs = pair_records(enriched)
    feature_names = sorted(enriched[0]["features"])
    if any(sorted(record["features"]) != feature_names for record in enriched):
        raise ValueError("shortcut feature vectors are inconsistent")

    predictions: dict[str, Record] = {}
    for held_pair_id, held_pair in sorted(pairs.items()):
        training = [
            record for pair_id, pair in pairs.items() if pair_id != held_pair_id for record in pair
        ]
        centers, scales = _standardization(training, feature_names)
        weights = _weights(pairs, held_pair_id, feature_names, centers, scales)

        scores: list[tuple[Record, float]] = []
        for record in training:
            vector = _standardized(
                record["features"],
                feature_names,
                centers,
                scales,
            )
            score = sum(weight * value for weight, value in zip(weights, vector, strict=True))
            scores.append((record, score))

        valid_mean = mean(score for record, score in scores if record["gold"]["action"] == "ALLOW")
        invalid_mean = mean(
            score for record, score in scores if record["gold"]["action"] != "ALLOW"
        )
        midpoint = (valid_mean + invalid_mean) / 2
        score_scale = pstdev([score for _record, score in scores]) or 1.0

        for record in held_pair:
            vector = _standardized(
                record["features"],
                feature_names,
                centers,
                scales,
            )
            score = sum(weight * value for weight, value in zip(weights, vector, strict=True))
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
