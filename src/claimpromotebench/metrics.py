"""Metrics for admissibility, paired behavior, attribution, and gate effects."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median
from typing import Any

from .statistics import pair_cluster_bootstrap_many, percentile


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


def _scored_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("parse_status") != "FORMAT_ERROR"
        and record.get("prediction") is not None
        and record["prediction"].get("p_admissible") is not None
    ]


def _score_groups(records: list[dict[str, Any]]) -> list[tuple[float, list[dict[str, Any]]]]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[float(record["prediction"]["p_admissible"])].append(record)
    return sorted(grouped.items(), key=lambda item: item[0], reverse=True)


def _average_precision(records: list[dict[str, Any]]) -> float | None:
    scored = _scored_records(records)
    positives = sum(record["gold"]["action"] == "ALLOW" for record in scored)
    if positives == 0:
        return None

    true_positive = 0
    false_positive = 0
    previous_recall = 0.0
    area = 0.0
    for _threshold, tied_records in _score_groups(scored):
        true_positive += sum(record["gold"]["action"] == "ALLOW" for record in tied_records)
        false_positive += sum(record["gold"]["action"] != "ALLOW" for record in tied_records)
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / positives
        area += (recall - previous_recall) * precision
        previous_recall = recall
    return area


def _precision_recall(records: list[dict[str, Any]], total: int) -> dict[str, Any]:
    scored = _scored_records(records)
    positives = sum(record["gold"]["action"] == "ALLOW" for record in scored)
    points: list[dict[str, float | int | None]] = []
    true_positive = 0
    false_positive = 0
    previous_recall = 0.0
    area = 0.0

    for threshold, tied_records in _score_groups(scored):
        true_positive += sum(record["gold"]["action"] == "ALLOW" for record in tied_records)
        false_positive += sum(record["gold"]["action"] != "ALLOW" for record in tied_records)
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / positives if positives else None
        if recall is not None:
            area += (recall - previous_recall) * precision
            previous_recall = recall
        points.append(
            {
                "threshold": threshold,
                "selected": true_positive + false_positive,
                "true_positive": true_positive,
                "false_positive": false_positive,
                "precision": precision,
                "recall": recall,
            }
        )

    prevalence = positives / len(scored) if scored else None
    average_precision = area if positives else None
    lift = (
        average_precision / prevalence
        if average_precision is not None and prevalence not in {None, 0.0}
        else None
    )
    return {
        "points": points,
        "auprc_stepwise": _defined(average_precision),
        "positive_prevalence": _defined(prevalence),
        "lift_over_prevalence": _defined(lift),
        "score_coverage": len(scored) / total if total else 0.0,
        "unique_thresholds": len(points),
    }


def _risk_coverage(records: list[dict[str, Any]], total: int) -> dict[str, Any]:
    scored = _scored_records(records)
    if not scored:
        return {"points": [], "aurc_trapezoid": None, "decision_coverage": 0.0}
    thresholds = sorted(
        {float(record["prediction"]["p_admissible"]) for record in scored}, reverse=True
    )
    points: list[dict[str, float]] = []
    for threshold in thresholds:
        selected = [
            record for record in scored if float(record["prediction"]["p_admissible"]) >= threshold
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
    return {
        "points": points,
        "aurc_trapezoid": area,
        "decision_coverage": len(scored) / total,
    }


def _paired_score_ranking(records: list[dict[str, Any]]) -> dict[str, Any]:
    pair_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        pair_records[str(record["pair_id"])].append(record)

    wins = 0
    ties = 0
    losses = 0
    margins: list[float] = []
    for pair in pair_records.values():
        scored = _scored_records(pair)
        if len(scored) != 2:
            continue
        valid = [record for record in scored if record["gold"]["action"] == "ALLOW"]
        invalid = [record for record in scored if record["gold"]["action"] != "ALLOW"]
        if len(valid) != 1 or len(invalid) != 1:
            raise ValueError("every pair must contain one valid and one invalid transition")
        margin = float(valid[0]["prediction"]["p_admissible"]) - float(
            invalid[0]["prediction"]["p_admissible"]
        )
        margins.append(margin)
        if margin > 0:
            wins += 1
        elif margin < 0:
            losses += 1
        else:
            ties += 1

    compared = len(margins)
    return {
        "compared_pairs": compared,
        "pair_coverage": compared / len(pair_records) if pair_records else 0.0,
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "strict_accuracy": _defined(_safe_rate(wins, compared)),
        "tie_adjusted_accuracy": _defined((wins + 0.5 * ties) / compared if compared else None),
        "score_margin_mean": _defined(mean(margins) if margins else None),
        "score_margin_median": _defined(median(margins) if margins else None),
    }


def _false_promotion_rate(records: list[dict[str, Any]]) -> float | None:
    invalid = [
        record
        for record in records
        if record["gold"]["action"] != "ALLOW" and record.get("parse_status") != "FORMAT_ERROR"
    ]
    return _safe_rate(
        sum(record["prediction"]["action"] == "ALLOW" for record in invalid), len(invalid)
    )


def _family_breakdown(records: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("family") is not None:
            families[str(record["family"])].append(record)

    breakdown: dict[str, Any] = {}
    for family, family_records in sorted(families.items()):
        parsed = [
            record for record in family_records if record.get("parse_status") != "FORMAT_ERROR"
        ]
        valid = [record for record in parsed if record["gold"]["action"] == "ALLOW"]
        breakdown[family] = {
            "instances": len(family_records),
            "decision_coverage": len(parsed) / len(family_records),
            "false_promotion_rate": _defined(_false_promotion_rate(family_records)),
            "valid_promotion_recall": _defined(
                _safe_rate(
                    sum(record["prediction"]["action"] == "ALLOW" for record in valid),
                    len(valid),
                )
            ),
            "precision_recall": _precision_recall(family_records, len(family_records)),
            "paired_score_ranking": _paired_score_ranking(family_records),
        }
    return breakdown


def evaluate_records(
    records: list[dict[str, Any]], *, bootstrap_samples: int = 10_000
) -> dict[str, Any]:
    """Evaluate joined records containing id, pair_id, gold, and prediction."""

    if not records:
        raise ValueError("evaluation requires at least one record")
    parsed_records = [record for record in records if record.get("parse_status") != "FORMAT_ERROR"]
    valid = [record for record in parsed_records if record["gold"]["action"] == "ALLOW"]
    promoted = [record for record in parsed_records if record["prediction"]["action"] == "ALLOW"]
    false_promotions = sum(record["gold"]["action"] != "ALLOW" for record in promoted)

    pair_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        pair_records[str(record["pair_id"])].append(record)
    pair_exact: list[bool] = []
    pair_flip: list[bool] = []
    complete_parsed_pairs = 0
    for pair in pair_records.values():
        if len(pair) != 2:
            raise ValueError("every evaluated pair must contain exactly two members")
        if any(member.get("parse_status") == "FORMAT_ERROR" for member in pair):
            continue
        complete_parsed_pairs += 1
        pair_exact.append(
            all(member["prediction"]["action"] == member["gold"]["action"] for member in pair)
        )
        invalid_member = next(member for member in pair if member["gold"]["action"] != "ALLOW")
        valid_member = next(member for member in pair if member["gold"]["action"] == "ALLOW")
        pair_flip.append(
            invalid_member["prediction"]["action"] in {"HOLD", "DEMOTE", "ESCALATE"}
            and valid_member["prediction"]["action"] == "ALLOW"
        )

    brier_values: list[float] = []
    nll_values: list[float] = []
    epsilon = 1e-15
    reason_instance_f1: list[float] = []
    evidence_precision: list[float] = []
    evidence_recall: list[float] = []
    missing_exact: list[bool] = []
    probability_records: list[dict[str, Any]] = []
    for record in records:
        if record.get("parse_status") == "FORMAT_ERROR":
            reason_instance_f1.append(0.0)
            evidence_precision.append(0.0)
            evidence_recall.append(0.0)
            missing_exact.append(False)
            continue
        target = 1.0 if record["gold"]["action"] == "ALLOW" else 0.0
        probability = float(record["prediction"]["p_admissible"])
        probability_records.append(record)
        brier_values.append((probability - target) ** 2)
        clipped = min(1 - epsilon, max(epsilon, probability))
        nll_values.append(-(target * math.log(clipped) + (1 - target) * math.log(1 - clipped)))
        _, _, f1 = _set_f1(
            set(record["prediction"]["reason_codes"]), set(record["gold"]["reason_codes"])
        )
        reason_instance_f1.append(f1)
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
                sum(record["prediction"]["action"] != "ALLOW" for record in valid), len(valid)
            )
        ),
        "literal_hold_rate_on_valid": _defined(
            _safe_rate(
                sum(record["prediction"]["action"] == "HOLD" for record in valid), len(valid)
            )
        ),
        "paired_transition_accuracy": _defined(mean(pair_exact) if pair_exact else None),
    }
    secondary = {
        "promotion_fdr": _defined(_safe_rate(false_promotions, len(promoted))),
        "promotion_coverage": len(promoted) / len(records),
        "decision_coverage": len(parsed_records) / len(records),
        "complete_pair_coverage": complete_parsed_pairs / len(pair_records),
        "counterfactual_flip_accuracy": _defined(mean(pair_flip) if pair_flip else None),
        "brier": _defined(mean(brier_values) if brier_values else None),
        "nll": _defined(mean(nll_values) if nll_values else None),
        "calibration_coverage": len(probability_records) / len(records),
        "precision_recall": _precision_recall(probability_records, len(records)),
        "risk_coverage": _risk_coverage(probability_records, len(records)),
        "paired_score_ranking": _paired_score_ranking(records),
        "reason_code_instance_set_f1": mean(reason_instance_f1),
        "evidence_id_macro_precision": mean(evidence_precision),
        "evidence_id_macro_recall": mean(evidence_recall),
        "missing_evidence_exact_match": mean(missing_exact),
    }
    parsed_pair_records = {
        pair_id: [record for record in pair if record.get("parse_status") != "FORMAT_ERROR"]
        for pair_id, pair in pair_records.items()
    }
    parsed_pair_records = {pair_id: pair for pair_id, pair in parsed_pair_records.items() if pair}
    bootstrap = (
        pair_cluster_bootstrap_many(
            parsed_pair_records,
            {
                "false_promotion_rate": _false_promotion_rate,
                "auprc_stepwise": _average_precision,
            },
            samples=bootstrap_samples,
        )
        if parsed_pair_records
        else None
    )
    primary["false_promotion_rate"]["ci95_pair_bootstrap"] = (
        bootstrap["false_promotion_rate"] if bootstrap else None
    )
    secondary["precision_recall"]["auprc_stepwise"]["ci95_pair_bootstrap"] = (
        bootstrap["auprc_stepwise"] if bootstrap else None
    )
    format_error_count = len(records) - len(parsed_records)
    invalid_total = sum(record["gold"]["action"] != "ALLOW" for record in records)
    invalid_format_errors = sum(
        record["gold"]["action"] != "ALLOW" and record.get("parse_status") == "FORMAT_ERROR"
        for record in records
    )
    primary["false_promotion_rate"]["worst_case_format_error_sensitivity"] = _defined(
        _safe_rate(false_promotions + invalid_format_errors, invalid_total)
    )
    return {
        "instances": len(records),
        "pairs": len(pair_records),
        "format_error_count": format_error_count,
        "primary": primary,
        "secondary": secondary,
        "by_family": _family_breakdown(records),
    }


def evaluate_gate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate raw intent separately from post-gate system behavior."""

    parsed = [record for record in records if record.get("parse_status") != "FORMAT_ERROR"]
    invalid = [record for record in parsed if record["gold"]["action"] != "ALLOW"]
    valid = [record for record in parsed if record["gold"]["action"] == "ALLOW"]
    invalid_raw_allow = [
        record for record in invalid if record["raw_decision"]["action"] == "ALLOW"
    ]
    valid_raw_allow = [record for record in valid if record["raw_decision"]["action"] == "ALLOW"]
    return {
        "decision_coverage": len(parsed) / len(records) if records else 0.0,
        "format_error_count": len(records) - len(parsed),
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
