from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = _load_script("analyze_balanced_public_challenge.py")


def _decision(action: str) -> dict[str, str]:
    return {"action": action}


def test_failure_aware_metrics_separate_coverage_from_conditional_accuracy() -> None:
    gold = [
        {"id": "p1-a", "decision": _decision("ALLOW")},
        {"id": "p1-b", "decision": _decision("HOLD")},
        {"id": "p2-a", "decision": _decision("ALLOW")},
        {"id": "p2-b", "decision": _decision("DEMOTE")},
        {"id": "p3-a", "decision": _decision("ALLOW")},
        {"id": "p3-b", "decision": _decision("ESCALATE")},
    ]
    pairs = [
        {"pair_id": "p1", "member_ids": ["p1-a", "p1-b"], "factor_id": "f1"},
        {"pair_id": "p2", "member_ids": ["p2-a", "p2-b"], "factor_id": "f2"},
        {"pair_id": "p3", "member_ids": ["p3-a", "p3-b"], "factor_id": "f3"},
    ]
    records = [
        {"item_id": "p1-a", "parse_status": "OK", "raw_decision": _decision("ALLOW")},
        {"item_id": "p1-b", "parse_status": "OK", "raw_decision": _decision("HOLD")},
        {
            "item_id": "p2-a",
            "parse_status": "TRANSPORT_ERROR",
            "raw_decision": None,
        },
        {"item_id": "p2-b", "parse_status": "OK", "raw_decision": _decision("DEMOTE")},
        {"item_id": "p3-a", "parse_status": "OK", "raw_decision": _decision("HOLD")},
        {"item_id": "p3-b", "parse_status": "OK", "raw_decision": _decision("ALLOW")},
    ]

    result = analysis.derive_reporting_metrics(gold, pairs, records)

    assert result["decision_coverage"] == 5 / 6
    assert result["end_to_end_item_accuracy"] == 3 / 6
    assert result["conditional_item_accuracy"] == 3 / 5
    assert result["pair_coverage"] == 2 / 3
    assert result["end_to_end_pair_accuracy"] == 1 / 3
    assert result["conditional_pair_accuracy"] == 1 / 2
    counts = result["confusion_matrix"]["counts"]
    assert counts["ALLOW"] == {
        "ALLOW": 1,
        "HOLD": 1,
        "DEMOTE": 0,
        "ESCALATE": 0,
        "NO_VALID_DECISION": 1,
    }
    assert result["per_action"]["DEMOTE"]["end_to_end_recall"] == 1.0
    assert result["per_action"]["ESCALATE"]["end_to_end_recall"] == 0.0


def test_pooling_sums_cells_and_preserves_failure_denominators() -> None:
    gold = [
        {"id": "p-a", "decision": _decision("ALLOW")},
        {"id": "p-b", "decision": _decision("HOLD")},
    ]
    pairs = [{"pair_id": "p", "member_ids": ["p-a", "p-b"], "factor_id": "f"}]
    records = [
        {"item_id": "p-a", "parse_status": "OK", "raw_decision": _decision("ALLOW")},
        {"item_id": "p-b", "parse_status": "SCHEMA_ERROR", "raw_decision": None},
    ]
    lane = analysis.derive_reporting_metrics(gold, pairs, records)

    pooled = analysis.combine_lane_metrics([lane, lane])

    assert pooled["items"] == 4
    assert pooled["correct_items"] == 2
    assert pooled["end_to_end_item_accuracy"] == 0.5
    assert pooled["conditional_item_accuracy"] == 1.0
    assert pooled["pairs"] == 2
    assert pooled["covered_pairs"] == 0
    assert pooled["conditional_pair_accuracy"] is None
    assert pooled["confusion_matrix"]["counts"]["HOLD"]["NO_VALID_DECISION"] == 2
