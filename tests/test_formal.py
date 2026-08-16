from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.dataset import load_jsonl
from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.formal import (
    TOOLCHAIN_CONTENT,
    TOOLCHAIN_SHA256,
    build_formal_artifact,
    formal_artifact_path,
    formal_claim_text,
    verify_alpha_formal_sources,
    verify_formal_artifact_binding,
    verify_formal_fixture_suite,
)
from claimpromotebench.hashing import sha256_bytes


def _stub_runner(_package_dir: Path, source: Path) -> dict[str, object]:
    rejected = source.name.startswith("reject-")
    return {
        "exit_code": 1 if rejected else 0,
        "output_sha256": "sha256:" + ("1" if rejected else "0") * 64,
    }


def test_pinned_toolchain_hash_is_derived_from_exact_file_bytes() -> None:
    assert TOOLCHAIN_SHA256 == sha256_bytes(TOOLCHAIN_CONTENT.encode("utf-8"))
    assert TOOLCHAIN_CONTENT == "leanprover/lean4:v4.33.0\n"


def test_formal_claims_and_sources_are_pair_specific() -> None:
    claim = formal_claim_text("alpha-formal-01")
    source = build_formal_artifact(
        "alpha-formal-01",
        "claim-test",
        "sha256:" + "1" * 64,
    )
    assert claim == "For every natural number n, n + 0 = n."
    assert formal_artifact_path("alpha-formal-01").endswith("Formal01.lean")
    assert "CPB_CLAIM_ID=claim-test" in source
    assert f"CPB_TOOLCHAIN_LOCK_SHA256={TOOLCHAIN_SHA256}" in source
    assert "theorem formal01 (n : Nat) : n + 0 = n" in source


def test_formal_fixture_suite_checks_expected_pass_and_reject(root: Path) -> None:
    report = verify_formal_fixture_suite(
        root / "fixtures" / "formal" / "cases.json",
        package_dir=root / "data" / "alpha",
        runner=_stub_runner,
    )
    assert report["status"] == "PASS"
    assert report["fixtures"] == 3
    assert report["positive_cases"] == 1
    assert report["negative_cases"] == 2


def test_alpha_formal_sources_are_bound_and_executable_with_stub(dataset_dir: Path) -> None:
    report = verify_alpha_formal_sources(dataset_dir, runner=_stub_runner)
    assert report["status"] == "PASS"
    assert report["artifacts"] == 3
    assert report["evidence_records"] == 6
    assert report["toolchain_sha256"] == TOOLCHAIN_SHA256


def test_valid_formal_member_rejects_scope_source_mismatch(dataset_dir: Path) -> None:
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    item = next(value for value in inputs if value["id"] == "alpha-formal-01-a")
    evidence = deepcopy(item["evidence"][0])
    evidence["scope"]["statement_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(DatasetIntegrityError, match="scope does not match"):
        verify_formal_artifact_binding(
            dataset_dir,
            item,
            evidence,
            require_scope_match=True,
        )
