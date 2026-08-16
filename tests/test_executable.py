from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.dataset import load_json
from claimpromotebench.errors import DatasetIntegrityError, ExecutableFixtureError
from claimpromotebench.executable import (
    main,
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
