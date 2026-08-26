"""C0 hash-boundary and C2 failure-accounting tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_json, write_jsonl
from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_c0_plan_has_no_unbound_hash_or_hidden_adaptation_path() -> None:
    validator = _load_script("validate_confirmatory_c0")
    plan_path = ROOT / "v2" / "fresh-confirmatory-study-plan.json"
    plan = load_json(plan_path)
    commitment = load_json(
        ROOT / "v2" / "confirmatory" / "c1-r6" / "confirmatory-hidden-commitment.json"
    )
    assert "PENDING_C0_HASH" not in plan_path.read_text(encoding="utf-8")
    validator.validate_plan(plan)
    authorization = validator.validate_plan_authorization(plan)
    assert authorization["status"] == "SUBSCRIPTION_AUTHORIZATION_GATE_PASS"
    assert plan["pilot"]["instances"] == 0
    assert plan["pilot"]["pairs"] == []
    assert plan["design"]["full_requires_pilot"] is False
    assert len(plan["statistics"]["hypotheses"]) == 2
    assert plan["design"]["planned_model_item_cells"] == 600
    assert plan["execution"]["client_retry_count"] == 0

    frozen_files = commitment["source_files_sha256"]
    for field, relative in validator._HASH_BINDINGS.items():
        assert validator._nested(plan, field) == frozen_files[relative]


def test_c2_seals_completed_and_conservatively_ambiguous_cells(tmp_path: Path) -> None:
    finalizer = _load_script("finalize_confirmatory_c2")
    cells = [
        {
            "lane_id": "lane-a",
            "item_id": f"item-{index}",
            "pair_id": f"pair-{index}",
            "sequence": index,
            "prompt_sha256": "sha256:" + str(index + 1) * 64,
            "request_body_sha256": "sha256:" + str(index + 4) * 64,
        }
        for index in range(3)
    ]
    schedule = {
        "schema_version": "1.0.0",
        "study_id": "study",
        "packet_sha256": "sha256:" + "a" * 64,
        "lane_order": ["lane-a"],
        "planned_cells": 3,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode("utf-8"))
    schedule_path = tmp_path / "schedule.json"
    schedule_path.write_text(canonical_json(schedule), encoding="utf-8")
    journal_path = tmp_path / "journal.jsonl"
    write_jsonl(
        journal_path,
        [
            {
                "event": "POST_INTENT",
                "lane_id": "lane-a",
                "item_id": "item-0",
                "request_body_sha256": cells[0]["request_body_sha256"],
            },
            {
                "event": "POST_INTENT",
                "lane_id": "lane-a",
                "item_id": "item-1",
                "request_body_sha256": cells[1]["request_body_sha256"],
            },
        ],
    )
    run_path = tmp_path / "run.jsonl"
    write_jsonl(
        run_path,
        [
            {
                "lane_id": "lane-a",
                "item_id": "item-0",
                "request_body_sha256": cells[0]["request_body_sha256"],
                "application_post_count": 1,
                "client_retry_count": 0,
                "parse_status": "OK",
                "raw_decision": {"action": "ALLOW"},
            }
        ],
    )
    receipt, by_lane = finalizer.finalize(
        schedule_path,
        [journal_path],
        [run_path],
        tmp_path / "complete",
    )
    assert receipt["planned_cells"] == receipt["sealed_cells"] == 3
    assert receipt["outcome_counts"] == {
        "AMBIGUOUS_ORCHESTRATION_LOSS": 1,
        "AMBIGUOUS_REQUEST_LOSS": 1,
        "RESPONSE_RECORDED": 1,
    }
    assert [row["c2_cell_outcome"] for row in by_lane["lane-a"]] == [
        "RESPONSE_RECORDED",
        "AMBIGUOUS_REQUEST_LOSS",
        "AMBIGUOUS_ORCHESTRATION_LOSS",
    ]
    for row in by_lane["lane-a"][1:]:
        assert row["application_post_count"] is None
        assert row["application_post_count_range"] == [0, 1]
        assert row["request_accounting_status"] == "UNKNOWN_0_OR_1_POST"
    assert receipt["ephemeral_runner_loss_cannot_prove_zero_posts"] is True
