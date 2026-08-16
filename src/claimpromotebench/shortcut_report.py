"""Reports and metrics for cross-fitted shortcut audits."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .metrics import evaluate_records
from .shortcut_features import EXCLUDED_FIELDS, TIERS, extract_features
from .shortcut_model import (
    Record,
    cross_fitted_predictions,
    enriched_records,
    join_items,
    pair_records,
)


def _member(pair: list[Record], allow: bool) -> Record:
    return next(
        record for record in pair if (record["gold"]["action"] == "ALLOW") is allow
    )


def _pair_difference_report(joined: list[Record], tier: str) -> dict[str, Any]:
    pairs = pair_records(enriched_records(joined, tier))
    feature_names = sorted(next(iter(pairs.values()))[0]["features"])
    differences: dict[str, dict[str, float | int]] = {}
    exposed_pairs: set[str] = set()

    for name in feature_names:
        valid_higher = 0
        invalid_higher = 0
        tied = 0
        absolute_deltas: list[float] = []
        for pair_id, pair in pairs.items():
            valid = _member(pair, True)
            invalid = _member(pair, False)
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


def _univariate_cross_fit(joined: list[Record], tier: str) -> list[dict[str, Any]]:
    pairs = pair_records(enriched_records(joined, tier))
    feature_names = sorted(next(iter(pairs.values()))[0]["features"])
    reports: list[dict[str, Any]] = []

    for name in feature_names:
        wins = 0
        ties = 0
        losses = 0
        for held_pair_id, held_pair in pairs.items():
            training_deltas = [
                float(_member(pair, True)["features"][name])
                - float(_member(pair, False)["features"][name])
                for pair_id, pair in pairs.items()
                if pair_id != held_pair_id
            ]
            orientation_value = mean(training_deltas)
            orientation = 1 if orientation_value > 0 else -1 if orientation_value < 0 else 0
            margin = orientation * (
                float(_member(held_pair, True)["features"][name])
                - float(_member(held_pair, False)["features"][name])
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
    inputs: list[Record],
    gold: list[Record],
    *,
    bootstrap_samples: int = 0,
) -> dict[str, Any]:
    """Audit two policy-blind tiers with leave-one-pair-out scoring."""

    if bootstrap_samples < 0:
        raise ValueError("bootstrap samples must be non-negative")
    joined = join_items(inputs, gold)
    pairs = pair_records(joined)
    tier_reports: dict[str, Any] = {}

    for tier in TIERS:
        predictions = cross_fitted_predictions(joined, tier)
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
            "excluded_fields": sorted(EXCLUDED_FIELDS),
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
