#!/usr/bin/env python3
"""Train the frozen policy-blind structured action baseline without evaluation labels."""

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
    raise SystemExit(f"slsa-structured-baseline: {message}")


def load_jsonl(path: Path) -> list[Json]:
    rows: list[Json] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            fail(f"{path} contains a non-object row")
        rows.append(value)
    return rows


def flatten_visible(item: Json, conflict_codes: tuple[str, ...]) -> dict[str, str | int | bool]:
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
    for key, value in observed.items():
        if isinstance(value, bool):
            features[f"observed.{key}"] = value
    conflicts = set(str(value) for value in observed["authenticated_conflicts"])
    for code in conflict_codes:
        features[f"conflict.{code}"] = code in conflicts
    return features


def train(dataset_root: Path, out_root: Path) -> Json:
    if out_root.exists():
        fail(f"output root already exists: {out_root}")
    out_root.mkdir(parents=True)
    policy = json.loads(
        (ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json").read_text(encoding="utf-8")
    )
    conflict_codes = tuple(str(value) for value in policy["authenticated_conflict_codes"])
    development_items = load_jsonl(dataset_root / "development-items.jsonl")
    development_gold = load_jsonl(dataset_root / "development-gold.jsonl")
    evaluation_items = load_jsonl(dataset_root / "evaluation-items.jsonl")
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in development_gold}
    if set(gold_by_id) != {str(row["id"]) for row in development_items}:
        fail("development item and label IDs differ")

    vectorizer = DictVectorizer(sparse=False, sort=True)
    development_features = [
        flatten_visible(row["model_visible"], conflict_codes) for row in development_items
    ]
    development_matrix = vectorizer.fit_transform(development_features)
    development_actions = [gold_by_id[str(row["id"])] for row in development_items]
    classifier = RandomForestClassifier(
        n_estimators=ESTIMATORS,
        random_state=RANDOM_STATE,
        class_weight="balanced_subsample",
        n_jobs=1,
    )
    classifier.fit(development_matrix, development_actions)
    training_predictions = classifier.predict(development_matrix).tolist()

    evaluation_features = [
        flatten_visible(row["model_visible"], conflict_codes) for row in evaluation_items
    ]
    evaluation_matrix = vectorizer.transform(evaluation_features)
    predicted_actions = classifier.predict(evaluation_matrix).tolist()
    predictions = [
        {
            "item_id": row["id"],
            "pair_id": row["pair_id"],
            "predicted_action": str(action),
        }
        for row, action in zip(evaluation_items, predicted_actions, strict=True)
    ]
    prediction_path = out_root / "predictions.jsonl"
    prediction_path.write_text(
        "".join(canonical_json(row) + "\n" for row in predictions), encoding="utf-8"
    )
    training_correct = sum(
        predicted == expected
        for predicted, expected in zip(training_predictions, development_actions, strict=True)
    )
    report: Json = {
        "schema_version": "1.0.0",
        "status": "FROZEN_POLICY_BLIND_STRUCTURED_ACTION_BASELINE",
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
            "Flattened model-visible state and verifier fields only; excludes IDs, pair/factor "
            "metadata, policy-oracle calls, evaluation labels, and model outputs."
        ),
        "development_items": len(development_items),
        "development_action_counts": dict(sorted(Counter(development_actions).items())),
        "feature_count": len(vectorizer.feature_names_),
        "training_correct": training_correct,
        "training_accuracy": training_correct / len(development_items),
        "evaluation_predictions": len(predictions),
        "development_items_sha256": sha256_file(dataset_root / "development-items.jsonl"),
        "development_gold_sha256": sha256_file(dataset_root / "development-gold.jsonl"),
        "evaluation_items_sha256": sha256_file(dataset_root / "evaluation-items.jsonl"),
        "predictions_sha256": sha256_file(prediction_path),
        "evaluation_gold_loaded": False,
        "model_outputs_loaded": False,
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
                "training_accuracy": report["training_accuracy"],
                "evaluation_predictions": report["evaluation_predictions"],
                "predictions_sha256": report["predictions_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
