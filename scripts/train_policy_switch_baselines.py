#!/usr/bin/env python3
"""Train policy-aware and profile-blind structured comparators before evaluation scoring."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sklearn import __version__ as sklearn_version
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]
RANDOM_STATE = 20260823
ESTIMATORS = 500


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-baselines: {message}")


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        fail(f"{path} contains a non-object row")
    return rows


def flatten_visible(item: Json, *, include_profile: bool) -> dict[str, str | int | bool]:
    current = item["current_state"]
    requested = item["requested_state"]
    evidence = item["evidence"][0]
    observed = evidence["observed"]
    features: dict[str, str | int | bool] = {
        "current.release_status": str(current["release_status"]),
        "current.accepted_build_level": int(current["accepted_build_level"]),
        "current.incident_review_required": bool(current["incident_review_required"]),
        "requested.release_status": str(requested["release_status"]),
        "requested.accepted_build_level": int(requested["accepted_build_level"]),
        "requested.incident_review_required": bool(requested["incident_review_required"]),
        "evidence.evidence_type": str(evidence["evidence_type"]),
        "observed.build_level_verified": int(observed["build_level_verified"]),
    }
    if include_profile:
        features["active_policy_profile"] = str(item["active_policy_profile"])
    for key, value in observed.items():
        if isinstance(value, bool):
            features[f"observed.{key}"] = value
    for code in (
        "SOURCE_REVISION_CONFLICT",
        "BUILD_PARAMETERS_CONFLICT",
        "VSA_POLICY_CONFLICT",
        "VERIFICATION_RESULT_CONFLICT",
    ):
        features[f"conflict.{code}"] = code in observed["authenticated_conflicts"]
    return features


def fit_predict(
    development_items: list[Json],
    development_actions: list[str],
    evaluation_items: list[Json],
    *,
    include_profile: bool,
) -> tuple[list[str], int, int]:
    vectorizer = DictVectorizer(sparse=False, sort=True)
    development_features = [
        flatten_visible(row["model_visible"], include_profile=include_profile)
        for row in development_items
    ]
    development_matrix = vectorizer.fit_transform(development_features)
    classifier = RandomForestClassifier(
        n_estimators=ESTIMATORS,
        random_state=RANDOM_STATE,
        class_weight="balanced_subsample",
        n_jobs=1,
    )
    classifier.fit(development_matrix, development_actions)
    training_predictions = classifier.predict(development_matrix).tolist()
    evaluation_matrix = vectorizer.transform(
        [
            flatten_visible(row["model_visible"], include_profile=include_profile)
            for row in evaluation_items
        ]
    )
    predictions = [str(value) for value in classifier.predict(evaluation_matrix).tolist()]
    training_correct = sum(
        predicted == expected
        for predicted, expected in zip(training_predictions, development_actions, strict=True)
    )
    return predictions, training_correct, len(vectorizer.feature_names_)


def write_predictions(path: Path, items: list[Json], actions: list[str]) -> None:
    rows = [
        {
            "item_id": item["id"],
            "pair_id": item["pair_id"],
            "predicted_action": action,
        }
        for item, action in zip(items, actions, strict=True)
    ]
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def train(dataset_root: Path, out_root: Path) -> Json:
    if out_root.exists():
        fail(f"output root already exists: {out_root}")
    out_root.mkdir(parents=True)
    development_items = load_jsonl(dataset_root / "development-items.jsonl")
    development_gold = load_jsonl(dataset_root / "development-gold.jsonl")
    evaluation_items = load_jsonl(dataset_root / "evaluation-items.jsonl")
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in development_gold}
    if set(gold_by_id) != {str(row["id"]) for row in development_items}:
        fail("development item and label IDs differ")
    development_actions = [gold_by_id[str(row["id"])] for row in development_items]

    comparators: Json = {}
    for comparator_id, include_profile in (
        ("policy_aware", True),
        ("profile_blind", False),
    ):
        predictions, training_correct, feature_count = fit_predict(
            development_items,
            development_actions,
            evaluation_items,
            include_profile=include_profile,
        )
        prediction_path = out_root / f"{comparator_id}-predictions.jsonl"
        write_predictions(prediction_path, evaluation_items, predictions)
        comparators[comparator_id] = {
            "include_active_policy_profile": include_profile,
            "feature_count": feature_count,
            "training_correct": training_correct,
            "training_accuracy": training_correct / len(development_items),
            "predictions_sha256": sha256_file(prediction_path),
        }

    report: Json = {
        "schema_version": "1.0.0",
        "status": "FROZEN_DEVELOPMENT_TRAINED_POLICY_SWITCH_COMPARATORS",
        "algorithm": "sklearn.ensemble.RandomForestClassifier",
        "scikit_learn_version": sklearn_version,
        "configuration": {
            "n_estimators": ESTIMATORS,
            "random_state": RANDOM_STATE,
            "class_weight": "balanced_subsample",
            "n_jobs": 1,
            "all_other_parameters": "scikit-learn defaults",
        },
        "feature_boundary": (
            "Both comparators use flattened model-visible state and verifier fields. The "
            "policy-aware comparator also observes active_policy_profile; the ablated comparator "
            "does not. Both exclude IDs, pair/factor metadata, policy-oracle calls, evaluation "
            "labels, and model outputs."
        ),
        "registered_shortcut_boundary": (
            "The profile-blind comparator receives identical features for both members of every "
            "evaluation pair and therefore cannot predict both action-changing labels."
        ),
        "development_items": len(development_items),
        "development_action_counts": dict(sorted(Counter(development_actions).items())),
        "evaluation_predictions_per_comparator": len(evaluation_items),
        "development_items_sha256": sha256_file(dataset_root / "development-items.jsonl"),
        "development_gold_sha256": sha256_file(dataset_root / "development-gold.jsonl"),
        "evaluation_items_sha256": sha256_file(dataset_root / "evaluation-items.jsonl"),
        "evaluation_gold_loaded": False,
        "model_outputs_loaded": False,
        "comparators": comparators,
    }
    (out_root / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    report = train(args.dataset_root.resolve(), args.out_root.resolve())
    print(
        canonical_json(
            {
                "status": report["status"],
                "evaluation_predictions_per_comparator": report[
                    "evaluation_predictions_per_comparator"
                ],
                "comparators": report["comparators"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
