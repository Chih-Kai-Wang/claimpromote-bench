from __future__ import annotations

import math

from claimpromotebench.baselines import baseline_decision
from claimpromotebench.metrics import evaluate_gate_records, evaluate_records
from claimpromotebench.statistics import holm_adjust, mcnemar_exact, pair_cluster_bootstrap


def joined(inputs, gold, policy, evaluation_time, baseline):
    gold_by_id = {record["id"]: record for record in gold}
    return [
        {
            "id": item["id"],
            "pair_id": item["pair_id"],
            "gold": gold_by_id[item["id"]]["decision"],
            "prediction": baseline_decision(baseline, item, policy, evaluation_time),
        }
        for item in inputs
    ]


def test_always_allow_and_hold_expose_paired_failure(inputs, gold, policy, manifest) -> None:
    allow = evaluate_records(
        joined(inputs, gold, policy, manifest["evaluation_time"], "always_allow"),
        bootstrap_samples=100,
    )
    hold = evaluate_records(
        joined(inputs, gold, policy, manifest["evaluation_time"], "always_hold"),
        bootstrap_samples=100,
    )
    assert allow["primary"]["false_promotion_rate"]["value"] == 1.0
    assert allow["primary"]["valid_promotion_recall"]["value"] == 1.0
    assert allow["primary"]["paired_transition_accuracy"]["value"] == 0.0
    assert hold["secondary"]["promotion_fdr"] == {"value": None, "defined": False}
    assert hold["primary"]["valid_promotion_recall"]["value"] == 0.0
    assert not math.isnan(hold["secondary"]["brier"])


def test_oracle_is_internal_upper_bound(inputs, gold, policy, manifest) -> None:
    report = evaluate_records(
        joined(inputs, gold, policy, manifest["evaluation_time"], "policy_oracle"),
        bootstrap_samples=100,
    )
    assert report["primary"]["false_promotion_rate"]["value"] == 0.0
    assert report["primary"]["valid_promotion_recall"]["value"] == 1.0
    assert report["primary"]["paired_transition_accuracy"]["value"] == 1.0


def test_gate_metrics_separate_intent_and_effect() -> None:
    records = [
        {
            "gold": {"action": "HOLD"},
            "raw_decision": {"action": "ALLOW"},
            "final_decision": {"action": "HOLD"},
        },
        {
            "gold": {"action": "ALLOW"},
            "raw_decision": {"action": "ALLOW"},
            "final_decision": {"action": "ALLOW"},
        },
    ]
    report = evaluate_gate_records(records)
    assert report["intent_false_promotion_rate"]["value"] == 1.0
    assert report["effective_false_promotion_rate"]["value"] == 0.0
    assert report["gate_catch_rate"]["value"] == 1.0
    assert report["false_block_rate"]["value"] == 0.0


def test_bootstrap_and_exact_tests_are_reproducible() -> None:
    pairs = {
        "p1": [{"value": 0.0}, {"value": 1.0}],
        "p2": [{"value": 1.0}, {"value": 1.0}],
    }

    def statistic(records):
        return sum(record["value"] for record in records) / len(records)

    first = pair_cluster_bootstrap(pairs, statistic, samples=100, seed=7)
    second = pair_cluster_bootstrap(pairs, statistic, samples=100, seed=7)
    assert first == second
    assert mcnemar_exact([True, True, False], [False, True, True]) == {
        "a_only_correct": 1,
        "b_only_correct": 1,
        "discordant": 2,
        "p": 1.0,
    }
    assert holm_adjust([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
