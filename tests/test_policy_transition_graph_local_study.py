from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_policy_transition_graph_local_study import validate_all  # noqa: E402

FREEZE_ROOT = (
    ROOT / "v2" / "local-model-replication-v1" / "transition-graph-v1" / "frozen"
)
SNAPSHOT = ROOT / "v2" / "local-model-replication-v1" / "model-snapshot-receipt.json"
QUALIFICATION = ROOT / "v2" / "local-model-replication-v1" / "environment-qualification.json"
VOID = (
    ROOT
    / "v2"
    / "local-model-replication-v1"
    / "frozen"
    / "slsa"
    / "void-exclusion-receipt.json"
)


def test_policy_transition_graph_local_freeze_validates() -> None:
    validate_all(
        FREEZE_ROOT,
        ROOT / "v2" / "local-model-replication-v1" / "model-catalog.json",
        SNAPSHOT,
        QUALIFICATION,
        VOID,
    )


def test_policy_transition_graph_local_plan_is_preinference_and_zero_retry() -> None:
    root = FREEZE_ROOT / "policy-transition-graph"
    plan = json.loads((root / "study-plan.json").read_text(encoding="utf-8"))
    schedule = json.loads((root / "request-schedule.json").read_text(encoding="utf-8"))
    decision = json.loads(
        (root / "design-decision-receipt.json").read_text(encoding="utf-8")
    )
    assert decision["transition_graph_model_calls_before_freeze"] == 0
    assert decision["outcomes_used_to_choose_edges_or_contexts"] is False
    assert plan["dataset"]["evaluation_factors"] == 10
    assert schedule["planned_cells"] == 240
    assert schedule["client_retry_count"] == 0
    assert schedule["application_posts_per_cell"] == 1
