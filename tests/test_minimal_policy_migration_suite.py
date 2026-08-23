from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_minimal_policy_migration_suite import (  # noqa: E402
    DEFAULT_COVERAGE,
    DEFAULT_OUT,
    DEFAULT_PAIRS,
    derive,
)


def test_minimal_policy_migration_suite_recomputes_byte_exactly() -> None:
    observed = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    assert derive(DEFAULT_PAIRS, DEFAULT_COVERAGE) == observed


def test_minimal_suite_meets_the_edge_lower_bound_and_covers_all_rules() -> None:
    receipt = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    assert receipt["optimality_certificate"] == {
        "lower_bound_pairs": 10,
        "lower_bound_reason": (
            "Each controlled pair realizes exactly one directed action edge, so covering ten "
            "distinct reachable edges requires at least ten pairs."
        ),
        "witness_pairs": 10,
        "bound_met": True,
    }
    assert receipt["coverage"] == {
        "reachable_edges": {"covered": 10, "total": 10},
        "changed_rules": {"covered": 12, "total": 12},
    }
    assert receipt["execution_budget"] == {
        "minimum_smoke_pairs": 10,
        "minimum_smoke_items": 20,
        "balanced_diagnostic_pairs": 60,
        "balanced_diagnostic_items": 120,
        "item_call_reduction_fraction": 5 / 6,
    }
    assert len(receipt["selected_pair_ids"]) == 10
    assert len(receipt["selected_item_ids"]) == 20
