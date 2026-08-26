from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from scripts.upstream_policy_revision import (
    expected_decision,
    render_prompt,
    upstream_policy_cases,
    validate_decision_semantics,
)

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "upstream-policy-revisions-v1"


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_upstream_policy_revision_study.py"
    spec = importlib.util.spec_from_file_location("validate_upstream_policy_revision_study", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finite_grammar_is_balanced_and_traceable() -> None:
    cases = upstream_policy_cases()
    assert len(cases) == 12
    assert len({case.pair_id for case in cases}) == 12
    migrations = {case.migration_id for case in cases}
    assert migrations == {
        "unique-service-selector-kind-filter",
        "flexvolume-empty-allowlist-blocks-all",
    }
    assert sum(case.pair_id.startswith("upr-unique-") for case in cases) == 6
    assert sum(case.pair_id.startswith("upr-flex-") for case in cases) == 6


def test_expected_decisions_require_independent_opa_counts() -> None:
    for case in upstream_policy_cases():
        if case.migration_id == "unique-service-selector-kind-filter":
            old_count, new_count = len(case.changed_witnesses), 0
        else:
            old_count, new_count = 0, len(case.changed_witnesses)
        old = expected_decision(case, "old", observed_violation_count=old_count)
        new = expected_decision(case, "new", observed_violation_count=new_count)
        assert old["action"] != new["action"]
        validate_decision_semantics(old)
        validate_decision_semantics(new)
        with pytest.raises(ValueError, match="OPA produced"):
            expected_decision(case, "old", observed_violation_count=old_count + 1)


def test_prompt_hides_revision_and_gold_metadata() -> None:
    case = upstream_policy_cases()[0]
    prompt = render_prompt(case, "package example\nviolation := []\n")
    lowered = prompt.lower()
    assert '"revision"' not in lowered
    assert '"decision"' not in lowered
    assert "gold" not in lowered
    assert case.query in prompt
    assert "POLICY SOURCE" in prompt
    assert "INPUT JSON" in prompt
    assert "BASE DATA JSON" in prompt


@pytest.mark.parametrize(
    "decision",
    [
        {
            "action": "ALLOW",
            "violation_count": 1,
            "rule_id": "NONE",
            "witnesses": [],
        },
        {
            "action": "HOLD",
            "violation_count": 0,
            "rule_id": "FLEXVOLUME_DRIVER",
            "witnesses": [],
        },
        {
            "action": "HOLD",
            "violation_count": 2,
            "rule_id": "UNIQUE_SERVICE_SELECTOR",
            "witnesses": [{"kind": "Service", "namespace": "x", "name": "a"}],
        },
    ],
)
def test_semantic_contract_rejects_inconsistent_decisions(decision: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        validate_decision_semantics(decision)


def test_generated_study_validates_offline() -> None:
    report = load_validator().validate()
    assert report == {
        "items": 24,
        "pairs": 12,
        "migrations": 2,
        "transitions": {"ALLOW->HOLD": 6, "HOLD->ALLOW": 6},
        "minimum_pairs": 2,
    }


def test_source_registry_pins_full_commits_and_license() -> None:
    registry = json.loads((STUDY_ROOT / "sources" / "registry.json").read_text(encoding="utf-8"))
    assert registry["license"] == "Apache-2.0"
    assert (ROOT / registry["license_path"]).is_file()
    assert (ROOT / registry["notice_path"]).is_file()
    assert len(registry["revisions"]) == 2
    for revision in registry["revisions"]:
        assert len(revision["old_commit"]) == 40
        assert len(revision["change_commit"]) == 40
        assert revision["change_url"].endswith(revision["change_commit"])
        assert revision["old_sha256"].startswith("sha256:")
        assert revision["new_sha256"].startswith("sha256:")
