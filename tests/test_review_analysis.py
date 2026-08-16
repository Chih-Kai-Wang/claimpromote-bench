from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.review import prepare_review_package
from claimpromotebench.review_analysis import (
    ADJUDICATION_FILENAME,
    REPORT_FILENAME,
    analyze_review_package,
    evaluate_final_gate,
    initialize_adjudication,
    main,
    validate_adjudication,
    validate_analysis_package,
    validate_analysis_root,
)

SECRET = bytes.fromhex("22" * 32)


def _load_object(path: Path) -> dict[str, Any]:
    value = load_json(path)
    assert isinstance(value, dict)
    return value


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _mapping(package_dir: Path) -> dict[str, str]:
    key = _load_object(package_dir / "private-key.json")
    return {str(value["review_item_id"]): str(value["item_id"]) for value in key["mapping"]}


def _gold(dataset_dir: Path) -> dict[str, dict[str, Any]]:
    return {str(record["id"]): record for record in load_jsonl(dataset_dir / "gold.jsonl")}


def _write_submission(
    dataset_dir: Path,
    package_dir: Path,
    reviewer_id: str,
    *,
    mutations: dict[str, tuple[str, list[str]]] | None = None,
) -> Path:
    manifest = _load_object(package_dir / "packet-manifest.json")
    mapping = _mapping(package_dir)
    gold = _gold(dataset_dir)
    changes = mutations or {}
    decisions: list[dict[str, Any]] = []
    for review_item_id, item_id in sorted(mapping.items()):
        expected = gold[item_id]["decision"]
        action, reasons = changes.get(
            item_id,
            (str(expected["action"]), list(expected["reason_codes"])),
        )
        decisions.append(
            {
                "review_item_id": review_item_id,
                "action": action,
                "reason_codes": reasons,
                "confidence": 4,
                "rationale": "Synthetic test judgment; not an external review.",
            }
        )
    submission = {
        "schema_version": "1.0.0",
        "reviewer_id": reviewer_id,
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "completed_at": "2026-08-16T14:00:00+08:00",
        "attestation": {
            "independent": True,
            "no_gold_access": True,
            "no_model_outputs": True,
            "no_collaboration": True,
            "public_release_after_unblinding": True,
        },
        "decisions": decisions,
    }
    path = package_dir / "submissions" / f"{reviewer_id}.json"
    _write_object(path, submission)
    return path


def _prepare_two_reviewer_package(
    dataset_dir: Path,
    tmp_path: Path,
    *,
    package_name: str = "package",
    second_mutations: dict[str, tuple[str, list[str]]] | None = None,
) -> Path:
    package = tmp_path / package_name
    prepare_review_package(dataset_dir, package, secret=SECRET)
    _write_submission(dataset_dir, package, "reviewer-one")
    _write_submission(
        dataset_dir,
        package,
        "reviewer-two",
        mutations=second_mutations,
    )
    return package


def _one_allow_item(dataset_dir: Path) -> str:
    gold = _gold(dataset_dir)
    return next(
        item_id for item_id, value in sorted(gold.items()) if value["decision"]["action"] == "ALLOW"
    )


def _low_agreement_mutations(dataset_dir: Path) -> dict[str, tuple[str, list[str]]]:
    gold = _gold(dataset_dir)
    allow_items = [
        item_id for item_id, value in sorted(gold.items()) if value["decision"]["action"] == "ALLOW"
    ]
    return {item_id: ("HOLD", ["MISSING_DEPENDENCY"]) for item_id in allow_items[:10]}


def _write_adjudication(
    report: dict[str, Any],
    path: Path,
    disposition: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for disagreement in report["disagreements"]:
        if disposition == "UNRESOLVED":
            action = None
            reasons: list[str] = []
        else:
            action = str(disagreement["gold_action"])
            reasons = list(disagreement["gold_reason_codes"])
        entries.append(
            {
                "disagreement_id": disagreement["disagreement_id"],
                "disposition": disposition,
                "recommended_action": action,
                "recommended_reason_codes": reasons,
                "note": f"Synthetic {disposition} test adjudication.",
            }
        )
    value = {
        "schema_version": "1.0.0",
        "analysis_report_id": report["report_id"],
        "packet_id": report["packet_id"],
        "adjudicator_id": "adjudicator-one",
        "completed_at": "2026-08-16T15:00:00+08:00",
        "entries": entries,
    }
    _write_object(path, value)
    return value


def test_perfect_review_report_passes_all_metrics(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = _prepare_two_reviewer_package(dataset_dir, tmp_path)
    report = analyze_review_package(dataset_dir, package)

    assert report["reviewer_count"] == 2
    assert report["item_count"] == 40
    assert report["gate"] == {
        "status": "PASS",
        "reviewer_count_pass": True,
        "per_reviewer_action_agreement_pass": True,
        "pairwise_action_agreement_pass": True,
        "metrics_pass": True,
        "disagreement_count": 0,
    }
    assert all(reviewer["action_agreement_with_gold"] == 1.0 for reviewer in report["reviewers"])
    pairwise = report["inter_reviewer"]["pairwise"]
    assert len(pairwise) == 1
    assert pairwise[0]["raw_action_agreement"] == 1.0
    assert pairwise[0]["cohen_kappa"] == 1.0
    assert report["inter_reviewer"]["fleiss_kappa"] == 1.0
    assert report["disagreements"] == []

    report_path = package / REPORT_FILENAME
    _write_object(report_path, report)
    validated = validate_analysis_package(dataset_dir, package)
    assert validated["status"] == "PASS"
    assert validated["final_gate"]["status"] == "PASS"


def test_single_high_agreement_disagreement_requires_adjudication(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    item_id = _one_allow_item(dataset_dir)
    package = _prepare_two_reviewer_package(
        dataset_dir,
        tmp_path,
        second_mutations={item_id: ("HOLD", ["MISSING_DEPENDENCY"])},
    )
    report = analyze_review_package(dataset_dir, package)
    report_path = package / REPORT_FILENAME
    _write_object(report_path, report)

    assert report["gate"]["metrics_pass"] is True
    assert report["gate"]["status"] == "NEEDS_ADJUDICATION"
    assert report["gate"]["disagreement_count"] == 1
    disagreement = report["disagreements"][0]
    assert set(disagreement["kinds"]) == {
        "GOLD_ACTION",
        "REVIEWER_ACTION",
        "GOLD_REASON_SET",
        "REVIEWER_REASON_SET",
    }
    with pytest.raises(DatasetIntegrityError, match="require adjudication"):
        validate_analysis_package(dataset_dir, package)

    draft_path = tmp_path / "adjudication-draft.json"
    draft_report = initialize_adjudication(report_path, "adjudicator-one", draft_path)
    draft = _load_object(draft_path)
    assert draft_report["status"] == "DRAFT_CREATED"
    assert draft["completed_at"] is None
    assert draft["entries"][0]["disposition"] == "UNRESOLVED"
    assert draft["entries"][0]["note"] == ""

    adjudication_path = package / ADJUDICATION_FILENAME
    _write_adjudication(report, adjudication_path, "KEEP_GOLD")
    validated = validate_adjudication(
        dataset_dir,
        package,
        report_path,
        adjudication_path,
    )
    assert validated["final_gate"]["status"] == "PASS"
    assert validate_analysis_package(dataset_dir, package)["final_gate"]["status"] == "PASS"


def test_revision_and_unresolved_dispositions_control_final_gate(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    item_id = _one_allow_item(dataset_dir)
    package = _prepare_two_reviewer_package(
        dataset_dir,
        tmp_path,
        second_mutations={item_id: ("HOLD", ["MISSING_DEPENDENCY"])},
    )
    report = analyze_review_package(dataset_dir, package)
    report_path = package / REPORT_FILENAME
    adjudication_path = package / ADJUDICATION_FILENAME
    _write_object(report_path, report)

    revision = _write_adjudication(report, adjudication_path, "REVISE_ITEM")
    assert evaluate_final_gate(report, revision)["status"] == "REVISION_REQUIRED"
    assert validate_analysis_package(dataset_dir, package)["final_gate"]["status"] == (
        "REVISION_REQUIRED"
    )

    unresolved = _write_adjudication(report, adjudication_path, "UNRESOLVED")
    assert evaluate_final_gate(report, unresolved)["status"] == "NEEDS_ADJUDICATION"
    assert validate_analysis_package(dataset_dir, package)["final_gate"]["status"] == (
        "NEEDS_ADJUDICATION"
    )


def test_metric_failure_requires_revision_even_after_keep_gold(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = _prepare_two_reviewer_package(
        dataset_dir,
        tmp_path,
        second_mutations=_low_agreement_mutations(dataset_dir),
    )
    report = analyze_review_package(dataset_dir, package)
    report_path = package / REPORT_FILENAME
    adjudication_path = package / ADJUDICATION_FILENAME
    _write_object(report_path, report)
    adjudication = _write_adjudication(report, adjudication_path, "KEEP_GOLD")

    assert report["reviewers"][1]["action_agreement_with_gold"] == 0.75
    assert report["inter_reviewer"]["minimum_pairwise_action_agreement"] == 0.75
    assert report["gate"]["metrics_pass"] is False
    assert report["gate"]["status"] == "REVISION_REQUIRED"
    assert evaluate_final_gate(report, adjudication)["status"] == "REVISION_REQUIRED"
    assert validate_analysis_package(dataset_dir, package)["final_gate"]["status"] == (
        "REVISION_REQUIRED"
    )


def test_report_and_adjudication_tampering_fail_closed(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    item_id = _one_allow_item(dataset_dir)
    package = _prepare_two_reviewer_package(
        dataset_dir,
        tmp_path,
        second_mutations={item_id: ("HOLD", ["MISSING_DEPENDENCY"])},
    )
    report = analyze_review_package(dataset_dir, package)
    report_path = package / REPORT_FILENAME
    adjudication_path = package / ADJUDICATION_FILENAME
    _write_object(report_path, report)
    adjudication = _write_adjudication(report, adjudication_path, "KEEP_GOLD")

    tampered_report = deepcopy(report)
    tampered_report["reviewers"][0]["action_agreement_with_gold"] = 0.5
    _write_object(report_path, tampered_report)
    with pytest.raises(DatasetIntegrityError, match="report_id is stale"):
        validate_analysis_package(dataset_dir, package)
    _write_object(report_path, report)

    missing = deepcopy(adjudication)
    missing["entries"] = []
    _write_object(adjudication_path, missing)
    with pytest.raises(DatasetIntegrityError, match="coverage mismatch"):
        validate_adjudication(dataset_dir, package, report_path, adjudication_path)

    wrong_keep = deepcopy(adjudication)
    wrong_keep["entries"][0]["recommended_action"] = "HOLD"
    wrong_keep["entries"][0]["recommended_reason_codes"] = ["MISSING_DEPENDENCY"]
    _write_object(adjudication_path, wrong_keep)
    with pytest.raises(DatasetIntegrityError, match="KEEP_GOLD"):
        validate_adjudication(dataset_dir, package, report_path, adjudication_path)


def test_published_package_requires_two_reviewers_report_and_exact_adjudication(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    one_reviewer = tmp_path / "one-reviewer"
    prepare_review_package(dataset_dir, one_reviewer, secret=SECRET)
    _write_submission(dataset_dir, one_reviewer, "reviewer-one")
    one_report = analyze_review_package(dataset_dir, one_reviewer)
    _write_object(one_reviewer / REPORT_FILENAME, one_report)
    with pytest.raises(DatasetIntegrityError, match="at least two reviewers"):
        validate_analysis_package(dataset_dir, one_reviewer)

    two_reviewers = _prepare_two_reviewer_package(dataset_dir, tmp_path / "two")
    with pytest.raises(DatasetIntegrityError, match="missing review-report"):
        validate_analysis_package(dataset_dir, two_reviewers)
    report = analyze_review_package(dataset_dir, two_reviewers)
    _write_object(two_reviewers / REPORT_FILENAME, report)
    assert validate_analysis_package(dataset_dir, two_reviewers)["final_gate"]["status"] == "PASS"


def test_analysis_root_preserves_pass_and_revision_required_results(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    reviews_root = tmp_path / "reviews"
    reviews_root.mkdir()
    pending = validate_analysis_root(dataset_dir, reviews_root, allow_empty=True)
    assert pending["status"] == "PENDING"
    assert pending["packages"] == 0

    passing = _prepare_two_reviewer_package(dataset_dir, reviews_root, package_name="passing")
    passing_report = analyze_review_package(dataset_dir, passing)
    _write_object(passing / REPORT_FILENAME, passing_report)

    failing = _prepare_two_reviewer_package(
        dataset_dir,
        reviews_root,
        package_name="revision",
        second_mutations=_low_agreement_mutations(dataset_dir),
    )
    failing_report = analyze_review_package(dataset_dir, failing)
    _write_object(failing / REPORT_FILENAME, failing_report)
    _write_adjudication(failing_report, failing / ADJUDICATION_FILENAME, "KEEP_GOLD")

    result = validate_analysis_root(dataset_dir, reviews_root, allow_empty=False)
    assert result["status"] == "PASS"
    assert result["packages"] == 2
    assert result["gate_counts"]["PASS"] == 1
    assert result["gate_counts"]["REVISION_REQUIRED"] == 1


def test_review_analysis_cli_analyze_and_validate_root(
    dataset_dir: Path,
    tmp_path: Path,
    capsys,
) -> None:
    reviews_root = tmp_path / "reviews"
    package = _prepare_two_reviewer_package(dataset_dir, reviews_root, package_name="package")
    report_path = package / REPORT_FILENAME
    assert (
        main(
            [
                "analyze",
                "--dataset",
                str(dataset_dir),
                "--package",
                str(package),
                "--out",
                str(report_path),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["out"] == str(report_path)
    assert summary["gate"]["status"] == "PASS"

    root_report = tmp_path / "root-report.json"
    assert (
        main(
            [
                "validate-root",
                "--dataset",
                str(dataset_dir),
                "--root",
                str(reviews_root),
                "--out",
                str(root_report),
            ]
        )
        == 0
    )
    root_summary = json.loads(capsys.readouterr().out)
    assert root_summary["status"] == "PASS"
    assert root_summary["out"] == str(root_report)
    assert _load_object(root_report)["gate_counts"]["PASS"] == 1
