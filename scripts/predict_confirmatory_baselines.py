#!/usr/bin/env python3
"""Freeze deterministic hidden predictions without accepting a dataset or gold path."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.confirmatory_baseline import (  # noqa: E402
    ACTIONS,
    predict_text_nb,
    validate_model,
)
from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"confirmatory-baselines: {message}")


def _stratified_prior_action(prompt_sha256: str, counts: Counter[str]) -> str:
    digest = sha256_bytes(f"public-dev-prior-v1:{prompt_sha256}".encode())
    quantile = int(digest.removeprefix("sha256:"), 16) / (1 << 256)
    total = sum(counts.values())
    cumulative = 0.0
    for action in ACTIONS:
        cumulative += counts[action] / total
        if quantile < cumulative:
            return action
    return ACTIONS[-1]


def build_predictions(model: Json, packet: Json, plan: Json) -> Json:
    """Predict every packet row without any interface for hidden labels."""

    validate_model(model)
    expected_predictor = plan.get("baselines", {}).get("predictor_sha256")
    observed_predictor = sha256_file(Path(__file__))
    if expected_predictor is not None and expected_predictor != observed_predictor:
        fail("baseline predictor differs from the frozen plan")
    expected_model = plan.get("baselines", {}).get("shallow_model_sha256")
    if expected_model is not None and expected_model != model["model_sha256"]:
        fail("shallow baseline model differs from the frozen plan")
    expected_feature_module = plan.get("baselines", {}).get("feature_module_sha256")
    observed_feature_module = sha256_file(
        ROOT / "src" / "claimpromotebench" / "confirmatory_baseline.py"
    )
    if expected_feature_module is not None and expected_feature_module != observed_feature_module:
        fail("shallow baseline feature module differs from the frozen plan")
    if packet.get("study_id") != plan.get("study_id"):
        fail("packet study_id differs from plan")
    counts = Counter({action: int(model["document_counts"][action]) for action in ACTIONS})
    majority = max(ACTIONS, key=lambda action: (counts[action], -ACTIONS.index(action)))
    records: list[Json] = []
    for row in sorted(packet["records"], key=lambda value: str(value["item_id"])):
        prompt = str(row["prompt"])
        prompt_sha256 = str(row["prompt_sha256"])
        records.append(
            {
                "item_id": str(row["item_id"]),
                "pair_id": str(row["pair_id"]),
                "prompt_sha256": prompt_sha256,
                "predictions": {
                    "always_allow": "ALLOW",
                    "always_hold": "HOLD",
                    "public_dev_majority": majority,
                    "public_dev_stratified_prior": _stratified_prior_action(prompt_sha256, counts),
                    "public_dev_text_nb": predict_text_nb(model, prompt),
                },
            }
        )
    report: Json = {
        "schema_version": "1.0.0",
        "study_id": str(plan["study_id"]),
        "packet_sha256": str(packet["packet_sha256"]),
        "public_dev_manifest_sha256": model["training"]["public_dev_manifest_sha256"],
        "shallow_model_sha256": model["model_sha256"],
        "predictor_sha256": observed_predictor,
        "feature_module_sha256": observed_feature_module,
        "contains_test_gold": False,
        "reads_test_dataset": False,
        "reads_test_gold": False,
        "action_order": list(ACTIONS),
        "public_dev_action_counts": {action: counts[action] for action in ACTIONS},
        "method_specs": {
            "public_dev_majority": (
                "Equivalent to always-ALLOW on the frozen public dev set; descriptive sanity check."
            ),
            "public_dev_stratified_prior": (
                "Descriptive SHA-256 prompt-hash allocation using fixed public-dev class shares; "
                "not a confirmatory comparator."
            ),
            "public_dev_text_nb": (
                "C0-frozen four-class multinomial NB; alpha=1; identifier-normalized prompt "
                "unigram+bigram counts."
            ),
        },
        "records": records,
    }
    report["predictions_sha256"] = sha256_bytes(canonical_json(report).encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_predictions(
        load_json(args.model.resolve()),
        load_json(args.packet.resolve()),
        load_json(args.plan.resolve()),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "BASELINES_FROZEN_WITHOUT_TEST_GOLD",
                "records": len(report["records"]),
                "predictions_sha256": report["predictions_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
