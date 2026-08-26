from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "v2" / "balanced-public-challenge" / "results"
PLAN = ROOT / "v2" / "balanced-public-challenge-study-plan.json"
DATASET = ROOT / "v2" / "balanced-public-challenge" / "dataset"
PACKET = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
CORRECTION = RESULTS / "reporting-correction-v1.json"
ACCOUNT_IDENTIFIER = re.compile(
    r"\buser_(?=[A-Za-z0-9_-]{20,64}\b)"
    r"(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]+\b"
)
HIDDEN_REASONING_FIELDS = {
    "reasoning_content",
    "thought",
    "thoughts",
    "thinking_content",
}


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _equivalent(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _equivalent(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_imported_result_hashes_and_privacy_boundaries() -> None:
    hashing = _load_script("analyze_balanced_public_challenge.py").sha256_file
    receipt = _json(RESULTS / "github-artifact-receipt.json")
    assert receipt["status"] == "IMPORTED_AND_INDEPENDENTLY_RECOMPUTED"
    assert receipt["source_commit"] == "1901e471bdf94f434f9671708b93599a106b1543"
    assert receipt["workflow"]["run_id"] == 32509532820
    assert receipt["source_artifact"]["digest"] == (
        "sha256:8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b"
    )
    for relative, expected in receipt["imported_files_sha256"].items():
        assert hashing(RESULTS / relative) == expected

    for path in sorted([*RESULTS.rglob("*.json"), *RESULTS.rglob("*.jsonl")]):
        text = path.read_text(encoding="utf-8")
        assert ACCOUNT_IDENTIFIER.search(text) is None
        values = (
            [json.loads(line) for line in text.splitlines() if line.strip()]
            if path.suffix == ".jsonl"
            else [json.loads(text)]
        )
        for value in _walk(values):
            if isinstance(value, dict):
                assert HIDDEN_REASONING_FIELDS.isdisjoint(value)
                if "provider_response_id" in value:
                    assert value["provider_response_id"] is None


def test_imported_aggregate_recomputes_from_all_360_terminal_records() -> None:
    analysis = _load_script("analyze_balanced_public_challenge.py")
    runs = sorted((RESULTS / "runs").glob("*-full.jsonl"))
    assert len(runs) == 2
    assert sum(len(path.read_text(encoding="utf-8").splitlines()) for path in runs) == 360

    recomputed = analysis.analyze_challenge(
        DATASET,
        _json(PACKET),
        _json(PLAN),
        PLAN,
        runs,
        workflow_run_url=(
            "https://github.com/f0909172434/claimpromote-bench/actions/runs/32509532820"
        ),
        workflow_run_attempt=1,
    )
    committed = _json(RESULTS / "aggregate.json")
    correction = _json(CORRECTION)
    receipt_payload = dict(correction)
    observed_receipt_sha = receipt_payload.pop("receipt_sha256")
    expected_receipt_sha = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                receipt_payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
    )
    assert observed_receipt_sha == expected_receipt_sha
    assert correction["status"] == "REPORTING_CORRECTION"
    assert correction["metric_convention"] == (
        "FIXED_FOUR_CLASS_MACRO_F1_WITH_ZERO_DIVISION_EQUAL_TO_ZERO"
    )
    assert correction["scope"] == {
        "conditional_macro_f1_changed": True,
        "confusion_matrix_changed": False,
        "end_to_end_item_or_pair_metrics_changed": False,
        "macro_f1_changed": True,
        "model_calls_performed": 0,
        "per_action_recall_changed": False,
        "primary_endpoints_changed": False,
        "raw_or_terminal_records_changed": False,
    }
    for relative, expected in correction["source_bindings"].items():
        assert analysis.sha256_file(ROOT / relative) == expected

    corrected_flash = next(
        lane["metrics"]
        for lane in recomputed["lanes"]
        if lane["lane_id"] == "opencode-go-deepseek-v4-flash-matched"
    )
    corrected = correction["affected_lanes"]["opencode-go-deepseek-v4-flash-matched"]
    assert corrected["corrected"] == {
        "conditional_macro_f1": corrected_flash["conditional_macro_f1"],
        "macro_f1": corrected_flash["macro_f1"],
        "per_action.DEMOTE.conditional_f1": corrected_flash["per_action"]["DEMOTE"][
            "conditional_f1"
        ],
        "per_action.DEMOTE.end_to_end_f1": corrected_flash["per_action"]["DEMOTE"]["end_to_end_f1"],
        "per_action.DEMOTE.precision": corrected_flash["per_action"]["DEMOTE"]["precision"],
    }

    # Preserve the imported workflow aggregate byte-for-byte. Its only differences from the
    # corrected recomputation are the five explicitly receipted Flash class metrics.
    historical_projection = deepcopy(recomputed)
    historical_flash = next(
        lane["metrics"]
        for lane in historical_projection["lanes"]
        if lane["lane_id"] == "opencode-go-deepseek-v4-flash-matched"
    )
    historical = corrected["historical"]
    historical_flash["conditional_macro_f1"] = historical["conditional_macro_f1"]
    historical_flash["macro_f1"] = historical["macro_f1"]
    historical_flash["per_action"]["DEMOTE"]["conditional_f1"] = historical[
        "per_action.DEMOTE.conditional_f1"
    ]
    historical_flash["per_action"]["DEMOTE"]["end_to_end_f1"] = historical[
        "per_action.DEMOTE.end_to_end_f1"
    ]
    historical_flash["per_action"]["DEMOTE"]["precision"] = historical[
        "per_action.DEMOTE.precision"
    ]
    assert _equivalent(committed, historical_projection)

    lanes = {row["lane_id"]: row["metrics"] for row in committed["lanes"]}
    qwen = lanes["opencode-go-qwen3.7-max"]
    flash = lanes["opencode-go-deepseek-v4-flash-matched"]
    assert qwen["parse_status_counts"] == {
        "OK": 148,
        "SEMANTIC_ERROR": 1,
        "TRANSPORT_ERROR": 31,
    }
    assert flash["parse_status_counts"] == {"OK": 146, "SEMANTIC_ERROR": 34}
    assert qwen["end_to_end_item_accuracy"] == 132 / 180
    assert qwen["end_to_end_pair_accuracy"] == 48 / 90
    assert flash["end_to_end_item_accuracy"] == 90 / 180
    assert flash["end_to_end_pair_accuracy"] == 13 / 90
    assert qwen["per_action"]["DEMOTE"]["correct"] == 4
    assert flash["per_action"]["DEMOTE"]["correct"] == 0
    assert corrected_flash["macro_f1"] == 0.39275710284113646
    assert corrected_flash["conditional_macro_f1"] == 0.46822747216138244
