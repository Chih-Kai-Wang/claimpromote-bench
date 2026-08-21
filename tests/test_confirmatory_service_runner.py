"""Static and request-byte tests for the gold-free confirmatory service runner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.dataset import load_json
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_confirmatory_worker_has_no_gold_or_gate_dependency() -> None:
    source = (ROOT / "scripts" / "run_confirmatory_service_study.py").read_text(encoding="utf-8")
    assert "postgate_decision" not in source
    assert "gold.jsonl" not in source
    assert "--dataset" not in source
    assert "claimpromotebench.v2" not in source
    assert "claimpromotebench.decision_validation" in source
    assert "HTTPRedirectHandler" in source
    assert "client_retry_count" in source
    assert "--preflight-only" in source
    assert '"git", "cat-file", "-e"' in source
    assert "GOLD_FREE_CREDENTIAL_FREE_PREFLIGHT_PASS" in source
    assert source.index("_verify_c1_and_source(\n        args.commitment") < source.index(
        "_validate_key(os.environ"
    )


def test_frozen_request_bodies_match_the_two_selected_service_adapters() -> None:
    runner = _load_script("run_confirmatory_service_study")
    schema = runner.portable_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )
    qwen = {
        "api_kind": "anthropic_messages",
        "response_format": "prompt_only_json",
        "model": "qwen3.7-max",
        "max_output_tokens": 1536,
    }
    qwen_body = runner.request_body_for_lane(qwen, "prompt", schema)
    assert qwen_body == {
        "model": "qwen3.7-max",
        "max_tokens": 1536,
        "messages": [{"role": "user", "content": "prompt"}],
        "stream": False,
    }
    flash = {
        "api_kind": "openai_compatible",
        "response_format": "json_schema",
        "model": "deepseek-v4-flash",
        "max_output_tokens": 1536,
    }
    flash_body = runner.request_body_for_lane(flash, "prompt", schema)
    assert flash_body["max_tokens"] == 1536
    assert flash_body["stream"] is False
    assert flash_body["response_format"]["type"] == "json_schema"
    assert flash_body["response_format"]["json_schema"]["strict"] is True
    for body in (qwen_body, flash_body):
        assert "temperature" not in body
        assert "top_p" not in body
        assert "seed" not in body


def test_reasoning_is_redacted_but_parse_independent_envelope_fields_remain() -> None:
    runner = _load_script("run_confirmatory_service_study")
    sanitized = runner._sanitize_envelope(
        {
            "id": "response-1",
            "reasoning_content": "private chain of thought",
            "content": [
                {"type": "text", "thought": True, "text": "private thought"},
                {"type": "text", "text": '{"action":"ALLOW"}'},
            ],
        }
    )
    assert sanitized["id"] == "response-1"
    assert sanitized["reasoning_content"] == "<REDACTED_HIDDEN_REASONING>"
    assert sanitized["content"][0]["text"] == "<REDACTED_HIDDEN_REASONING>"
    assert sanitized["content"][1]["text"] == '{"action":"ALLOW"}'


@pytest.mark.skipif(
    sys.platform == "win32" and sys.version_info >= (3, 14),
    reason="Python 3.14 Windows PTY handle duplication bug; exercised on pinned 3.11 CI",
)
def test_credential_free_preflight_validates_an_ancestor_source_commit(tmp_path: Path) -> None:
    runner = _load_script("run_confirmatory_service_study")
    repository = tmp_path / "clean-checkout"
    plan_path = repository / "v2" / "fresh-confirmatory-study-plan.json"
    source_path = repository / "frozen-source.txt"
    plan_path.parent.mkdir(parents=True)
    plan = {"study_id": "rehearsal-r5"}
    plan_path.write_text(canonical_json(plan) + "\n", encoding="utf-8", newline="\n")
    source_path.write_text("frozen\n", encoding="utf-8", newline="\n")
    for command in (
        ["git", "init"],
        ["git", "config", "user.name", "Confirmatory Rehearsal"],
        ["git", "config", "user.email", "rehearsal@example.invalid"],
        ["git", "config", "core.autocrlf", "false"],
        ["git", "add", "."],
        ["git", "commit", "-m", "frozen source"],
    ):
        subprocess.run(command, cwd=repository, check=True, capture_output=True)
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    marker = repository / "post-c1-marker.txt"
    marker.write_text("later public receipt\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "later receipt"],
        cwd=repository,
        check=True,
        capture_output=True,
    )

    records = [
        {
            "item_id": f"item-{index:03d}",
            "pair_id": f"pair-{index:03d}",
            "prompt_sha256": sha256_bytes(f"prompt-{index}".encode()),
        }
        for index in range(300)
    ]
    packet = {"study_id": plan["study_id"], "records": records}
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode())
    cells = []
    for lane_id in ("lane-a", "lane-b"):
        for index, record in enumerate(records):
            body = {"model": lane_id, "messages": [{"content": f"prompt-{index}"}]}
            cells.append(
                {
                    "lane_id": lane_id,
                    "sequence": index,
                    "item_id": record["item_id"],
                    "pair_id": record["pair_id"],
                    "prompt_sha256": record["prompt_sha256"],
                    "request_body": body,
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode()),
                }
            )
    baselines = {
        "packet_sha256": packet["packet_sha256"],
        "contains_test_gold": False,
        "records": [],
    }
    baselines["predictions_sha256"] = sha256_bytes(canonical_json(baselines).encode())
    schedule = {
        "study_id": plan["study_id"],
        "packet_sha256": packet["packet_sha256"],
        "planned_cells": 600,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode())
    request_hashes = sorted(str(cell["request_body_sha256"]) for cell in cells)
    c1 = {
        "study_id": plan["study_id"],
        "plan_file_sha256": sha256_file(plan_path),
        "packet_sha256": packet["packet_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "baseline_predictions_sha256": baselines["predictions_sha256"],
        "request_body_hash_set_sha256": sha256_bytes(canonical_json(request_hashes).encode()),
        "planned_cells": 600,
    }
    c1["c1_receipt_sha256"] = sha256_bytes(canonical_json(c1).encode())
    commitment = {
        "study_id": plan["study_id"],
        "source_commit": source_commit,
        "source_files_sha256": {
            "frozen-source.txt": sha256_file(source_path),
            "v2/fresh-confirmatory-study-plan.json": sha256_file(plan_path),
        },
        "c1_receipt": c1,
    }
    commitment["commitment_sha256"] = sha256_bytes(canonical_json(commitment).encode())
    commitment_path = repository / "commitment.json"
    baseline_path = repository / "baselines.json"
    commitment_path.write_text(json.dumps(commitment), encoding="utf-8")
    baseline_path.write_text(json.dumps(baselines), encoding="utf-8")

    original_root = runner.ROOT
    try:
        runner.ROOT = repository
        runner._verify_frozen_plan(plan_path, source_commit)
        runner._verify_c1_and_source(
            commitment_path,
            plan_path,
            plan,
            packet,
            schedule,
            source_commit,
            baseline_path,
        )
    finally:
        runner.ROOT = original_root
