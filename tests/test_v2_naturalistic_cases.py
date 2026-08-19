from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_v2_naturalistic_cases.py"
SCHEMA = ROOT / "v2" / "schemas" / "naturalistic-case.schema.json"
COMMIT = "a" * 40
RANK = "sha256:" + "b" * 64
SOURCE_HASH = "sha256:" + "c" * 64


def _module():
    spec = importlib.util.spec_from_file_location("validate_v2_naturalistic_cases", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate_pool() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "status": "CANDIDATE_POOL_ONLY",
        "candidate_count": 1,
        "candidates": [
            {
                "candidate_id": "core-bench:capsule-test",
                "source_repository": "example/research",
                "source_commit": COMMIT,
                "source_path": "benchmark/task.json",
                "sampling_rank_sha256": RANK,
            }
        ],
    }


def _case() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "case_id": "naturalistic-example-case",
        "candidate_id": "core-bench:capsule-test",
        "source": {
            "repository": "example/research",
            "commit": COMMIT,
            "path": "benchmark/task.json",
            "stable_url": f"https://github.com/example/research/blob/{COMMIT}/benchmark/task.json",
            "source_sha256": SOURCE_HASH,
            "license_review": "POINTER_ONLY",
            "redistribution_mode": "POINTER_ONLY",
            "evaluation_time": "2026-08-20T00:00:00Z",
        },
        "selection": {
            "sampling_rank_sha256": RANK,
            "inclusion_status": "PENDING",
            "inclusion_decided_without_model_outputs": True,
            "decision_note": "Awaiting source-level evidence review.",
        },
        "label_status": "UNLABELED",
        "model_visible": {
            "claim_text": "The recorded computation completed successfully.",
            "current_state": {
                "research_status": "OPEN",
                "computation_status": "NONE",
                "formal_status": "NONE",
                "review_status": "UNREVIEWED",
            },
            "requested_target_state": {
                "research_status": "OPEN",
                "computation_status": "COMPUTATIONAL",
                "formal_status": "NONE",
                "review_status": "UNREVIEWED",
            },
            "evidence_snapshot": [
                {
                    "evidence_id": "evidence-run-log",
                    "evidence_type": "RUNTIME",
                    "description": "Public pointer to the recorded run log.",
                    "source_pointer": "benchmark/task.json#run-log",
                    "observed_at": "2026-08-19T00:00:00Z",
                    "artifact_sha256": None,
                    "copied_source_bytes": False,
                }
            ],
        },
        "evaluator_only": {
            "policy_version": "PENDING_POLICY_REVIEW",
            "action": None,
            "reason_codes": [],
            "label_rationale": "",
            "interpretation_choices": [],
            "source_checks": [],
        },
        "release": {
            "pointer_only": True,
            "copied_source_bytes": False,
            "license_verified_for_copied_bytes": False,
        },
    }


def _write_fixture(tmp_path: Path, case: dict[str, object]) -> tuple[Path, Path]:
    root = tmp_path / "cases"
    root.mkdir()
    (root / "case.json").write_text(json.dumps(case), encoding="utf-8")
    candidate_path = tmp_path / "candidates.json"
    candidate_path.write_text(json.dumps(_candidate_pool()), encoding="utf-8")
    return root, candidate_path


def test_valid_unlabeled_pointer_only_case_passes(tmp_path: Path) -> None:
    module = _module()
    root, candidate_path = _write_fixture(tmp_path, _case())
    report = module.validate_root(
        root,
        schema_path=SCHEMA,
        candidate_path=candidate_path,
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 1
    assert report["label_status_counts"] == {
        "UNLABELED": 1,
        "LABELED": 0,
        "EXCLUDED": 0,
    }


def test_future_evidence_is_rejected(tmp_path: Path) -> None:
    module = _module()
    case = deepcopy(_case())
    case["model_visible"]["evidence_snapshot"][0]["observed_at"] = "2026-08-21T00:00:00Z"
    root, candidate_path = _write_fixture(tmp_path, case)
    with pytest.raises(SystemExit, match="observed after evaluation_time"):
        module.validate_root(root, schema_path=SCHEMA, candidate_path=candidate_path)


def test_model_visible_evaluator_label_is_rejected(tmp_path: Path) -> None:
    module = _module()
    case = deepcopy(_case())
    case["model_visible"]["action"] = "ALLOW"
    root, candidate_path = _write_fixture(tmp_path, case)
    with pytest.raises(SystemExit, match="schema violation"):
        module.validate_root(root, schema_path=SCHEMA, candidate_path=candidate_path)


def test_candidate_source_binding_is_rejected_when_changed(tmp_path: Path) -> None:
    module = _module()
    case = deepcopy(_case())
    case["source"]["path"] = "different/task.json"
    case["source"]["stable_url"] = (
        f"https://github.com/example/research/blob/{COMMIT}/different/task.json"
    )
    root, candidate_path = _write_fixture(tmp_path, case)
    with pytest.raises(SystemExit, match="does not match frozen candidate"):
        module.validate_root(root, schema_path=SCHEMA, candidate_path=candidate_path)


def test_pointer_only_case_cannot_claim_copied_bytes(tmp_path: Path) -> None:
    module = _module()
    case = deepcopy(_case())
    case["model_visible"]["evidence_snapshot"][0]["copied_source_bytes"] = True
    root, candidate_path = _write_fixture(tmp_path, case)
    with pytest.raises(SystemExit, match="schema violation"):
        module.validate_root(root, schema_path=SCHEMA, candidate_path=candidate_path)
