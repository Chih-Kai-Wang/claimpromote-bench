from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_json

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "v2" / "policy-switch-v1" / "frozen" / "results"


def load_deriver() -> ModuleType:
    path = ROOT / "scripts" / "derive_policy_switch_hosted_exclusion.py"
    spec = importlib.util.spec_from_file_location("derive_policy_switch_hosted_exclusion", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hosted_policy_switch_is_excluded_in_full_without_row_selection() -> None:
    module = load_deriver()
    expected = module.derive(
        ROOT / "v2" / "policy-switch-v1" / "frozen" / "study-plan.json",
        ROOT / "v2" / "policy-switch-v1" / "frozen" / "journal" / "terminal-records.jsonl",
        RESULTS,
        ROOT / "v2" / "local-model-replication-v1" / "model-catalog.json",
    )
    receipt = load_json(RESULTS / "manuscript-exclusion-receipt.json")
    assert receipt == expected
    assert receipt["observed_terminal_counts"] == {
        "scheduled_and_terminal": 240,
        "valid_decisions": 113,
        "semantic_errors": 12,
        "quota_or_rate_limit_errors": 114,
        "server_errors": 1,
        "first_quota_or_rate_limit_sequence": 126,
        "last_quota_or_rate_limit_sequence": 239,
    }
    assert receipt["decision"]["hosted_model_rows_enter_manuscript"] is False
    assert receipt["decision"]["successful_row_subset_selected"] is False
    assert receipt["decision"]["hosted_study_resumed_or_retried"] is False
