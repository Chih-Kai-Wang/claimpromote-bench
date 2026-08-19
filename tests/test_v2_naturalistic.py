from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_v2_naturalistic_candidates.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_v2_naturalistic_candidates", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_core_bench_candidate_sampling_is_deterministic_and_unlabeled() -> None:
    module = _module()
    rows = [
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
    source = {
        "source_id": "core-bench-train",
        "repository": "siegelz/core-bench",
        "commit": "deadbeef",
        "path": "benchmark/dataset/core_train.json",
        "eligible_field": "Computer Science",
        "redistribution_mode": "METADATA_POINTERS_ONLY_UNLESS_CASE_LICENSE_VERIFIED",
    }

    first = module.sample_core_bench(rows, salt="fixed-salt", count=12, source=source)
    second = module.sample_core_bench(list(reversed(rows)), salt="fixed-salt", count=12, source=source)

    assert first == second
    assert len(first) == 12
    assert len({row["candidate_id"] for row in first}) == 12
    assert all(row["label_status"] == "UNLABELED_CANDIDATE" for row in first)
    assert all(row["include_status"] == "PENDING_SOURCE_LEVEL_REVIEW" for row in first)
    assert all(row["capsule_id"] != "capsule-excluded" for row in first)
    assert all("sampling_rank_sha256" in row for row in first)
