from __future__ import annotations

import importlib.util
import json
import shutil
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
            "/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/work/result.json",
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
    assert cleaned["nested"][3] == "/anonymous/workspace/work/result.json"
    assert "f0909172434" not in rendered
    assert "b86ee1e1d28db8a390344d28582af88e26970560" not in rendered
    assert "f44b01eb97418d87aa6d7486fa785c0f49b9dda2" not in rendered
    assert "wangzhikai" not in rendered


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


def test_review_readme_describes_validation_without_claiming_a_rebuild() -> None:
    builder = load_builder()

    readme = builder.review_readme()
    assert "validate the public alpha benchmark" in readme
    assert "rebuild and validate" not in readme
    assert "1,260" not in readme
    assert "subscription quota" in readme
    assert "excluded in full" in readme
    assert "seven-route" not in readme


def test_paper_empirical_projection_contains_only_retained_studies() -> None:
    builder = load_builder()

    validator = builder.paper_empirical_validator()
    balanced = builder.paper_balanced_analyzer()
    compile(validator, "validate_anonymous_empirical_evidence.py", "exec")
    compile(balanced, "analyze_balanced_public_challenge.py", "exec")

    assert "def validate_fresh_confirmatory" in validator
    assert "def validate_balanced_public_challenge" in validator
    assert "def validate_slsa_portability" in validator
    assert "def validate_local_model_replications" in validator
    assert "def validate_synthetic_policy_evidence" in validator
    assert '"policy_switch": validate_policy_switch()' not in validator
    assert "def validate_capable_hidden" not in validator
    assert "def validate_public_model_breadth" not in validator
    assert "def validate_v1_" not in validator
    assert "aggregate_capable_hidden_study" not in validator
    assert "analyze_stronger_model_study" not in validator + balanced
    assert "def derive_reporting_metrics" in balanced


def test_slsa_anonymous_projection_redacts_schema_identity_and_rebinds_receipts(
    tmp_path: Path,
) -> None:
    builder = load_builder()
    destination = tmp_path / "slsa-portability"

    builder.build_slsa_portability_anonymous_evidence(destination)
    builder.scan_identity(destination)
    builder.scan_sensitive_payloads(destination)

    packet = json.loads(
        (destination / "dataset" / "evaluation-prompt-packet.json").read_text(encoding="utf-8")
    )
    schedule = json.loads((destination / "request-schedule.json").read_text(encoding="utf-8"))
    privacy = json.loads((destination / "privacy-receipt-review.json").read_text(encoding="utf-8"))
    result = json.loads((destination / "result-receipt-review.json").read_text(encoding="utf-8"))

    assert len(packet["records"]) == 120
    assert all("anonymous.invalid/repository" in row["prompt"] for row in packet["records"])
    assert all("github.com/f0909172434" not in row["prompt"] for row in packet["records"])
    assert all(
        cell["request_digest_scope"] == "ANONYMOUS_LANE_ITEM_PROMPT_PROJECTION"
        for cell in schedule["cells"]
    )
    assert privacy["status"] == "ANONYMOUS_SYNTHETIC_POLICY_DERIVATIVE_VALIDATED"
    assert result["status"] == "ANONYMOUS_SYNTHETIC_POLICY_RESULTS_SEALED"


def test_hosted_policy_switch_exclusion_receipt_contains_no_selected_rows(tmp_path: Path) -> None:
    builder = load_builder()
    destination = tmp_path / "hosted-policy-switch-exclusion.json"
    builder.build_hosted_policy_switch_exclusion_receipt(destination)
    receipt = json.loads(destination.read_text(encoding="utf-8"))
    assert receipt["status"] == ("HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION")
    assert receipt["decision"]["hosted_model_rows_enter_manuscript"] is False
    assert receipt["decision"]["successful_row_subset_selected"] is False
    assert receipt["raw_terminal_records_included"] is False
    assert receipt["valid_output_subset_included"] is False
    assert receipt["source_bindings_included"] is False


def test_hosted_policy_switch_replacement_exclusion_contains_no_selected_rows(
    tmp_path: Path,
) -> None:
    builder = load_builder()
    destination = tmp_path / "hosted-policy-switch-replacement-exclusion.json"
    builder.build_hosted_policy_switch_replacement_exclusion_receipt(destination)
    receipt = json.loads(destination.read_text(encoding="utf-8"))
    assert receipt["status"] == (
        "HOSTED_REPLACEMENT_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
    )
    assert receipt["classification"]["explicit_resource_exhaustion_errors"] == 240
    assert receipt["decision"]["all_240_terminal_outcomes_considered"] is True
    assert receipt["decision"]["hosted_model_rows_enter_manuscript"] is False
    assert receipt["decision"]["conditional_success_subset_selected"] is False
    assert receipt["raw_terminal_records_included"] is False
    assert receipt["free_form_error_text_included"] is False
    assert receipt["valid_output_subset_included"] is False
    assert receipt["source_bindings_included"] is False


def test_local_void_attempt_projects_only_a_redacted_exclusion_receipt(tmp_path: Path) -> None:
    builder = load_builder()
    destination = tmp_path / "initial-void-exclusion.json"
    source = ROOT / "v2" / "local-model-replication-v1"
    builder.build_local_void_exclusion_receipt(source, destination)
    receipt = json.loads(destination.read_text(encoding="utf-8"))
    assert receipt["status"] == "INELIGIBLE_LOCAL_ATTEMPT_PRE_TERMINAL_SCHEMA_REJECTION"
    assert receipt["observed_counts"]["application_invocations"] == 1
    assert receipt["observed_counts"]["durable_terminal_records"] == 0
    assert receipt["observed_counts"]["retained_model_outputs"] == 0
    assert receipt["source_bindings_included"] is False
    assert receipt["raw_generation_text_included"] is False
    assert receipt["model_outcome_included"] is False


def test_submission_wrappers_preserve_canonical_reproducibility_disclosure() -> None:
    submission_builder = load_submission_builder()

    body = submission_builder.canonical_body()
    reproducibility_start = body.index(r"\section{Reproducibility Statement}")
    conclusion_start = body.index(r"\section{Conclusion}", reproducibility_start)
    canonical_tail = body[reproducibility_start:conclusion_start]

    assert "binds policies, source standards, generators" in canonical_tail
    assert "manifest derives file counts from the generated tree" in canonical_tail
    assert "Generative AI tools assisted" in canonical_tail
    assert "all 14 pilot attempts" not in canonical_tail
    assert canonical_tail in submission_builder.iclr_tex(body)
    assert canonical_tail in submission_builder.arxiv_tex(body)


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


def test_public_model_breadth_projection_drops_private_text_and_rebinds_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = load_builder()
    fake_root = tmp_path / "source-root"
    study = fake_root / "v2" / "public-model-breadth-v1"
    results = study / "results"
    results.mkdir(parents=True)
    for name in ("study-plan.json", "request-schedule.json", "catalog-snapshot.json"):
        source = ROOT / "v2" / "public-model-breadth-v1" / name
        target = study / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    plan = json.loads((study / "study-plan.json").read_text(encoding="utf-8"))
    lane_order = plan["execution"]["base_lane_order"]
    lane_files: dict[str, str] = {}
    aggregate_lanes = []
    lane_output_sha256: dict[str, str] = {}
    frozen_commit = "e3823dbc2df2ac596df43ee4d6c3b5fb2ff16516"
    for lane_id in lane_order:
        path = results / "runs" / f"{lane_id}.jsonl"
        rows = [
            {
                "frozen_plan_commit": frozen_commit,
                "item_id": f"item-{index:03d}",
                "lane_id": lane_id,
                "parse_error_detail": None,
                "provider_response_id": None,
                "raw_response_text": None,
                "system_fingerprint": None,
                "transport_error": None,
            }
            for index in range(180)
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(f"{builder.canonical_json(row)}\n" for row in rows),
            encoding="utf-8",
        )
        lane_files[lane_id] = path.relative_to(results).as_posix()
        lane_output_sha256[path.name] = builder.sha256_file(path)
        aggregate_lanes.append(
            {"lane_id": lane_id, "metrics": {"parseable_items": 0}, "run_sha256": "source"}
        )

    builder.write_json(
        results / "reported-aggregate.json",
        {
            "external_commitment": {"frozen_plan_commit": frozen_commit},
            "lanes": aggregate_lanes,
            "scope_limits": {},
            "service_comparison": {},
        },
    )
    builder.write_json(
        results / "execution-receipt.json",
        {
            "frozen_plan_commit": frozen_commit,
            "lane_output_sha256": lane_output_sha256,
            "request_intent_journal_sha256": "sha256:private-intents",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "terminal_journal_sha256": "sha256:private-terminals",
        },
    )
    builder.write_json(
        results / "failure-cause-addendum.json",
        {
            "status": "POST_RUN_FROZEN_LOG_AUDIT_COMPLETE",
            "transport_failures": 630,
            "transport_failure_categories": {
                "AUTHORIZATION": 76,
                "CONNECTION": 1,
                "QUOTA_RATE_LIMIT": 547,
                "SERVER": 5,
                "TIMEOUT": 1,
            },
            "quota_cutoff": {"cells": 547, "contiguous_schedule_tail": True},
            "privacy": {"raw_error_text_included": False},
            "interpretation_boundary": {
                "route_reliability_comparison_supported": False,
                "model_family_ranking_supported": False,
            },
        },
    )
    source_files = {
        path.relative_to(results).as_posix(): builder.sha256_file(path)
        for path in sorted(results.rglob("*"))
        if path.is_file() and path.name != "failure-cause-addendum.json"
    }
    builder.write_json(
        results / "privacy-receipt.json",
        {
            "credentials_included": False,
            "derived_files_sha256": source_files,
            "free_form_error_detail_included": False,
            "hidden_reasoning_fields_included": False,
            "provider_response_identifiers_included": False,
            "public_lane_files": lane_files,
            "raw_final_response_text_included": False,
            "status": "POST_EXECUTION_PUBLIC_SAFE_DERIVATIVE",
            "terminal_records_validated": 1260,
        },
    )

    monkeypatch.setattr(builder, "ROOT", fake_root)
    destination = tmp_path / "anonymous-breadth"
    builder.build_public_model_breadth_anonymous_evidence(destination)

    rendered = "\n".join(
        path.read_text(encoding="utf-8") for path in destination.rglob("*") if path.is_file()
    )
    row_map = [
        json.loads(line)
        for line in (destination / "review-row-hashes.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    execution = json.loads(
        (destination / "execution-receipt-review.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))
    catalog = json.loads((destination / "catalog-snapshot.json").read_text(encoding="utf-8"))

    assert frozen_commit not in rendered
    assert "0000000000000000000000000000000000000009" in rendered
    assert len(row_map) == 1260
    assert all("source_row_sha256" not in row for row in row_map)
    assert execution["source_journal_digests_included"] is False
    assert "request_intent_journal_sha256" not in execution
    assert manifest["file_count"] == len(manifest["files"])
    assert catalog["model_count"] == len(catalog["model_ids"]) == 29
    assert len(catalog["selected_model_ids"]) == 7
    assert set(catalog["selected_model_ids"]) <= set(catalog["model_ids"])
    builder.scan_identity(destination)
    builder.scan_sensitive_payloads(destination)
