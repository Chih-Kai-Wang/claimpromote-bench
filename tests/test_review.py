from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.review import (
    initialize_submission,
    main,
    prepare_review_package,
    validate_review_package,
    validate_review_package_material,
    validate_review_root,
    validate_review_submission,
)

SECRET = bytes.fromhex("11" * 32)


def _load_object(path: Path) -> dict[str, Any]:
    value = load_json(path)
    assert isinstance(value, dict)
    return value


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _complete_submission(
    dataset_dir: Path,
    package_dir: Path,
    reviewer_id: str,
    out_path: Path,
) -> dict[str, Any]:
    manifest = _load_object(package_dir / "packet-manifest.json")
    key = _load_object(package_dir / "private-key.json")
    gold = {record["id"]: record for record in load_jsonl(dataset_dir / "gold.jsonl")}
    mapping = {
        value["review_item_id"]: value["item_id"]
        for value in key["mapping"]
    }
    submission = {
        "schema_version": "1.0.0",
        "reviewer_id": reviewer_id,
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "completed_at": "2026-08-16T12:00:00+08:00",
        "attestation": {
            "independent": True,
            "no_gold_access": True,
            "no_model_outputs": True,
            "no_collaboration": True,
            "public_release_after_unblinding": True,
        },
        "decisions": [],
    }
    for review_item_id in sorted(mapping):
        decision = gold[mapping[review_item_id]]["decision"]
        submission["decisions"].append(
            {
                "review_item_id": review_item_id,
                "action": decision["action"],
                "reason_codes": decision["reason_codes"],
                "confidence": 5,
                "rationale": "Synthetic unit-test record; not an external review.",
            }
        )
    _write_object(out_path, submission)
    return submission


def test_prepare_review_package_is_deterministic_and_blinded(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    report = prepare_review_package(dataset_dir, first, secret=SECRET)
    prepare_review_package(dataset_dir, second, secret=SECRET)

    assert report["status"] == "PREPARED"
    assert report["items"] == 40
    assert (first / "packet.jsonl").read_bytes() == (second / "packet.jsonl").read_bytes()
    assert (first / "packet-manifest.json").read_bytes() == (
        second / "packet-manifest.json"
    ).read_bytes()
    assert (first / "private-key.json").read_bytes() == (
        second / "private-key.json"
    ).read_bytes()

    records = load_jsonl(first / "packet.jsonl")
    assert len(records) == 40
    assert [record["review_item_id"] for record in records] == sorted(
        record["review_item_id"] for record in records
    )
    for record in records:
        payload = record["payload"]
        assert not {"id", "pair_id", "split", "family", "gold"} & set(payload)

    material = validate_review_package_material(dataset_dir, first)
    assert material["status"] == "PASS"
    assert material["items"] == 40


def test_prepare_rejects_nonempty_directory_and_wrong_secret(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "existing.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(DatasetIntegrityError, match="not empty"):
        prepare_review_package(dataset_dir, occupied, secret=SECRET)
    with pytest.raises(DatasetIntegrityError, match="32 bytes"):
        prepare_review_package(dataset_dir, tmp_path / "short", secret=b"short")


def test_initialize_submission_is_unbiased_and_intentionally_incomplete(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    prepare_review_package(dataset_dir, package, secret=SECRET)
    draft_path = tmp_path / "draft.json"
    report = initialize_submission(package, "reviewer-one", draft_path)
    draft = _load_object(draft_path)

    assert report["status"] == "DRAFT_CREATED"
    assert report["items"] == 40
    assert draft["completed_at"] is None
    assert all(value is False for value in draft["attestation"].values())
    assert all(decision["action"] is None for decision in draft["decisions"])
    assert all(decision["confidence"] is None for decision in draft["decisions"])


def test_valid_submission_and_completed_package_pass(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    prepare_review_package(dataset_dir, package, secret=SECRET)
    first_path = package / "submissions" / "reviewer-one.json"
    second_path = package / "submissions" / "reviewer-two.json"
    _complete_submission(dataset_dir, package, "reviewer-one", first_path)
    _complete_submission(dataset_dir, package, "reviewer-two", second_path)

    report = validate_review_submission(dataset_dir, package, first_path)
    assert report["status"] == "PASS"
    assert report["reviewer_id"] == "reviewer-one"
    assert report["decisions"] == 40

    package_report = validate_review_package(dataset_dir, package)
    assert package_report["status"] == "PASS"
    assert package_report["reviewers"] == 2
    assert package_report["items"] == 40


def test_submission_rejects_coverage_reason_and_attestation_failures(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    prepare_review_package(dataset_dir, package, secret=SECRET)
    path = tmp_path / "submission.json"
    base = _complete_submission(dataset_dir, package, "reviewer-one", path)

    missing = deepcopy(base)
    missing["decisions"].pop()
    _write_object(path, missing)
    with pytest.raises(DatasetIntegrityError, match="coverage mismatch"):
        validate_review_submission(dataset_dir, package, path)

    unknown = deepcopy(base)
    unknown["decisions"][0]["reason_codes"] = ["NOT_A_POLICY_REASON"]
    _write_object(path, unknown)
    with pytest.raises(DatasetIntegrityError, match="unknown review reason"):
        validate_review_submission(dataset_dir, package, path)

    invalid_allow = deepcopy(base)
    allow = next(
        decision for decision in invalid_allow["decisions"] if decision["action"] == "ALLOW"
    )
    allow["reason_codes"] = ["MISSING_DEPENDENCY"]
    _write_object(path, invalid_allow)
    with pytest.raises(DatasetIntegrityError, match="POLICY_SATISFIED only"):
        validate_review_submission(dataset_dir, package, path)

    invalid_hold = deepcopy(base)
    hold = next(
        decision for decision in invalid_hold["decisions"] if decision["action"] != "ALLOW"
    )
    hold["reason_codes"] = ["POLICY_SATISFIED"]
    _write_object(path, invalid_hold)
    with pytest.raises(DatasetIntegrityError, match="cannot use POLICY_SATISFIED"):
        validate_review_submission(dataset_dir, package, path)

    unattested = deepcopy(base)
    unattested["attestation"]["no_gold_access"] = False
    _write_object(path, unattested)
    with pytest.raises(DatasetIntegrityError, match="violates schema"):
        validate_review_submission(dataset_dir, package, path)


def test_packet_and_private_mapping_tampering_fail_closed(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    prepare_review_package(dataset_dir, package, secret=SECRET)

    packet_path = package / "packet.jsonl"
    original_packet = packet_path.read_text(encoding="utf-8")
    packet_path.write_text(original_packet + "\n", encoding="utf-8")
    with pytest.raises(DatasetIntegrityError, match="packet hash"):
        validate_review_package_material(dataset_dir, package)
    packet_path.write_text(original_packet, encoding="utf-8")

    key_path = package / "private-key.json"
    key = _load_object(key_path)
    key["mapping"][0]["item_id"] = "alpha-does-not-exist"
    _write_object(key_path, key)
    with pytest.raises(DatasetIntegrityError, match="HMAC"):
        validate_review_package_material(dataset_dir, package)


def test_completed_package_rejects_no_submissions_and_duplicate_reviewer(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    prepare_review_package(dataset_dir, package, secret=SECRET)
    with pytest.raises(DatasetIntegrityError, match="no submissions"):
        validate_review_package(dataset_dir, package)

    _complete_submission(
        dataset_dir,
        package,
        "reviewer-one",
        package / "submissions" / "one.json",
    )
    _complete_submission(
        dataset_dir,
        package,
        "reviewer-one",
        package / "submissions" / "two.json",
    )
    with pytest.raises(DatasetIntegrityError, match="duplicate reviewer"):
        validate_review_package(dataset_dir, package)


def test_review_root_is_pending_when_empty_and_validates_completed_packages(
    dataset_dir: Path,
    tmp_path: Path,
) -> None:
    root = tmp_path / "reviews"
    root.mkdir()
    assert validate_review_root(dataset_dir, root, allow_empty=True) == {
        "status": "PENDING",
        "packages": 0,
        "reviewers": 0,
    }
    with pytest.raises(DatasetIntegrityError, match="no completed package"):
        validate_review_root(dataset_dir, root, allow_empty=False)

    package = root / "alpha-review"
    prepare_review_package(dataset_dir, package, secret=SECRET)
    _complete_submission(
        dataset_dir,
        package,
        "reviewer-one",
        package / "submissions" / "reviewer-one.json",
    )
    report = validate_review_root(dataset_dir, root, allow_empty=False)
    assert report["status"] == "PASS"
    assert report["packages"] == 1
    assert report["reviewers"] == 1


def test_review_cli_prepare_initialize_and_validate_root(
    dataset_dir: Path,
    tmp_path: Path,
    capsys,
) -> None:
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text(SECRET.hex() + "\n", encoding="utf-8")
    package = tmp_path / "reviews" / "alpha"
    assert (
        main(
            [
                "prepare",
                "--dataset",
                str(dataset_dir),
                "--out",
                str(package),
                "--secret-file",
                str(secret_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "PREPARED"

    draft = tmp_path / "draft.json"
    assert (
        main(
            [
                "init-submission",
                "--package",
                str(package),
                "--reviewer-id",
                "reviewer-one",
                "--out",
                str(draft),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "DRAFT_CREATED"

    submission = package / "submissions" / "reviewer-one.json"
    _complete_submission(dataset_dir, package, "reviewer-one", submission)
    report_path = tmp_path / "review-root.json"
    assert (
        main(
            [
                "validate-root",
                "--dataset",
                str(dataset_dir),
                "--root",
                str(package.parent),
                "--out",
                str(report_path),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PASS"
    assert summary["out"] == str(report_path)
    assert _load_object(report_path)["reviewers"] == 1


def test_review_cli_rejects_invalid_secret_file(
    dataset_dir: Path,
    tmp_path: Path,
    capsys,
) -> None:
    secret_path = tmp_path / "bad-secret.txt"
    secret_path.write_text("not-hex", encoding="utf-8")
    assert (
        main(
            [
                "prepare",
                "--dataset",
                str(dataset_dir),
                "--out",
                str(tmp_path / "package"),
                "--secret-file",
                str(secret_path),
            ]
        )
        == 1
    )
    assert "64 hexadecimal digits" in capsys.readouterr().err
