#!/usr/bin/env python3
"""Exact pre-hidden power analysis for the fresh confirmatory family."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

Json = dict[str, Any]


def _binomial_tail(trials: int, probability: float, minimum: int) -> float:
    return sum(
        math.comb(trials, successes)
        * probability**successes
        * (1.0 - probability) ** (trials - successes)
        for successes in range(minimum, trials + 1)
    )


def _critical_successes(trials: int, raw_alpha: float) -> int | None:
    for successes in range((trials + 1) // 2, trials + 1):
        if _binomial_tail(trials, 0.5, successes) <= raw_alpha:
            return successes
    return None


def exact_clipped_pair_sign_power(
    pairs: int,
    nonzero_pair_rate: float,
    positive_sign_probability: float,
    raw_alpha: float,
) -> float:
    """Integrate the exact sign-test power over the empirical discordance rate."""

    power = 0.0
    for nonzero_pairs in range(1, pairs + 1):
        nonzero_probability = (
            math.comb(pairs, nonzero_pairs)
            * nonzero_pair_rate**nonzero_pairs
            * (1.0 - nonzero_pair_rate) ** (pairs - nonzero_pairs)
        )
        critical = _critical_successes(nonzero_pairs, raw_alpha)
        if critical is not None:
            power += nonzero_probability * _binomial_tail(
                nonzero_pairs,
                positive_sign_probability,
                critical,
            )
    return power


def analyze(assumptions: Json) -> Json:
    design = assumptions["design"]
    pairs = int(design["pairs"])
    family_size = int(design["confirmatory_family_size"])
    familywise_alpha = float(design["familywise_alpha"])
    delta = float(design["minimum_action_accuracy_effect"])
    raw_alpha = familywise_alpha / family_size
    results: list[Json] = []
    for comparison in assumptions["comparisons"]:
        histogram = {
            int(key): int(value)
            for key, value in comparison["old_pair_difference_histogram"].items()
        }
        if sum(histogram.values()) != pairs or any(abs(value) > 1 for value in histogram):
            raise ValueError("power assumptions must contain one clipped pair difference per pair")
        nonzero = sum(count for value, count in histogram.items() if value != 0)
        nonzero_rate = nonzero / pairs
        maximum_effect_with_clipped_magnitudes = nonzero / (2 * pairs)
        if delta > maximum_effect_with_clipped_magnitudes:
            raise ValueError("minimum effect is incompatible with the old discordance rate")
        positive_sign_probability = (1.0 + 2.0 * delta / nonzero_rate) / 2.0
        power = exact_clipped_pair_sign_power(
            pairs,
            nonzero_rate,
            positive_sign_probability,
            raw_alpha,
        )
        results.append(
            {
                "comparison_id": comparison["comparison_id"],
                "old_pair_difference_histogram": {
                    str(key): histogram[key] for key in sorted(histogram)
                },
                "old_action_accuracy_effect": sum(
                    value * count for value, count in histogram.items()
                )
                / (2 * pairs),
                "nonzero_pair_rate": nonzero_rate,
                "positive_sign_probability_at_minimum_effect": positive_sign_probability,
                "bonferroni_sufficient_power": power,
                "passes_0_80": power >= 0.8,
            }
        )
    minimum_power = min(float(row["bonferroni_sufficient_power"]) for row in results)
    return {
        "schema_version": "1.0.0",
        "status": "PRE_HIDDEN_POWER_GATE_PASS"
        if minimum_power >= 0.8
        else "PRE_HIDDEN_POWER_GATE_FAIL",
        "study_id": assumptions["study_id"],
        "source_assumptions": assumptions["source"],
        "design": {
            **design,
            "raw_bonferroni_alpha": raw_alpha,
            "test_model": (
                "Exact pair-sign power after clipping each old whole-pair correctness "
                "difference to magnitude one; the empirical nonzero-pair rate is retained, "
                "and signs are tilted to the registered minimum effect."
            ),
            "holm_interpretation": (
                "Bonferroni rejection at alpha/family_size is a conservative sufficient "
                "condition for rejection under the registered Holm procedure."
            ),
        },
        "comparisons": results,
        "minimum_power": minimum_power,
        "all_comparisons_pass_0_80": minimum_power >= 0.8,
        "uses_fresh_hidden_seed_or_outputs": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assumptions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assumptions = json.loads(args.assumptions.read_text(encoding="utf-8"))
    report = analyze(assumptions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {"status": report["status"], "minimum_power": report["minimum_power"]}, sort_keys=True
        )
    )
    return 0 if report["all_comparisons_pass_0_80"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
