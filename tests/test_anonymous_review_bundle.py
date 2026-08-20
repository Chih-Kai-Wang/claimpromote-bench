from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_anonymous_review_bundle.py"
SUBMISSION_BUILDER_PATH = ROOT / "scripts" / "build_submission_tex.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("anonymous_bundle_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_submission_builder():
    spec = importlib.util.spec_from_file_location("submission_builder", SUBMISSION_BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_anonymous_license_replaces_named_notice() -> None:
    builder = load_builder()
    license_text = builder.anonymous_license()

    assert "Copyright (c) 2026 Anonymous Authors" in license_text
    assert "Chih-Kai Wang" not in license_text


def test_identity_scan_checks_extensionless_license(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "LICENSE").write_text(
        "MIT License\n\nCopyright (c) 2026 Chih-Kai Wang\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit, match="identity/provenance leak detected"):
        builder.scan_identity(tmp_path)


def test_iclr_bundle_description_does_not_claim_hidden_recovery_checks() -> None:
    submission_builder = load_submission_builder()

    statement = submission_builder.ICLR_REPRODUCIBILITY
    assert "recovery checks" not in statement
    assert "Hidden inference and recovery provenance remain outside that bundle" in statement


def test_stronger_followup_anonymization_keeps_metrics_and_removes_provenance() -> None:
    builder = load_builder()
    source = builder.load_object(
        ROOT / "v2" / "stronger-model-results" / "openrouter-openai-gpt-5.4-v2-study.json"
    )
    cleaned = builder.anonymize_stronger_results(source)
    rendered = json.dumps(cleaned, sort_keys=True)

    assert cleaned["full"]["parseable_decisions"] == 99
    assert cleaned["full"]["raw_correct_pairs"] == 49
    assert cleaned["full"]["routed_provider_values"] == ["OpenAI"]
    assert "3634ce85785e9b516abc519711fff12388307331" not in rendered
    assert "0054a4d73bdbd81e0ba31871ab4e51140ebf5f2421feda7cce40d57639b53ef7" not in rendered
