"""Regression tests for frozen confirmatory baselines and statistics."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.dataset import load_json
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
BASE_PLAN = ROOT / "v2" / "stronger-model-study-plan.json"


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def public_dev(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset = tmp_path_factory.mktemp("confirmatory-baseline-dev") / "dev"
    _load_script("build_v1_dataset").build("dev", dataset, None)
    return dataset


def test_baseline_predictions_are_deterministic_and_cannot_read_test_gold(
    tmp_path: Path,
    public_dev: Path,
) -> None:
    packet_builder = _load_script("build_stronger_model_packet")
    trainer = _load_script("train_confirmatory_shallow_baseline")
    predictor = _load_script("predict_confirmatory_baselines")
    plan = load_json(BASE_PLAN)
    model = trainer.build_model(
        public_dev,
        sha256_file(public_dev / "manifest.json"),
        str(plan["prompt"]["arm"]),
        str(plan["prompt"]["provider_neutral_control_suffix"]),
    )
    plan["baselines"] = {
        "public_dev_manifest_sha256": sha256_file(public_dev / "manifest.json"),
        "predictor_sha256": None,
        "feature_module_sha256": None,
        "shallow_model_sha256": model["model_sha256"],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    packet = packet_builder.build_packet(public_dev, plan_path)

    first = predictor.build_predictions(model, packet, plan)
    second = predictor.build_predictions(model, packet, plan)
    assert first == second
    assert first["contains_test_gold"] is False
    assert first["reads_test_gold"] is False
    assert first["reads_test_dataset"] is False
    assert first["public_dev_action_counts"] == {
        "ALLOW": 50,
        "HOLD": 46,
        "DEMOTE": 2,
        "ESCALATE": 2,
    }
    assert len(first["records"]) == 100
    assert {row["predictions"]["public_dev_majority"] for row in first["records"]} == {"ALLOW"}
    payload = dict(first)
    digest = payload.pop("predictions_sha256")
    assert digest == sha256_bytes(canonical_json(payload).encode("utf-8"))


def test_exact_pair_blocked_swap_and_holm_cover_the_complete_registered_family() -> None:
    analysis = _load_script("analyze_confirmatory_hidden_study")
    pairs = [
        {"pair_id": "p1", "member_ids": ["a", "b"]},
        {"pair_id": "p2", "member_ids": ["c", "d"]},
    ]
    result = analysis.exact_pair_blocked_swap(
        {"a": True, "b": True, "c": False, "d": False},
        {"a": False, "b": True, "c": True, "d": False},
        pairs,
    )
    assert result == {
        "pairs": 2,
        "nonzero_pair_differences": 2,
        "sum_item_correctness_difference": 0,
        "action_accuracy_difference": 0.0,
        "one_sided_exact_p": 0.75,
        "test_unit": "controlled_pair",
        "permutation": "swap_complete_two_member_correctness_vectors_within_pair",
    }
    tests = [
        {"one_sided_exact_p": value, "id": index}
        for index, value in enumerate((0.001, 0.02, 0.04, 0.2, 0.5, 1.0))
    ]
    adjusted = analysis.holm_adjust(tests)
    assert len(adjusted) == 6
    assert adjusted[0]["holm_adjusted_p"] == pytest.approx(0.006)
    assert all(0.0 <= row["holm_adjusted_p"] <= 1.0 for row in adjusted)
