"""Regression tests for the post-study r6 reporting addendum."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "derive_r6_reporting_addendum.py"
ARTIFACT = ROOT / "v2" / "confirmatory" / "r6-execution" / "reviewer-reporting-addendum.json"


def load_deriver():
    spec = importlib.util.spec_from_file_location("r6_reporting_addendum", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r6_reporting_addendum_recomputes_committed_artifact() -> None:
    deriver = load_deriver()
    observed = deriver.build_addendum()
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert observed == committed
    digest_payload = dict(observed)
    digest = digest_payload.pop("self_digest")
    assert digest == sha256_bytes(canonical_json(digest_payload).encode("utf-8"))


def test_r6_reporting_addendum_exposes_service_and_reasoning_decomposition() -> None:
    deriver = load_deriver()
    report = deriver.build_addendum()
    qwen = report["qwen_service_configuration"]

    assert qwen["valid_decisions"] == 272
    assert qwen["correct_items"] == 258
    assert qwen["complete_pairs"] == 123
    assert qwen["correct_pairs"] == 113
    assert qwen["conditional_item_accuracy_given_valid_decision"] == 258 / 272
    assert qwen["conditional_pair_accuracy_given_complete_pair"] == 113 / 123
    assert qwen["confusion"]["DEMOTE"]["ALLOW"] == 8
    assert report["invalid_action_factor_support"]["DEMOTE"] == {"current_binding": 8}
    assert report["invalid_action_factor_support"]["ESCALATE"] == {"contradiction": 8}


def test_policy_executor_is_explicitly_a_definitional_ceiling() -> None:
    deriver = load_deriver()
    ceiling = deriver.build_addendum()["deterministic_policy_executor"]

    assert ceiling["role"] == "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    assert ceiling["reads_released_gold_during_prediction"] is False
    assert ceiling["correct_items"] == 300
    assert ceiling["correct_pairs"] == 150
