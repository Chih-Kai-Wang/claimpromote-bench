"""Static and request-byte tests for the gold-free confirmatory service runner."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from copy import deepcopy
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
    assert "_independently_reconstruct_subscription_authorization(" in source
    assert "confirmatory_subscription_authorization" not in source
    assert "build_confirmatory_c1" not in source
    assert "subscription_authorization_gate" in source
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


def test_credential_free_preflight_validates_an_ancestor_source_commit(tmp_path: Path) -> None:
    runner = _load_script("run_confirmatory_service_study")
    repository = tmp_path / "clean-checkout"
    plan_path = repository / "v2" / "fresh-confirmatory-study-plan.json"
    source_path = repository / "frozen-source.txt"
    plan_path.parent.mkdir(parents=True)
    lane_ids = (
        "opencode-go-qwen3.7-max",
        "opencode-go-deepseek-v4-flash-matched",
    )
    plan = {
        "study_id": "rehearsal-r6",
        "design": {
            "planned_lanes": 2,
            "planned_instances": 300,
            "planned_model_item_cells": 600,
        },
        "execution": {
            "lane_order": list(lane_ids),
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "redirect_following": False,
            "partial_resume": "FORBIDDEN",
            "workflow_job_rerun": (
                "FORBIDDEN; ANY_R6_SCORED_WORKFLOW_DISPATCH_CONSUMES_THE_VERSION_"
                "REGARDLESS_OF_CONFIRM_VALUE_POST_COUNT_OR_JOB_OUTCOME"
            ),
        },
        "budget": {
            "mode": "PREEXISTING_SUBSCRIPTION_QUOTA_ONLY",
            "authorization_scope": (
                "USER_AUTHORIZED_FULL_EXISTING_OPENCODE_GO_SUBSCRIPTION_QUOTA_FOR_THIS_"
                "FIXED_600_CELL_STUDY"
            ),
            "planned_application_posts": 600,
            "planned_posts_per_lane": 300,
            "max_output_tokens_per_post": 1536,
            "incremental_cash_cap_usd": 0.0,
            "workflow_initiated_purchase_or_recharge": False,
            "cash_balance_fallback": False,
            "alternate_provider_fallback": False,
            "per_lane_token_usd_cap": None,
            "pre_post_token_cost_gate": "NOT_APPLICABLE",
            "quota_exhaustion": "CELL_INCORRECT_NO_RETRY",
            "provider_reported_usage_and_quota_value": "POSTHOC_DESCRIPTIVE_ONLY",
            "adaptive_stop_on_usage_or_results": False,
        },
        "formal_lanes": [
            {
                "lane_id": lane_id,
                "model": (
                    "qwen3.7-max" if lane_id == "opencode-go-qwen3.7-max" else "deepseek-v4-flash"
                ),
                "api_kind": (
                    "anthropic_messages"
                    if lane_id == "opencode-go-qwen3.7-max"
                    else "openai_compatible"
                ),
                "response_format": (
                    "prompt_only_json" if lane_id == "opencode-go-qwen3.7-max" else "json_schema"
                ),
                "base_url": "https://opencode.ai/zen/go/v1",
                "auth_env": "OPENCODE_GO_API_KEY",
                "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
                "spend_cap_usd": None,
                "quota_value_rates_use": "POSTHOC_DESCRIPTIVE_ONLY",
                "max_output_tokens": 1536,
            }
            for lane_id in lane_ids
        ],
    }
    plan_path.write_text(canonical_json(plan) + "\n", encoding="utf-8", newline="\n")
    source_path.write_text("frozen\n", encoding="utf-8", newline="\n")
    schema_path = repository / "schemas" / "agent-decision.schema.json"
    schema_path.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "schemas" / "agent-decision.schema.json", schema_path)
    manifest_path = repository / "configs" / "confirmatory-runtime-source-manifest-r6.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "schema_version": "1.0.0",
        "status": "EXACT_RUNTIME_SOURCE_CLOSURE",
        "study_id": plan["study_id"],
        "file_count": 2,
        "files_sha256": {
            "frozen-source.txt": sha256_file(source_path),
            "schemas/agent-decision.schema.json": sha256_file(schema_path),
        },
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest).encode())
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
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
            "prompt": f"prompt-{index}",
            "prompt_sha256": sha256_bytes(f"prompt-{index}".encode()),
        }
        for index in range(300)
    ]
    packet = {"study_id": plan["study_id"], "records": records}
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode())
    cells = []
    schema = runner.portable_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    for lane_id in lane_ids:
        for index, record in enumerate(records):
            body = runner.request_body_for_lane(lanes[lane_id], record["prompt"], schema)
            headers = runner.request_headers_template(lanes[lane_id])
            cells.append(
                {
                    "cell_id": f"{lane_id}/{record['item_id']}",
                    "lane_id": lane_id,
                    "sequence": index,
                    "item_id": record["item_id"],
                    "pair_id": record["pair_id"],
                    "prompt_sha256": record["prompt_sha256"],
                    "request_body": body,
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode()),
                    "request_headers_template": headers,
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
        "lane_order": list(lane_ids),
        "item_order": "LEXICOGRAPHIC_OPAQUE_ITEM_ID_WITHIN_EACH_LANE",
        "planned_cells": 600,
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode())
    request_hashes = sorted(str(cell["request_body_sha256"]) for cell in cells)
    authorization = _load_script("confirmatory_subscription_authorization")
    c1 = {
        "study_id": plan["study_id"],
        "plan_file_sha256": sha256_file(plan_path),
        "packet_sha256": packet["packet_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "baseline_predictions_sha256": baselines["predictions_sha256"],
        "request_body_hash_set_sha256": sha256_bytes(canonical_json(request_hashes).encode()),
        "planned_cells": 600,
        "subscription_authorization": authorization.validate_schedule_authorization(plan, schedule),
    }
    c1["c1_receipt_sha256"] = sha256_bytes(canonical_json(c1).encode())
    commitment = {
        "study_id": plan["study_id"],
        "source_commit": source_commit,
        "runtime_source_manifest_sha256": manifest["manifest_sha256"],
        "source_files_sha256": {
            "configs/confirmatory-runtime-source-manifest-r6.json": sha256_file(manifest_path),
            "frozen-source.txt": sha256_file(source_path),
            "schemas/agent-decision.schema.json": sha256_file(schema_path),
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
    original_schema = runner.DECISION_SCHEMA
    original_manifest = runner.RUNTIME_SOURCE_MANIFEST
    original_rules = runner._RUNTIME_DISCOVERY_RULES
    original_explicit = runner._RUNTIME_EXPLICIT_PATHS
    original_extras = runner._SOURCE_MAP_EXTRAS
    try:
        runner.ROOT = repository
        runner.DECISION_SCHEMA = schema_path
        runner.RUNTIME_SOURCE_MANIFEST = manifest_path
        runner._RUNTIME_DISCOVERY_RULES = ()
        runner._RUNTIME_EXPLICIT_PATHS = {
            "frozen-source.txt",
            "schemas/agent-decision.schema.json",
        }
        runner._SOURCE_MAP_EXTRAS = {
            "configs/confirmatory-runtime-source-manifest-r6.json",
            "v2/fresh-confirmatory-study-plan.json",
        }
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

        changed_prompt = deepcopy(packet)
        changed_prompt["records"][0]["prompt_sha256"] = "sha256:" + "0" * 64
        with pytest.raises(SystemExit, match="changed prompt digest"):
            runner._independently_reconstruct_subscription_authorization(
                plan, schedule, changed_prompt
            )

        changed_schema = deepcopy(schedule)
        flash_index = 300
        changed_schema["cells"][flash_index]["request_body"]["response_format"]["json_schema"][
            "strict"
        ] = False
        with pytest.raises(SystemExit, match="exact request reconstruction failed"):
            runner._independently_reconstruct_subscription_authorization(
                plan, changed_schema, packet
            )

        changed_order = deepcopy(schedule)
        changed_order["cells"][1]["sequence"] = 0
        with pytest.raises(SystemExit, match="changed cell order"):
            runner._independently_reconstruct_subscription_authorization(
                plan, changed_order, packet
            )
    finally:
        runner.ROOT = original_root
        runner.DECISION_SCHEMA = original_schema
        runner.RUNTIME_SOURCE_MANIFEST = original_manifest
        runner._RUNTIME_DISCOVERY_RULES = original_rules
        runner._RUNTIME_EXPLICIT_PATHS = original_explicit
        runner._SOURCE_MAP_EXTRAS = original_extras
