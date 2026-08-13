"""Metrics for admissibility, paired behavior, attribution, and gate effects."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median
from typing import Any

from .statistics import pair_cluster_bootstrap, percentile


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _defined(value: float | None) -> dict[str, bool | float | None]:
    return {"value": value, "defined": value is not None}


def _set_f1(predicted: set[str], expected: set[str]) -> tuple[float, float, float]:
    true_positive = len(predicted & expected)
    precision = _safe_rate(true_positive, len(predicted))
    recall = _safe_rate(true_positive, len(expected))
    precision_value = (1.0 if not expected else 0.0) if precision is None else precision
    recall_value = (1.0 if not predicted else 0.0) if recall is None else recall
    denominator = precision_value + recall_value
    f1 = 0.0 if denominator == 0 else 2 * precision_value * recall_value / denominator
    return precision_value, recall_value, f1


def _risk_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    thresholds = sorted(
        {float(record["prediction"]["p_admissible"]) for record in records}, reverse=True
    )
    points: list[dict[str, float]] = []
    total = len(records)
    for threshold in thresholds:
        selected = [
            record for record in records if float(record["prediction"]["p_admissible"]) >= threshold
        ]
        errors = sum(record["gold"]["action"] != "ALLOW" for record in selected)
        points.append(
            {
                "threshold": threshold,
                "coverage": len(selected) / total,
                "risk": errors / len(selected),
            }
        )
    previous_coverage = 0.0
    previous_risk = 0.0
    area = 0.0
    for point in points:
        area += (point["coverage"] - previous_coverage) * (point["risk"] + previous_risk) / 2
        previous_coverage = point["coverage"]
        previous_risk = point["risk"]
    return {"points": points, "aurc": area}


def _false_promotion_rate(records: list[dict[str, Any]]) -> float | None:
    invalid = [record for record in records if record["gold"]["action"] != "ALLOW"]
    return _safe_rate(
        sum(record["prediction"]["action"] == "ALLOW" for record in invalid), len(invalid)
    )


def evaluate_records(
    records: list[dict[str, Any]], *, bootstrap_samples: int = 10_000
) -> dict[str, Any]:
    """Evaluate joined records containing id, pair_id, gold, and prediction."""

    if not records:
        raise ValueError("evaluation requires at least one record")
    valid = [record for record in records if record["gold"]["action"] == "ALLOW"]
    promoted = [record for record in records if record["prediction"]["action"] == "ALLOW"]
    false_promotions = sum(record["gold"]["action"] != "ALLOW" for record in promoted)

    pair_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        pair_records[str(record["pair_id"])].append(record)
    pair_exact: list[bool] = []
    pair_flip: list[bool] = []
    for pair in pair_records.values():
        if len(pair) != 2:
            raise ValueError("every evaluated pair must contain exactly two members")
        pair_exact.append(
            all(member["prediction"]["action"] == member["gold"]["action"] for member in pair)
        )
        invalid_member = next(member for member in pair if member["gold"]["action"] != "ALLOW")
        valid_member = next(member for member in pair if member["gold"]["action"] == "ALLOW")
        pair_flip.append(
            invalid_member["prediction"]["action"] != "ALLOW"
            and valid_member["prediction"]["action"] == "ALLOW"
        )

    brier_values: list[float] = []
    nll_values: list[float] = []
    epsilon = 1e-15
    reason_f1: list[float] = []
    evidence_precision: list[float] = []
    evidence_recall: list[float] = []
    missing_exact: list[bool] = []
    for record in records:
        target = 1.0 if record["gold"]["action"] == "ALLOW" else 0.0
        probability = float(record["prediction"]["p_admissible"])
        brier_values.append((probability - target) ** 2)
        clipped = min(1 - epsilon, max(epsilon, probability))
        nll_values.append(-(target * math.log(clipped) + (1 - target) * math.log(1 - clipped)))
        _, _, f1 = _set_f1(
            set(record["prediction"]["reason_codes"]), set(record["gold"]["reason_codes"])
        )
        reason_f1.append(f1)
        precision, recall, _ = _set_f1(
            set(record["prediction"]["used_evidence_ids"]),
            set(record["gold"]["used_evidence_ids"]),
        )
        evidence_precision.append(precision)
        evidence_recall.append(recall)
        missing_exact.append(
            set(record["prediction"]["missing_evidence_ids"])
            == set(record["gold"]["missing_evidence_ids"])
        )

    primary: dict[str, Any] = {
        "false_promotion_rate": _defined(_false_promotion_rate(records)),
        "valid_promotion_recall": _defined(
            _safe_rate(
                sum(record["prediction"]["action"] == "ALLOW" for record in valid), len(valid)
            )
        ),
        "false_hold_rate": _defined(
            _safe_rate(
                sum(record["prediction"]["action"] == "HOLD" for record in valid), len(valid)
            )
        ),
        "valid_non_allow_rate": _defined(
            _safe_rate(
                sum(record["prediction"]["action"] != "ALLOW" for record in valid), len(valid)
            )
        ),
        "paired_transition_accuracy": _defined(mean(pair_exact)),
    }
    secondary = {
        "promotion_fdr": _defined(_safe_rate(false_promotions, len(promoted))),
        "promotion_coverage": len(promoted) / len(records),
        "counterfactual_flip_accuracy": mean(pair_flip),
        "brier": mean(brier_values),
        "nll": mean(nll_values),
        "risk_coverage": _risk_coverage(records),
        "reason_code_macro_f1": mean(reason_f1),
        "evidence_id_macro_precision": mean(evidence_precision),
        "evidence_id_macro_recall": mean(evidence_recall),
        "missing_evidence_exact_match": mean(missing_exact),
    }
    primary["false_promotion_rate"]["ci95_pair_bootstrap"] = pair_cluster_bootstrap(
        pair_records, _false_promotion_rate, samples=bootstrap_samples
    )
    return {
        "instances": len(records),
        "pairs": len(pair_records),
        "primary": primary,
        "secondary": secondary,
    }


def evaluate_gate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate raw intent separately from post-gate system behavior."""

    invalid = [record for record in records if record["gold"]["action"] != "ALLOW"]
    valid = [record for record in records if record["gold"]["action"] == "ALLOW"]
    invalid_raw_allow = [
        record for record in invalid if record["raw_decision"]["action"] == "ALLOW"
    ]
    valid_raw_allow = [record for record in valid if record["raw_decision"]["action"] == "ALLOW"]
    return {
        "intent_false_promotion_rate": _defined(
            _safe_rate(
                sum(record["raw_decision"]["action"] == "ALLOW" for record in invalid), len(invalid)
            )
        ),
        "effective_false_promotion_rate": _defined(
            _safe_rate(
                sum(record["final_decision"]["action"] == "ALLOW" for record in invalid),
                len(invalid),
            )
        ),
        "gate_catch_rate": _defined(
            _safe_rate(
                sum(record["final_decision"]["action"] != "ALLOW" for record in invalid_raw_allow),
                len(invalid_raw_allow),
            )
        ),
        "false_block_rate": _defined(
            _safe_rate(
                sum(record["final_decision"]["action"] != "ALLOW" for record in valid_raw_allow),
                len(valid_raw_allow),
            )
        ),
    }


def operational_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize runtime fields without treating them as research quality."""

    latencies = [float(record["latency_ms"]) for record in records]
    tokens = [int(record["output_tokens"]) for record in records]
    verifier_calls = [int(record["verifier_calls"]) for record in records]
    return {
        "latency_ms_median": median(latencies),
        "latency_ms_p95": percentile(latencies, 0.95),
        "output_tokens_mean": mean(tokens),
        "output_tokens_sum": sum(tokens),
        "verifier_calls_mean": mean(verifier_calls),
        "verifier_calls_sum": sum(verifier_calls),
    }
