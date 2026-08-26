from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "v2"
    / "local-model-replication-v1"
    / "transition-graph-v1"
    / "minimum-subset-analysis-plan.json"
)
SCRIPT_PATH = ROOT / "scripts" / "analyze_minimal_policy_migration_gate.py"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_minimum_subset_analysis_was_bound_before_graph_execution() -> None:
    plan = load_json(PLAN_PATH)
    minimum = load_json(ROOT / plan["source_bindings"]["minimum_suite"]["path"])
    assert plan["status"] == "PROSPECTIVELY_FROZEN_MINIMUM_MIGRATION_SUBSET_ANALYSIS"
    assert plan["freeze"]["full_graph_terminal_records_before_analysis_freeze"] == 0
    assert plan["selection"]["model_outputs_consulted"] is False
    assert plan["selection"]["selected_before_route_execution"] is True
    assert plan["selection"]["selected_pair_ids"] == minimum["selected_pair_ids"]
    assert plan["selection"]["selected_item_ids"] == minimum["selected_item_ids"]
    assert plan["execution"]["additional_model_or_client_calls"] == 0
    for binding in plan["source_bindings"].values():
        assert binding["sha256"] == sha256_file(ROOT / binding["path"])


def test_strict_gate_requires_every_item_and_pair() -> None:
    module = runpy.run_path(str(SCRIPT_PATH), run_name="minimum_gate_test")
    strict_gate_pass = module["strict_gate_pass"]
    passing = {
        "items": 20,
        "pairs": 10,
        "parseable_items": 20,
        "correct_items": 20,
        "covered_pairs": 10,
        "correct_pairs": 10,
    }
    assert strict_gate_pass(passing) is True
    for field in ("parseable_items", "correct_items"):
        failing = dict(passing)
        failing[field] = 19
        assert strict_gate_pass(failing) is False
    for field in ("covered_pairs", "correct_pairs"):
        failing = dict(passing)
        failing[field] = 9
        assert strict_gate_pass(failing) is False
