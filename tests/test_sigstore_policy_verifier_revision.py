from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "sigstore-policy-verifier-revision-v1"


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_sigstore_policy_verifier_revision.py"
    spec = importlib.util.spec_from_file_location(
        "validate_sigstore_policy_verifier_revision", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sigstore_fault_addendum_validates_offline() -> None:
    assert load_validator().validate() == {
        "cases": 6,
        "minimum_cases": 4,
        "repositories": 1,
        "transitions": {"ALLOW->HOLD": 4, "HOLD->ALLOW": 2},
        "upstream_regression_fixtures": 2,
    }


def test_sigstore_registry_pins_independent_history() -> None:
    registry = json.loads((STUDY_ROOT / "sources" / "registry.json").read_text(encoding="utf-8"))
    assert registry["repository"] == "https://github.com/sigstore/cosign"
    assert registry["old_commit"] == "0c26fba3492cd6047fbfecbad622c9c2782fb16a"
    assert registry["change_commit"] == "3b597b999ad083afd2ce0dba68fa2715ddec0f06"
    assert registry["license"] == "Apache-2.0"
    assert len(registry["upstream_test_names"]) == 2
    assert registry["test_source"].endswith("sources/rego_test.go")


def test_upstream_and_author_extensions_are_separated() -> None:
    payload = json.loads((STUDY_ROOT / "cases.json").read_text(encoding="utf-8"))
    origins = [row["origin"] for row in payload["cases"]]
    assert origins.count("UPSTREAM_REGRESSION_TEST_SEMANTICS") == 2
    assert origins.count("UPSTREAM_COMMIT_MESSAGE_FAILURE_MODE") == 1
    assert origins.count("AUTHOR_VARIANT_OF_DOCUMENTED_FAILURE_MODE") == 1
    assert origins.count("AUTHOR_CONTRAST_FOR_CHANGED_QUERY") == 2
    assert payload["model_calls"] == 0
