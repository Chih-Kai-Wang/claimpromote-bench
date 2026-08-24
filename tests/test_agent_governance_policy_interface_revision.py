from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "agent-governance-policy-interface-revision-v1"


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_agent_governance_policy_interface_revision.py"
    spec = importlib.util.spec_from_file_location(
        "validate_agent_governance_policy_interface_revision", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_governance_policy_interface_revision_validates_offline() -> None:
    assert load_validator().validate() == {
        "cases": 2,
        "minimum_cases": 1,
        "new_tests_passed": 15,
        "old_tests_failed": 4,
        "repositories": 1,
    }


def test_registry_pins_formal_search_and_independent_history() -> None:
    registry = json.loads((STUDY_ROOT / "sources" / "registry.json").read_text())
    assert registry["repository"] == "https://github.com/microsoft/agent-governance-toolkit"
    assert registry["old_commit"] == "577627921d1615af6a8f40db551106ee5a1c8759"
    assert registry["change_commit"] == "e87b74530e1cbae54d5e90bc1b45ecf5c8911b28"
    assert registry["formal_search_query"] == "openai opa in:name,description,readme"
    assert registry["formal_search_rank"] == 7
    assert registry["license"] == "MIT"


def test_action_mapping_is_explicitly_author_defined() -> None:
    cases = json.loads((STUDY_ROOT / "cases.json").read_text())
    receipt = json.loads((STUDY_ROOT / "source-validation-receipt.json").read_text())
    assert cases["human_annotators"] == 0
    assert cases["model_calls"] == 0
    assert "Author mapping" in cases["action_mapping"]
    assert receipt["action_mapping_is_author_mapping"] is True
