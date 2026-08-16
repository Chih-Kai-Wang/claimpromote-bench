"""Pair-aware uncertainty and exact paired comparisons."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import Any


def percentile(values: Sequence[float], probability: float) -> float:
    """Linear-interpolated percentile with deterministic edge behavior."""

    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _bootstrap_summary(estimates: list[float], seed: int) -> dict[str, float | int | None]:
    if not estimates:
        return {"low": None, "high": None, "samples_defined": 0, "seed": seed}
    return {
        "low": percentile(estimates, 0.025),
        "high": percentile(estimates, 0.975),
        "samples_defined": len(estimates),
        "seed": seed,
    }


def pair_cluster_bootstrap_many(
    pair_records: dict[str, list[dict[str, Any]]],
    statistics: dict[str, Callable[[list[dict[str, Any]]], float | None]],
    *,
    samples: int = 10_000,
    seed: int = 20_260_813,
) -> dict[str, dict[str, float | int | None]]:
    """Bootstrap statistics together; zero samples returns empty interval metadata."""

    pair_ids = sorted(pair_records)
    if not pair_ids:
        raise ValueError("bootstrap requires at least one pair")
    if not statistics:
        raise ValueError("bootstrap requires at least one statistic")
    if samples < 0:
        raise ValueError("bootstrap samples must be non-negative")

    rng = random.Random(seed)
    estimates: dict[str, list[float]] = {name: [] for name in statistics}
    for _ in range(samples):
        sample: list[dict[str, Any]] = []
        for _pair_index in pair_ids:
            chosen = rng.choice(pair_ids)
            sample.extend(pair_records[chosen])
        for name, statistic in statistics.items():
            value = statistic(sample)
            if value is not None and math.isfinite(value):
                estimates[name].append(value)
    return {name: _bootstrap_summary(values, seed) for name, values in estimates.items()}


def pair_cluster_bootstrap(
    pair_records: dict[str, list[dict[str, Any]]],
    statistic: Callable[[list[dict[str, Any]]], float | None],
    *,
    samples: int = 10_000,
    seed: int = 20_260_813,
) -> dict[str, float | int | None]:
    """Bootstrap pairs, carrying both pair members into each resample."""

    return pair_cluster_bootstrap_many(
        pair_records,
        {"statistic": statistic},
        samples=samples,
        seed=seed,
    )["statistic"]


def mcnemar_exact(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> dict[str, Any]:
    """Two-sided exact McNemar test using the conditional binomial distribution."""

    if len(correct_a) != len(correct_b):
        raise ValueError("paired correctness vectors must have equal length")
    b = sum(a and not other for a, other in zip(correct_a, correct_b, strict=True))
    c = sum((not a) and other for a, other in zip(correct_a, correct_b, strict=True))
    discordant = b + c
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, index) for index in range(min(b, c) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {"a_only_correct": b, "b_only_correct": c, "discordant": discordant, "p": p_value}


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Return Holm step-down adjusted p-values in original order."""

    count = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda pair: pair[1])
    adjusted = [0.0] * count
    running = 0.0
    for rank, (index, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * value))
        adjusted[index] = running
    return adjusted
