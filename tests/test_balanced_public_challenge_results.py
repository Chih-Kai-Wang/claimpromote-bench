from __future__ import annotations

import importlib.util
import json
import math
import re
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "v2" / "balanced-public-challenge" / "results"
PLAN = ROOT / "v2" / "balanced-public-challenge-study-plan.json"
DATASET = ROOT / "v2" / "balanced-public-challenge" / "dataset"
PACKET = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
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
    assert _equivalent(committed, recomputed)

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
