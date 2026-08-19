#!/usr/bin/env python3
"""Validate the artifact-only public v2 pilot aggregate and its paper-facing facts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "v2" / "pilot-results" / "v2-public-pilot-study.json"
EXPECTED_STUDY_SHA = "sha256:83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e"
EXPECTED_RUN = 32291482079
EXPECTED = {
    ("Qwen/Qwen3-0.6B", "free"): {
        "status_counts": {
            "JSON_SYNTAX_ERROR": 0,
            "OK": 30,
            "SCHEMA_ERROR": 10,
            "SEMANTIC_ERROR": 0,
        },
        "decision_coverage": 0.75,
        "pair_coverage": 0.70,
        "raw_action_accuracy": 0.50,
        "raw_pair_accuracy": 0.0,
        "raw_flip_rate": 0.0,
    },
    ("Qwen/Qwen3-0.6B", "json_schema"): {
        "status_counts": {
            "JSON_SYNTAX_ERROR": 0,
            "OK": 40,
            "SCHEMA_ERROR": 0,
            "SEMANTIC_ERROR": 0,
        },
        "decision_coverage": 1.0,
        "pair_coverage": 1.0,
        "raw_action_accuracy": 0.50,
        "raw_pair_accuracy": 0.0,
        "raw_flip_rate": 0.0,
    },
    ("Qwen/Qwen3-1.7B", "free"): {
        "status_counts": {
            "JSON_SYNTAX_ERROR": 0,
            "OK": 0,
            "SCHEMA_ERROR": 40,
            "SEMANTIC_ERROR": 0,
        },
        "decision_coverage": 0.0,
        "pair_coverage": 0.0,
        "raw_action_accuracy": None,
        "raw_pair_accuracy": None,
        "raw_flip_rate": None,
    },
    ("Qwen/Qwen3-1.7B", "json_schema"): {
        "status_counts": {
            "JSON_SYNTAX_ERROR": 0,
            "OK": 38,
            "SCHEMA_ERROR": 2,
            "SEMANTIC_ERROR": 0,
        },
        "decision_coverage": 0.95,
        "pair_coverage": 0.90,
        "raw_action_accuracy": 0.50,
        "raw_pair_accuracy": 0.0,
        "raw_flip_rate": 0.0,
    },
}

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"v2-public-pilot: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("study file must contain a JSON object")
    return value


def close(observed: Any, expected: float, label: str) -> None:
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        fail(f"{label} must be numeric")
    if not math.isclose(float(observed), expected, rel_tol=0.0, abs_tol=1e-12):
        fail(f"{label} mismatch: expected {expected}, got {observed}")


def reject_private_or_raw_fields(value: Any, path: str = "$") -> None:
    forbidden = {"raw_response_text", "raw_decision", "postgate_decision", "prompt"}
    if isinstance(value, dict):
        overlap = forbidden & set(value)
        if overlap:
            fail(f"public aggregate contains forbidden fields at {path}: {sorted(overlap)}")
        for key, child in value.items():
            reject_private_or_raw_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_private_or_raw_fields(child, f"{path}[{index}]")


def main() -> int:
    study = load_object(STUDY)
    reject_private_or_raw_fields(study)

    if study.get("status") != "COMPLETE":
        fail("study status is not COMPLETE")
    if study.get("study_kind") != "POST_V1_PUBLIC_INTERFACE_PILOT":
        fail("study kind changed")
    if study.get("source_workflow_run_id") != EXPECTED_RUN:
        fail("source workflow run changed")
    if study.get("study_sha256") != EXPECTED_STUDY_SHA:
        fail("study SHA changed")
    if study.get("aggregate_status_counts") != {"OK": 108, "SCHEMA_ERROR": 52}:
        fail("aggregate status counts changed")

    protocol = study.get("protocol")
    if not isinstance(protocol, dict):
        fail("protocol is missing")
    required_protocol = {
        "dataset": "data/alpha",
        "instances": 40,
        "pairs": 20,
        "seed": 104729,
        "prompt_arm": "ledger_verifier",
        "total_decisions": 160,
        "paid_api_calls": 0,
    }
    for key, expected in required_protocol.items():
        if protocol.get(key) != expected:
            fail(f"protocol.{key} changed")
    if set(protocol.get("models", [])) != {"Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"}:
        fail("protocol model matrix changed")
    if set(protocol.get("decoding_modes", [])) != {"free", "json_schema"}:
        fail("protocol decoding modes changed")

    runs = study.get("runs")
    if not isinstance(runs, list) or len(runs) != 4:
        fail("study must contain four run summaries")
    seen: set[tuple[str, str]] = set()
    parseable = 0
    constrained_parseable = 0
    constrained_covered_pairs = 0
    for row in runs:
        if not isinstance(row, dict) or not isinstance(row.get("summary"), dict):
            fail("malformed run summary")
        identity = (str(row.get("model_id")), str(row.get("decoding_mode")))
        if identity in seen or identity not in EXPECTED:
            fail(f"unexpected or duplicate run identity: {identity}")
        seen.add(identity)
        summary = row["summary"]
        expected = EXPECTED[identity]
        if summary.get("records") != 40:
            fail(f"{identity} does not contain 40 records")
        if summary.get("status_counts") != expected["status_counts"]:
            fail(f"{identity} status counts changed")
        for key in (
            "decision_coverage",
            "pair_coverage",
            "raw_action_accuracy",
            "raw_pair_accuracy",
            "raw_flip_rate",
        ):
            expected_value = expected[key]
            observed = summary.get(key)
            if expected_value is None:
                if observed is not None:
                    fail(f"{identity}.{key} must be undefined")
            else:
                close(observed, float(expected_value), f"{identity}.{key}")
        if summary.get("decision_coverage", 0) > 0:
            close(summary.get("raw_fpr"), 1.0, f"{identity}.raw_fpr")
            close(summary.get("raw_vpr"), 1.0, f"{identity}.raw_vpr")
            close(
                summary.get("postgate_action_accuracy"),
                1.0,
                f"{identity}.postgate_action_accuracy",
            )
            close(
                summary.get("postgate_pair_accuracy"),
                1.0,
                f"{identity}.postgate_pair_accuracy",
            )
        else:
            undefined_keys = (
                "raw_fpr",
                "raw_vpr",
                "postgate_action_accuracy",
                "postgate_pair_accuracy",
            )
            for key in undefined_keys:
                if summary.get(key) is not None:
                    fail(f"{identity}.{key} must be undefined with zero coverage")
        ok = int(summary["status_counts"]["OK"])
        parseable += ok
        if identity[1] == "json_schema":
            constrained_parseable += ok
            constrained_covered_pairs += int(summary["covered_pairs"])

    if seen != set(EXPECTED):
        fail("run matrix is incomplete")
    if parseable != 108:
        fail("parseable decision count changed")
    if constrained_parseable != 78:
        fail("constrained parseable decision count changed")
    if constrained_covered_pairs != 38:
        fail("constrained complete-pair count changed")

    comparisons = study.get("model_comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 2:
        fail("model comparison matrix changed")
    expected_deltas = {
        "Qwen/Qwen3-0.6B": (0.25, 0.30, 10),
        "Qwen/Qwen3-1.7B": (0.95, 0.90, 38),
    }
    for comparison in comparisons:
        if not isinstance(comparison, dict):
            fail("malformed model comparison")
        model = str(comparison.get("model_id"))
        invariants = comparison.get("invariants")
        effect = comparison.get("constraint_effect")
        comparison_is_valid = (
            model in expected_deltas
            and isinstance(invariants, dict)
            and isinstance(effect, dict)
        )
        if not comparison_is_valid:
            fail("unknown model comparison")
        if invariants.get("status") != "PASS":
            fail(f"{model} prompt/runtime invariants do not pass")
        if invariants.get("only_registered_difference") != "response_format":
            fail(f"{model} has an unregistered mode difference")
        if not invariants.get("prompt_hashes_identical"):
            fail(f"{model} prompt hashes differ")
        coverage_delta, pair_delta, removed = expected_deltas[model]
        close(effect.get("decision_coverage_delta"), coverage_delta, f"{model}.coverage_delta")
        close(effect.get("pair_coverage_delta"), pair_delta, f"{model}.pair_delta")
        if effect.get("schema_errors_removed") != removed:
            fail(f"{model} schema-error reduction changed")

    print(
        "v2-public-pilot: PASS "
        f"(160 decisions, 108 parseable, 78 constrained parseable, "
        f"38 constrained complete pairs, {EXPECTED_STUDY_SHA})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
