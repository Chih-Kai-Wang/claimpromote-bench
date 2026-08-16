from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.dataset import (
    EXPECTED_FAMILY_COUNTS,
    check_pairs,
    load_jsonl,
    validate_dataset,
    verify_manifest,
)
from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.hashing import resolve_artifact, verify_artifact


def test_full_dataset_contract(dataset_dir: Path) -> None:
    report = validate_dataset(dataset_dir)
    assert report["instances"] == 40
    assert report["pairs"] == 20
    assert report["families"] == EXPECTED_FAMILY_COUNTS
    assert report["executable_computation_artifacts"] == 4
    assert report["executable_computation_evidence"] == 8
    assert report["model_experiments"] == "PENDING"


def test_manifest_and_pairs(dataset_dir: Path) -> None:
    assert len(verify_manifest(dataset_dir)["files"]) >= 5
    assert check_pairs(dataset_dir) == EXPECTED_FAMILY_COUNTS


def test_public_inputs_do_not_contain_gold(dataset_dir: Path) -> None:
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    assert all("gold" not in item for item in inputs)


def test_path_escape_and_tampering_are_dataset_errors(dataset_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(DatasetIntegrityError):
        resolve_artifact(dataset_dir, "../gold.jsonl")
    evidence = deepcopy(load_jsonl(dataset_dir / "inputs.jsonl")[0]["evidence"][0])
    evidence["artifact_hash"] = "sha256:" + "0" * 64
    with pytest.raises(DatasetIntegrityError, match="artifact hash mismatch"):
        verify_artifact(dataset_dir, evidence)
