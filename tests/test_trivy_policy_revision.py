from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "trivy-policy-revision-v1"


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_trivy_policy_revision.py"
    spec = importlib.util.spec_from_file_location("validate_trivy_policy_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trivy_policy_revision_validates_offline() -> None:
    assert load_validator().validate() == {
        "cases": 4,
        "minimum_cases": 2,
        "repositories": 1,
        "transitions": {"ALLOW->HOLD": 2, "HOLD->ALLOW": 2},
        "upstream_regression_fixtures": 4,
    }


def test_trivy_registry_pins_independent_history() -> None:
    registry = json.loads((STUDY_ROOT / "sources" / "registry.json").read_text())
    assert registry["repository"] == "https://github.com/aquasecurity/trivy-checks"
    assert registry["old_commit"] == "f37551204c6c6e731ccdc0b5ade0a74cf3f556b1"
    assert registry["change_commit"] == "e4defae1e4c6e346104f41e70489503069ad1b90"
    assert registry["license"] == "MIT"
    assert len(registry["upstream_test_names"]) == 4


def test_trivy_cases_are_all_upstream_regression_semantics() -> None:
    payload = json.loads((STUDY_ROOT / "cases.json").read_text())
    assert {row["origin"] for row in payload["cases"]} == {"UPSTREAM_REGRESSION_TEST_SEMANTICS"}
    assert payload["model_calls"] == 0
