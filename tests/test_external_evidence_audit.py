from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_external_evidence_audit.py"
    spec = importlib.util.spec_from_file_location("validate_external_evidence_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_evidence_audit_validates_offline() -> None:
    assert load_validator().validate() == {
        "architecture_only": 6,
        "code_seeds": 10,
        "model_calls": 0,
        "qualifying_revisions": 2,
        "repository_seeds": 465,
        "source_level_reviewed": 11,
    }
