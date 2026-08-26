from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_policy_migration_mutation_audit import (  # noqa: E402
    DEFAULT_GRAPH_COVERAGE,
    DEFAULT_GRAPH_PAIRS,
    DEFAULT_OUT,
    DEFAULT_RULE_COVERAGE,
    DEFAULT_RULE_PAIRS,
    derive,
)


def test_policy_migration_mutation_audit_recomputes_byte_exactly() -> None:
    observed = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    assert (
        derive(
            DEFAULT_RULE_PAIRS,
            DEFAULT_RULE_COVERAGE,
            DEFAULT_GRAPH_PAIRS,
            DEFAULT_GRAPH_COVERAGE,
        )
        == observed
    )


def test_graph_coverage_detects_every_registered_edge_local_mutant() -> None:
    audit = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    rule = audit["suites"]["rule_stratified"]
    graph = audit["suites"]["transition_graph"]
    assert rule["changed_rule_coverage"] == {"numerator": 12, "denominator": 12}
    assert rule["edge_local_mutant_detection"] == {
        "numerator": 6,
        "denominator": 10,
        "value": 0.6,
    }
    assert len(rule["edge_local_mutants_missed"]) == 4
    assert graph["changed_rule_coverage"] == {"numerator": 12, "denominator": 12}
    assert graph["edge_local_mutant_detection"] == {
        "numerator": 10,
        "denominator": 10,
        "value": 1.0,
    }
    assert graph["edge_local_mutants_missed"] == []
