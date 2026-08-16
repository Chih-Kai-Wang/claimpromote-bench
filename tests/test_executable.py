from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.errors import DatasetIntegrityError, ExecutableFixtureError
from claimpromotebench.executable import (
    build_exact_grid_artifact,
    main,
    verify_dataset_artifact,
    verify_exact_grid_artifact,
    verify_fixture_case,
    verify_fixture_suite,
)


def _valid_case(root: Path) -> dict[str, object]:
    value = load_json(root / "fixtures" / "executable" / "valid-nonnegative-quadratic.json")
    assert isinstance(value, dict)
    return value


def test_exact_grid_fixture_recomputes_expected_values(root: Path) -> None:
    case = _valid_case(root)
    artifact = case["artifact"]
    assert isinstance(artifact, dict)
    result = verify_exact_grid_artifact(artifact)
    assert result["status"] == "PASS"
    assert result["grid_points"] == 5
    assert result["minimum"] == "3/4"
    assert result["maximum"] == "1"
    assert result["predicate_holds"] is True
    assert result["repetitions"] == 3


def test_exact_grid_builder_reproduces_registered_positive_fixture(root: Path) -> None:
    case = _valid_case(root)
    assert (
        build_exact_grid_artifact(
            coefficients=["1", "-1", "1"],
            grid=["0", "1/4", "1/2", "3/4", "1"],
            relation=">=",
            threshold="0",
            repetitions=3,
        )
        == case["artifact"]
    )


def test_alpha_numerical_artifacts_are_executable_and_bound(dataset_dir: Path) -> None:
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold = {record["id"]: record for record in load_jsonl(dataset_dir / "gold.jsonl")}
    artifact_paths: set[str] = set()
    evidence_count = 0
    for item in inputs:
        if item["family"] != "NUMERICAL":
            continue
        evidence = item["evidence"][0]
        result = verify_dataset_artifact(
            dataset_dir,
            evidence,
            require_scope_match=gold[item["id"]]["decision"]["action"] == "ALLOW",
        )
        assert result["status"] == "PASS"
        assert result["predicate_holds"] is True
        artifact_paths.add(evidence["artifact_path"])
        evidence_count += 1
    assert len(artifact_paths) == 4
    assert evidence_count == 8


def test_alpha_valid_member_rejects_scope_artifact_mismatch(dataset_dir: Path) -> None:
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    item = next(value for value in inputs if value["id"] == "alpha-num-01-a")
    evidence = deepcopy(item["evidence"][0])
    evidence["scope"]["repetitions"] = 4
    with pytest.raises(DatasetIntegrityError, match="repetitions"):
        verify_dataset_artifact(dataset_dir, evidence, require_scope_match=True)


def test_executable_fixture_suite_covers_positive_and_negative_cases(root: Path) -> None:
    report = verify_fixture_suite(root / "fixtures" / "executable")
    assert report["status"] == "PASS"
    assert report["fixtures"] == 6
    assert report["positive_cases"] == 1
    assert report["negative_cases"] == 5
    rejected = {
        result["case_id"]: result["error_code"]
        for result in report["results"]
        if result["observed_status"] == "REJECT"
    }
    assert rejected == {
        "reject-not-preregistered": "PREREGISTRATION_REQUIRED",
        "reject-overclaimed-scope": "SCOPE_MISMATCH",
        "reject-tampered-digest": "REPETITION_DIGEST_MISMATCH",
        "reject-tampered-observation": "OBSERVATION_MISMATCH",
        "reject-unsupported-protocol": "UNSUPPORTED_PROTOCOL",
    }


def test_direct_verifier_rejects_invalid_grid_and_rational(root: Path) -> None:
    case = _valid_case(root)
    artifact = case["artifact"]
    assert isinstance(artifact, dict)

    duplicate_grid = deepcopy(artifact)
    duplicate_grid["program"]["grid"][2] = "1/4"
    with pytest.raises(ExecutableFixtureError) as grid_error:
        verify_exact_grid_artifact(duplicate_grid)
    assert grid_error.value.code == "INVALID_GRID"

    invalid_rational = deepcopy(artifact)
    invalid_rational["program"]["coefficients"][0] = "1/0"
    with pytest.raises(ExecutableFixtureError) as rational_error:
        verify_exact_grid_artifact(invalid_rational)
    assert rational_error.value.code == "INVALID_RATIONAL"


def test_fixture_case_rejects_wrong_expected_error(root: Path) -> None:
    value = load_json(root / "fixtures" / "executable" / "reject-tampered-observation.json")
    assert isinstance(value, dict)
    value["expected_error_code"] = "SCOPE_MISMATCH"
    with pytest.raises(DatasetIntegrityError, match="OBSERVATION_MISMATCH"):
        verify_fixture_case(value)


def test_executable_cli_writes_machine_readable_report(
    root: Path,
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "executable-fixtures.json"
    assert (
        main(
            [
                "--fixtures",
                str(root / "fixtures" / "executable"),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert summary == {
        "fixtures": 6,
        "negative_cases": 5,
        "out": str(output),
        "positive_cases": 1,
        "status": "PASS",
    }
    assert report["status"] == "PASS"
    assert len(report["results"]) == 6


def test_executable_cli_fails_closed_on_empty_suite(tmp_path: Path, capsys) -> None:
    assert main(["--fixtures", str(tmp_path)]) == 1
    assert "no executable fixtures" in capsys.readouterr().err
