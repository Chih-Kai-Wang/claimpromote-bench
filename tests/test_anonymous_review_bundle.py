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


def test_identity_scan_rejects_provider_account_identifier(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "failure.jsonl").write_text(
        '{"transport_error":"account user_Aa1234567890Bb1234567890Cc1"}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="possible provider account identifier"):
        builder.scan_identity(tmp_path)


def test_sensitive_scan_rejects_provider_response_identifier(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "record.json").write_text(
        '{"provider_response_id":"msg_977a9766-548a-49f3-9193-af73ce878e67"}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="retained provider_response_id"):
        builder.scan_sensitive_payloads(tmp_path)


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
        "fresh_confirmatory_run_id": 32453310192,
        "frozen_plan_commit": "b86ee1e1d28db8a390344d28582af88e26970560",
        "fresh_confirmatory_commit": "f44b01eb97418d87aa6d7486fa785c0f49b9dda2",
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
    assert cleaned["fresh_confirmatory_run_id"] == "anonymous-fresh-confirmatory-run"
    assert cleaned["frozen_plan_commit"] == "0000000000000000000000000000000000000002"
    assert cleaned["fresh_confirmatory_commit"] == "0000000000000000000000000000000000000008"
    assert cleaned["raw_response_text"] == source["raw_response_text"]
    assert cleaned["nested"][1] == 99
    assert cleaned["nested"][2] == "/anonymous/workspace/work/result.json"
    assert "f0909172434" not in rendered
    assert "b86ee1e1d28db8a390344d28582af88e26970560" not in rendered
    assert "f44b01eb97418d87aa6d7486fa785c0f49b9dda2" not in rendered


def test_empirical_provenance_anonymizer_redacts_provider_account_identifier() -> None:
    builder = load_builder()
    account_identifier = "user_Aa1234567890Bb1234567890Cc1"
    source = {
        "parse_error_detail": f'provider payload: {{"user_id":"{account_identifier}"}}',
        "transport_error": f"request rejected for {account_identifier}",
        "legitimate_control": "user_id and user-visible text remain intact",
    }

    cleaned = builder.anonymize_provenance(source)
    rendered = json.dumps(cleaned, sort_keys=True)

    assert account_identifier not in rendered
    assert cleaned["parse_error_detail"].count("anonymous-provider-account") == 1
    assert cleaned["transport_error"].count("anonymous-provider-account") == 1
    assert cleaned["legitimate_control"] == source["legitimate_control"]


def test_empirical_provenance_anonymizer_removes_provider_ids_and_hidden_reasoning() -> None:
    builder = load_builder()
    source = {
        "provider_response_id": "provider-id-must-not-survive",
        "provider_request_id": "provider-request-must-not-survive",
        "reasoning_content": "private chain of thought",
        "raw_response_text": '{"action":"ALLOW"}',
    }

    cleaned = builder.anonymize_provenance(source)

    assert cleaned["provider_response_id"] is None
    assert cleaned["provider_request_id"] is None
    assert "reasoning_content" not in cleaned
    assert cleaned["raw_response_text"] == source["raw_response_text"]


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
    for index in range(16):
        phase = "pilot" if index < 14 else "full"
        attempt = tmp_path / "attempt-history" / f"attempt-{index:02d}"
        attempt_runs = attempt / "runs"
        attempt_analyses = attempt / "analysis"
        attempt_runs.mkdir(parents=True)
        attempt_analyses.mkdir(parents=True)
        attempt_run = attempt_runs / f"lane-{index}-{phase}.jsonl"
        row = (
            {"lane_id": "lane-a", "phase": "pilot", "item_id": "item-a"}
            if index == 0
            else {"lane_id": f"lane-{index}", "phase": phase, "item_id": "item-a"}
        )
        attempt_run.write_text(json.dumps(row) + "\n", encoding="utf-8")
        (attempt_analyses / f"lane-{index}-{phase}.json").write_text(
            json.dumps({"lane_id": row["lane_id"], "phase": phase, "run_sha256": "stale"}),
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


def test_noncanonical_attempt_history_is_retained() -> None:
    builder = load_builder()

    assert not builder.should_skip(Path("attempt-history/old-run.jsonl"))


def test_review_runner_prefers_the_bundled_source_tree() -> None:
    builder = load_builder()

    runner = builder.review_runner()
    assert 'package_root = str(ROOT / "src")' in runner
    assert 'env["PYTHONPATH"]' in runner
    assert "subprocess.run(command, cwd=ROOT, check=True, env=env)" in runner


def test_review_runner_checks_frozen_naturalistic_decision() -> None:
    builder = load_builder()

    runner = builder.review_runner()
    readme = builder.review_readme()
    assert "scripts/validate_v2_naturalistic_candidates.py" in runner
    assert "tests/test_v2_naturalistic.py" in runner
    normalized = " ".join(readme.split())
    assert "zero benchmark cases" in normalized
    assert "zero model calls" in normalized
    assert "no human annotators" in normalized


def test_iclr_bundle_description_matches_item_level_hidden_release() -> None:
    submission_builder = load_submission_builder()

    statement = submission_builder.ICLR_REPRODUCIBILITY
    normalized = " ".join(statement.split())
    assert "recovery checks" not in statement
    assert "item-level" in statement
    assert "exactly 27 cross-field-invalid" in normalized
    assert "C2 seals all 600 terminal cells" in normalized
    assert "275 response envelopes" in normalized
    assert "byte-identical scientific analysis" in normalized
    assert "manifest records the generated tree's current file count" in normalized
    assert "receipt validates all 360 item-level records" in normalized
    assert "retained provider response identifiers" in normalized
    assert "both registered lane dispositions" in normalized
    assert "all 14 pilot attempts" in normalized
    assert "The private construction seed is excluded" in normalized
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


def test_fresh_confirmatory_anonymous_projection_is_compact_and_identity_free(
    tmp_path: Path,
) -> None:
    builder = load_builder()
    source = ROOT / "release" / "reviewer-evidence-source" / "fresh-confirmatory"
    destination = tmp_path / "fresh-confirmatory"

    builder.build_fresh_confirmatory_anonymous_evidence(source, destination)

    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))
    addendum = json.loads((destination / "reporting-addendum.json").read_text(encoding="utf-8"))
    qwen_path = destination / manifest["lane_files"]["opencode-go-qwen3.7-max"]
    qwen = [json.loads(line) for line in qwen_path.read_text(encoding="utf-8").splitlines()]
    rendered = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in destination.rglob("*")
        if path.is_file()
    )
    assert len(qwen) == 300
    assert sum(row["parse_status"] == "OK" for row in qwen) == 272
    assert all("sanitized_provider_envelope" not in row for row in qwen)
    assert all("frozen_plan_commit" not in row for row in qwen)
    assert addendum["qwen_service_configuration"]["complete_pairs"] == 123
    assert addendum["qwen_service_configuration"]["correct_pairs"] == 113
    assert len(addendum["qwen_service_configuration"]["factor_metrics"]) == 20
    assert {
        factor["factor_id"]
        for factor in addendum["qwen_service_configuration"]["factor_metrics"]
        if factor["end_to_end_pair_accuracy"] == 0
    } == {"current_binding", "dependency_statement"}
    assert addendum["deterministic_policy_executor"]["correct_items"] == 300
    assert addendum["sources"] == {
        "anonymous_recomputation": (
            "Recomputed from dataset/, runs/, and reported-analysis.json in this directory."
        ),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
    }
    assert "32453310192" not in rendered
    assert "f44b01eb97418d87aa6d7486fa785c0f49b9dda2" not in rendered
    assert '"thinking":' not in rendered


def test_balanced_public_anonymous_projection_is_replayable_and_identity_free(
    tmp_path: Path,
) -> None:
    builder = load_builder()
    destination = tmp_path / "balanced-public-challenge"

    builder.build_balanced_public_anonymous_evidence(destination)

    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))
    aggregate = json.loads((destination / "reported-aggregate.json").read_text(encoding="utf-8"))
    correction = json.loads(
        (destination / "reporting-correction-review.json").read_text(encoding="utf-8")
    )
    receipt = json.loads((destination / "privacy-receipt-review.json").read_text(encoding="utf-8"))
    qwen_path = destination / manifest["lane_files"]["opencode-go-qwen3.7-max"]
    flash_path = destination / manifest["lane_files"]["opencode-go-deepseek-v4-flash-matched"]
    qwen = [json.loads(line) for line in qwen_path.read_text(encoding="utf-8").splitlines()]
    flash = [json.loads(line) for line in flash_path.read_text(encoding="utf-8").splitlines()]
    actual_files = [
        path for path in destination.rglob("*") if path.is_file() and path.name != "MANIFEST.json"
    ]
    rendered = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in destination.rglob("*")
        if path.is_file()
    )

    assert manifest["file_count"] == len(actual_files) == len(manifest["files"])
    assert len(qwen) == len(flash) == 180
    assert sum(row["parse_status"] == "OK" for row in qwen) == 148
    assert sum(row["parse_status"] == "OK" for row in flash) == 146
    assert all(row["provider_response_id"] is None for row in qwen + flash)
    lane_metrics = {row["lane_id"]: row["metrics"] for row in aggregate["lanes"]}
    assert lane_metrics["opencode-go-qwen3.7-max"]["correct_pairs"] == 48
    flash_metrics = lane_metrics["opencode-go-deepseek-v4-flash-matched"]
    assert flash_metrics["correct_pairs"] == 13
    assert flash_metrics["macro_f1"] == 0.39275710284113646
    assert flash_metrics["conditional_macro_f1"] == 0.46822747216138244
    assert flash_metrics["per_action"]["DEMOTE"]["precision"] == 0.0
    assert correction["status"] == "REPORTING_CORRECTION"
    assert correction["metric_convention"] == (
        "FIXED_FOUR_CLASS_MACRO_F1_WITH_ZERO_DIVISION_EQUAL_TO_ZERO"
    )
    assert correction["scope"]["model_calls_performed"] == 0
    assert correction["scope"]["primary_endpoints_changed"] is False
    assert correction["anonymous_run_sha256"] == {
        "opencode-go-deepseek-v4-flash-matched": builder.sha256_file(flash_path),
        "opencode-go-qwen3.7-max": builder.sha256_file(qwen_path),
    }
    assert receipt["validation"]["terminal_records_validated"] == 360
    assert receipt["validation"]["retained_provider_response_ids"] == 0
    assert "f0909172434" not in rendered
    assert "32509532820" not in rendered
    assert "9460301513" not in rendered
    assert "1901e471bdf94f434f9671708b93599a106b1543" not in rendered
    assert "8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b" not in rendered
    builder.scan_identity(destination)
    builder.scan_sensitive_payloads(destination)
