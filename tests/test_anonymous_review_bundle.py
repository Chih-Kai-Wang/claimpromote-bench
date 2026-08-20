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


def test_identity_scan_checks_searchable_filename(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "run-3634ce8.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="filename contains"):
        builder.scan_identity(tmp_path)


def test_identity_scan_rejects_embedded_api_credential(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "notes.txt").write_text(
        "temporary=sk-proj-abcdefghijklmnopqrstuvwxyz0123456789\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="possible OpenAI-style secret"):
        builder.scan_identity(tmp_path)


def test_empirical_copy_anonymizes_searchable_filename(tmp_path: Path) -> None:
    builder = load_builder()
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    (source / "run-3634ce8.json").write_text("{}\n", encoding="utf-8")

    builder.copy_anonymized_tree(source, destination)

    assert (destination / "run-anonymous-followup-plan-b.json").is_file()


def test_empirical_provenance_anonymizer_preserves_payload() -> None:
    builder = load_builder()
    source = {
        "github_run_id": 32405565039,
        "frozen_plan_commit": "b86ee1e1d28db8a390344d28582af88e26970560",
        "raw_response_text": '{"action":"ALLOW"}',
        "nested": [
            "github.com/f0909172434/project",
            99,
            "/home/runner/work/claimpromote-bench/claimpromote-bench/work/result.json",
        ],
    }
    cleaned = builder.anonymize_provenance(source)
    rendered = json.dumps(cleaned, sort_keys=True)

    assert cleaned["github_run_id"] == "anonymous-capable-final-qualified-run"
    assert cleaned["frozen_plan_commit"] == "0000000000000000000000000000000000000002"
    assert cleaned["raw_response_text"] == source["raw_response_text"]
    assert cleaned["nested"][1] == 99
    assert cleaned["nested"][2] == "/anonymous/workspace/work/result.json"
    assert "f0909172434" not in rendered
    assert "b86ee1e1d28db8a390344d28582af88e26970560" not in rendered


def test_capable_anonymous_evidence_rebinds_changed_file_digests(tmp_path: Path) -> None:
    builder = load_builder()
    runs = tmp_path / "canonical" / "runs"
    analyses = tmp_path / "canonical" / "analysis"
    runs.mkdir(parents=True)
    analyses.mkdir(parents=True)
    run_path = runs / "lane-a-pilot.jsonl"
    run_path.write_text(
        json.dumps({"lane_id": "lane-a", "phase": "pilot", "item_id": "item-a"}) + "\n",
        encoding="utf-8",
    )
    analysis_path = analyses / "lane-a-pilot.json"
    analysis_path.write_text(
        json.dumps({"lane_id": "lane-a", "phase": "pilot", "run_sha256": "stale"}),
        encoding="utf-8",
    )
    (tmp_path / "aggregate.json").write_text(
        json.dumps(
            {
                "qualification": {"pilots": [{"lane_id": "lane-a", "run_sha256": "stale"}]},
                "models_with_complete_hidden_pass": [],
                "provenance": {
                    "pilot_run_sha256": {"lane-a": "stale"},
                    "full_run_sha256": {},
                    "pilot_analysis_sha256": {"lane-a": "stale"},
                    "full_analysis_sha256": {},
                },
            }
        ),
        encoding="utf-8",
    )

    builder.repair_capable_anonymous_evidence(tmp_path)

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    aggregate = json.loads((tmp_path / "aggregate.json").read_text(encoding="utf-8"))
    assert analysis["run_sha256"] == builder.sha256_file(run_path)
    assert aggregate["qualification"]["pilots"][0]["run_sha256"] == builder.sha256_file(run_path)
    assert aggregate["provenance"]["pilot_analysis_sha256"]["lane-a"] == (
        builder.sha256_file(analysis_path)
    )


def test_noncanonical_attempt_history_is_excluded() -> None:
    builder = load_builder()

    assert builder.should_skip(Path("attempt-history/old-run.jsonl"))


def test_review_runner_prefers_the_bundled_source_tree() -> None:
    builder = load_builder()

    runner = builder.review_runner()
    assert 'package_root = str(ROOT / "src")' in runner
    assert 'env["PYTHONPATH"]' in runner
    assert "subprocess.run(command, cwd=ROOT, check=True, env=env)" in runner


def test_iclr_bundle_description_matches_item_level_hidden_release() -> None:
    submission_builder = load_submission_builder()

    statement = submission_builder.ICLR_REPRODUCIBILITY
    assert "recovery checks" not in statement
    assert "item-level" in statement
    assert "The private construction seed is excluded" in statement
    assert "public preprint" not in statement


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
