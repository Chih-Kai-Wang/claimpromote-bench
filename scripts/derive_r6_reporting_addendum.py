#!/usr/bin/env python3
"""Derive post-study reporting diagnostics from the immutable public r6 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.oracle import evaluate  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
NO_DECISION = "NO_DECISION"
DEFAULT_EVIDENCE = ROOT / "release" / "reviewer-evidence-source" / "fresh-confirmatory"
DEFAULT_OUTPUT = (
    ROOT / "v2" / "confirmatory" / "r6-execution" / "reviewer-reporting-addendum.json"
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSONL objects: {path}")
    return rows


def raw_prediction(row: Json) -> str | None:
    if row.get("parse_status") != "OK" or not isinstance(row.get("raw_decision"), dict):
        return None
    action = str(row["raw_decision"].get("action"))
    return action if action in ACTIONS else None


def build_addendum(evidence_root: Path = DEFAULT_EVIDENCE) -> Json:
    dataset = evidence_root / "dataset"
    manifest_path = dataset / "manifest.json"
    analysis_path = evidence_root / "confirmatory-analysis-public.json"
    qwen_paths = sorted(
        evidence_root.glob("collected/*/complete/opencode-go-qwen3.7-max-c2-complete.jsonl")
    )
    if len(qwen_paths) != 1:
        raise ValueError("expected exactly one public Qwen r6 C2 run")
    qwen_path = qwen_paths[0]

    manifest = load_json(manifest_path)
    inputs = {str(row["id"]): row for row in load_jsonl(dataset / "inputs.jsonl")}
    gold = {
        str(row["id"]): str(row["decision"]["action"])
        for row in load_jsonl(dataset / "gold.jsonl")
    }
    pairs_value = json.loads((dataset / "pairs.json").read_text(encoding="utf-8"))
    if not isinstance(pairs_value, list) or not all(isinstance(row, dict) for row in pairs_value):
        raise ValueError("pairs.json must contain pair objects")
    pairs: list[Json] = pairs_value
    run_rows = load_jsonl(qwen_path)
    rows = {str(row["item_id"]): row for row in run_rows}
    expected_ids = {item_id for pair in pairs for item_id in pair["member_ids"]}
    if set(inputs) != set(gold) or set(gold) != set(rows) or set(rows) != expected_ids:
        raise ValueError("r6 input, gold, run, and pair coverage differ")

    predictions = {item_id: raw_prediction(rows[item_id]) for item_id in sorted(expected_ids)}
    confusion = {
        action: {predicted: 0 for predicted in (*ACTIONS, NO_DECISION)} for action in ACTIONS
    }
    correct: dict[str, bool] = {}
    for item_id in sorted(expected_ids):
        predicted = predictions[item_id]
        confusion[gold[item_id]][predicted if predicted is not None else NO_DECISION] += 1
        correct[item_id] = predicted == gold[item_id]

    covered_items = sum(prediction is not None for prediction in predictions.values())
    correct_items = sum(correct.values())
    complete_pairs = [
        pair
        for pair in pairs
        if all(predictions[str(item_id)] is not None for item_id in pair["member_ids"])
    ]
    correct_pairs = [
        pair for pair in pairs if all(correct[str(item_id)] for item_id in pair["member_ids"])
    ]

    factor_support: dict[str, Counter[str]] = {action: Counter() for action in ACTIONS}
    factor_counts: dict[str, Json] = {}
    for pair in pairs:
        invalid_id = str(pair["invalid_id"])
        factor_id = str(pair["factor_id"])
        invalid_action = gold[invalid_id]
        factor_support[invalid_action][factor_id] += 1
        factor = factor_counts.setdefault(
            factor_id,
            {
                "factor_id": factor_id,
                "family": str(pair["family"]),
                "invalid_action": invalid_action,
                "pairs": 0,
                "covered_pairs": 0,
                "correct_pairs": 0,
            },
        )
        if factor["family"] != str(pair["family"]) or factor["invalid_action"] != invalid_action:
            raise ValueError(f"inconsistent r6 factor metadata: {factor_id}")
        member_ids = [str(item_id) for item_id in pair["member_ids"]]
        factor["pairs"] += 1
        factor["covered_pairs"] += all(predictions[item_id] is not None for item_id in member_ids)
        factor["correct_pairs"] += all(correct[item_id] for item_id in member_ids)

    factor_metrics: list[Json] = []
    for factor_id in sorted(factor_counts):
        factor = factor_counts[factor_id]
        covered = int(factor["covered_pairs"])
        pair_count = int(factor["pairs"])
        pair_correct = int(factor["correct_pairs"])
        factor_metrics.append(
            {
                **factor,
                "pair_coverage": covered / pair_count,
                "end_to_end_pair_accuracy": pair_correct / pair_count,
                "conditional_pair_accuracy": pair_correct / covered if covered else None,
            }
        )

    policy = load_policy(ROOT / "policies" / str(manifest["policy_file"]))
    evaluation_time = str(manifest["evaluation_time"])
    oracle_predictions = {
        item_id: str(evaluate(inputs[item_id], policy, evaluation_time)["action"])
        for item_id in sorted(inputs)
    }
    oracle_correct_items = sum(oracle_predictions[item_id] == gold[item_id] for item_id in gold)
    oracle_correct_pairs = sum(
        all(
            oracle_predictions[str(item_id)] == gold[str(item_id)]
            for item_id in pair["member_ids"]
        )
        for pair in pairs
    )

    reported = load_json(analysis_path)
    reported_qwen = reported["scores"]["opencode-go-qwen3.7-max"]["raw"]
    reported_nb = reported["scores"]["public_dev_text_nb"]["raw"]
    if (
        correct_items / len(expected_ids) != reported_qwen["item_accuracy"]
        or len(correct_pairs) / len(pairs) != reported_qwen["pair_accuracy"]
        or confusion != reported_qwen["confusion"]
    ):
        raise ValueError("derived Qwen reporting differs from the frozen scientific analysis")
    if oracle_correct_items != len(expected_ids) or oracle_correct_pairs != len(pairs):
        raise ValueError("deterministic policy executor differs from released gold")

    addendum: Json = {
        "schema_version": "1.1.0",
        "status": "POST_STUDY_DESCRIPTIVE_REPORTING_ADDENDUM",
        "interpretation_boundary": (
            "Derived after r6 unblinding to expose service coverage, conditional correctness, "
            "confusion, factor-level pair outcomes, action-factor concentration, and the "
            "deterministic policy ceiling. It does not alter the preregistered hypotheses, C2 "
            "records, frozen analysis, or claims."
        ),
        "sources": {
            "dataset_manifest_sha256": sha256_file(manifest_path),
            "frozen_analysis_sha256": sha256_file(analysis_path),
            "qwen_c2_public_run_sha256": sha256_file(qwen_path),
            "derivation_script_sha256": sha256_file(Path(__file__)),
        },
        "qwen_service_configuration": {
            "items": len(expected_ids),
            "valid_decisions": covered_items,
            "decision_coverage": covered_items / len(expected_ids),
            "correct_items": correct_items,
            "end_to_end_item_accuracy": correct_items / len(expected_ids),
            "conditional_item_accuracy_given_valid_decision": correct_items / covered_items,
            "pairs": len(pairs),
            "complete_pairs": len(complete_pairs),
            "pair_coverage": len(complete_pairs) / len(pairs),
            "correct_pairs": len(correct_pairs),
            "end_to_end_pair_accuracy": len(correct_pairs) / len(pairs),
            "conditional_pair_accuracy_given_complete_pair": len(correct_pairs)
            / len(complete_pairs),
            "confusion": confusion,
            "factor_metrics": factor_metrics,
        },
        "public_dev_text_nb": {
            "end_to_end_item_accuracy": reported_nb["item_accuracy"],
            "end_to_end_pair_accuracy": reported_nb["pair_accuracy"],
            "balanced_action_recall": reported_nb["balanced_action_recall"],
            "macro_f1": reported_nb["macro_f1"],
        },
        "deterministic_policy_executor": {
            "role": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE",
            "reads_model_visible_inputs_and_public_policy": True,
            "reads_released_gold_during_prediction": False,
            "correct_items": oracle_correct_items,
            "item_accuracy": oracle_correct_items / len(expected_ids),
            "correct_pairs": oracle_correct_pairs,
            "pair_accuracy": oracle_correct_pairs / len(pairs),
        },
        "invalid_action_factor_support": {
            action: dict(sorted(counts.items()))
            for action, counts in factor_support.items()
            if counts
        },
    }
    addendum["self_digest"] = sha256_bytes(canonical_json(addendum).encode("utf-8"))
    return addendum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    addendum = build_addendum(args.evidence_root.resolve())
    output = args.out.resolve()
    rendered = json.dumps(addendum, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("r6-reporting-addendum: committed artifact differs from recomputation")
        print("r6-reporting-addendum: PASS")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
