from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_v2_naturalistic_candidates.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_v2_naturalistic_candidates.py"


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {
            "field": "Computer Science",
            "language": "Python",
            "capsule_title": f"Paper {index}",
            "capsule_id": f"capsule-{index:04d}",
            "task_prompt": f"Run experiment {index}",
            "capsule_doi": f"https://doi.org/example.{index}",
        }
        for index in range(20)
    ]
    rows.append(
        {
            "field": "Social Sciences",
            "language": "R",
            "capsule_title": "Excluded field",
            "capsule_id": "capsule-excluded",
            "task_prompt": "Do not select",
            "capsule_doi": "https://doi.org/excluded",
        }
    )
    return rows


def _source() -> dict[str, object]:
    return {
        "source_id": "core-bench-train",
        "repository": "siegelz/core-bench",
        "commit": "deadbeef",
        "path": "benchmark/dataset/core_train.json",
        "eligible_field": "Computer Science",
        "redistribution_mode": "METADATA_POINTERS_ONLY_UNLESS_CASE_LICENSE_VERIFIED",
        "status": "APPROVED_FOR_CANDIDATE_SAMPLING",
    }


def test_core_bench_candidate_sampling_is_deterministic_and_unlabeled() -> None:
    module = _module(BUILD_SCRIPT, "build_v2_naturalistic_candidates")
    rows = _rows()
    source = _source()

    first = module.sample_core_bench(rows, salt="fixed-salt", count=12, source=source)
    second = module.sample_core_bench(
        list(reversed(rows)), salt="fixed-salt", count=12, source=source
    )

    assert first == second
    assert len(first) == 12
    assert len({row["candidate_id"] for row in first}) == 12
    assert all(row["label_status"] == "UNLABELED_CANDIDATE" for row in first)
    assert all(row["include_status"] == "PENDING_SOURCE_LEVEL_REVIEW" for row in first)
    assert all(row["capsule_id"] != "capsule-excluded" for row in first)
    assert all("sampling_rank_sha256" in row for row in first)


def _pool_fixture():
    builder = _module(BUILD_SCRIPT, "build_v2_naturalistic_candidates_fixture")
    validator = _module(VALIDATE_SCRIPT, "validate_v2_naturalistic_candidates_fixture")
    source = _source()
    manual_source = {
        "source_id": "manual-source",
        "repository": "example/manual",
        "commit": "cafebabe",
        "path": None,
        "redistribution_mode": "POINTER_ONLY",
        "status": "APPROVED_FOR_MANUAL_POINTER_CURATION",
    }
    registry = {
        "schema_version": "1.0.0",
        "selection_salt": "fixed-salt",
        "candidate_target_per_source": 12,
        "sources": [source, manual_source],
    }
    candidates = builder.sample_core_bench(
        _rows(), salt="fixed-salt", count=12, source=source
    )
    pool = {
        "schema_version": "1.0.0",
        "status": "CANDIDATE_POOL_ONLY",
        "selection_salt": "fixed-salt",
        "registry_sha256": validator.digest(registry),
        "source_snapshots": [
            {
                "source_id": "core-bench-train",
                "repository": "siegelz/core-bench",
                "commit": "deadbeef",
                "path": "benchmark/dataset/core_train.json",
                "source_bytes_sha256": "sha256:" + "1" * 64,
                "sampled": 12,
            },
            {
                "source_id": "manual-source",
                "status": "APPROVED_FOR_MANUAL_POINTER_CURATION",
                "sampled": 0,
            },
        ],
        "candidate_count": 12,
        "candidates": candidates,
        "interpretation_boundary": "These are unlabeled source candidates, not benchmark items.",
    }
    return validator, registry, pool


def test_naturalistic_candidate_pool_validator_accepts_pointer_only_pool() -> None:
    validator, registry, pool = _pool_fixture()
    report = validator.validate(registry, pool)
    assert report["status"] == "PASS"
    assert report["candidate_count"] == 12
    assert report["approved_sources"] == ["core-bench-train"]


def test_naturalistic_candidate_pool_validator_rejects_result_leakage() -> None:
    validator, registry, pool = _pool_fixture()
    invalid = deepcopy(pool)
    invalid["candidates"][0]["results"] = {"answer": 1}
    with pytest.raises(SystemExit, match="result/label keys"):
        validator.validate(registry, invalid)
