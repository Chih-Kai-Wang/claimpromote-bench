#!/usr/bin/env python3
"""Freeze a matched three-repeat route study on historical upstream policy revisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from upstream_route_repetition import (  # noqa: E402
    CATALOG_URL,
    DECISION_SCHEMA,
    DOCS_URL,
    GOLD_PATH,
    PACKET_PATH,
    PAIRS_PATH,
    REPETITIONS,
    RUN_SCHEMA,
    SOURCE_MANIFEST_PATH,
    SOURCE_ROOT,
    STUDY_ID,
    STUDY_ROOT,
    lanes,
    request_body,
)

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUNTIME_SOURCES = (
    "pyproject.toml",
    "scripts/analyze_upstream_policy_route_repetition.py",
    "scripts/freeze_upstream_policy_route_repetition.py",
    "scripts/frozen_run_io.py",
    "scripts/openai_compatible_call.py",
    "scripts/run_upstream_policy_route_repetition.py",
    "scripts/upstream_policy_revision.py",
    "scripts/upstream_route_repetition.py",
    "scripts/validate_upstream_policy_revision_study.py",
    "scripts/validate_upstream_policy_route_repetition.py",
    "scripts/validate_upstream_policy_route_repetition_results.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/errors.py",
    "src/claimpromotebench/hashing.py",
    "v2/schemas/upstream-policy-decision.schema.json",
    "v2/schemas/upstream-policy-route-repetition-record.schema.json",
    "v2/upstream-policy-revisions-v1/artifact-manifest.json",
    "v2/upstream-policy-revisions-v1/dataset/evaluation-gold.jsonl",
    "v2/upstream-policy-revisions-v1/dataset/evaluation-pairs.json",
    "v2/upstream-policy-revisions-v1/dataset/evaluation-prompt-packet.json",
)
FAILURE_RULE = (
    "Every scheduled service, availability, syntax, schema, and semantic failure remains "
    "incorrect in its complete 24-item repetition denominator. Each cell permits one "
    "application POST and zero client retries. Interrupted execution is ineligible and cannot "
    "resume; successful subsets cannot replace a scheduled repetition."
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-freeze: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        fail(f"path is outside the repository: {path}")


def fetch_bytes(url: str, api_key: str | None = None) -> bytes:
    headers = {"User-Agent": "ClaimPromoteBench-UpstreamRepetitionFreeze/1"}
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        fail(f"could not fetch preinference source {url}: {exc}")


def selected_catalog_rows(raw: bytes) -> list[Json]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        fail("authenticated model catalog returned non-JSON content")
    rows = value.get("data") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        fail("authenticated model catalog lacks a data array")
    requested = [str(lane["model"]) for lane in lanes()]
    selected: list[Json] = []
    for model_id in requested:
        matches = [row for row in rows if isinstance(row, dict) and row.get("id") == model_id]
        if len(matches) != 1:
            fail(f"authenticated catalog does not contain exactly one {model_id} entry")
        row = matches[0]
        retained = {
            key: row[key]
            for key in ("id", "object", "owned_by", "name", "context_length")
            if key in row
        }
        selected.append(retained)
    return selected


def build_schedule(plan: Json, packet: Json) -> Json:
    lane_rows = [dict(row) for row in plan["formal_lanes"]]
    cells: list[Json] = []
    for repetition in range(1, REPETITIONS + 1):
        for item_index, record in enumerate(packet["records"]):
            rotation = (item_index + repetition - 1) % len(lane_rows)
            ordered_lanes = lane_rows[rotation:] + lane_rows[:rotation]
            for lane in ordered_lanes:
                body = request_body(lane, str(record["prompt"]))
                lane_id = str(lane["lane_id"])
                item_id = str(record["item_id"])
                cells.append(
                    {
                        "sequence": len(cells),
                        "cell_id": f"{lane_id}/r{repetition}/{item_id}",
                        "repetition": repetition,
                        "lane_id": lane_id,
                        "item_id": item_id,
                        "pair_id": str(record["pair_id"]),
                        "prompt_sha256": str(record["prompt_sha256"]),
                        "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
                    }
                )
    schedule: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "planned_cells": len(cells),
        "repetitions": REPETITIONS,
        "base_lane_order": [str(row["lane_id"]) for row in lane_rows],
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": sha256_file(PACKET_PATH),
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode("utf-8"))
    return schedule


def freeze(api_key: str) -> Json:
    targets = (
        STUDY_ROOT / "catalog-snapshot.json",
        STUDY_ROOT / "selection-receipt.json",
        STUDY_ROOT / "study-plan.json",
        STUDY_ROOT / "request-schedule.json",
    )
    if any(path.exists() for path in targets):
        fail("refusing to overwrite an existing freeze artifact")
    if not api_key or api_key != api_key.strip():
        fail("OPENCODE_GO_API_KEY is absent or malformed")
    missing_runtime = [relative for relative in RUNTIME_SOURCES if not (ROOT / relative).is_file()]
    if missing_runtime:
        fail(f"runtime-source files are absent: {missing_runtime}")

    packet = load_json(PACKET_PATH)
    if not isinstance(packet, dict) or len(packet.get("records", [])) != 24:
        fail("source prompt packet must contain twenty-four records")
    catalog_raw = fetch_bytes(CATALOG_URL, api_key)
    docs_raw = fetch_bytes(DOCS_URL)
    recorded_at = utc_now()
    model_ids = [str(lane["model"]) for lane in lanes()]
    catalog: Json = {
        "schema_version": "1.0.0",
        "status": "AUTHENTICATED_CATALOG_SNAPSHOT_BEFORE_INFERENCE",
        "study_id": STUDY_ID,
        "recorded_at_utc": recorded_at,
        "catalog_url": CATALOG_URL,
        "catalog_response_sha256": sha256_bytes(catalog_raw),
        "selected_model_ids": model_ids,
        "selected_model_entries": selected_catalog_rows(catalog_raw),
        "credentials_retained": False,
        "account_identifiers_retained": False,
        "provider_response_identifiers_retained": False,
        "model_outputs_available_before_freeze": False,
    }
    catalog["self_digest"] = self_digest(catalog)
    selection: Json = {
        "schema_version": "1.0.0",
        "status": "ROUTES_AND_REPETITIONS_SELECTED_BEFORE_NEW_OUTPUTS",
        "study_id": STUDY_ID,
        "recorded_at_utc": recorded_at,
        "selection_basis": (
            "Two previously studied named routes provide protocol continuity. Three exact "
            "repetitions estimate time-local within-route stability on the same historical "
            "revision packet."
        ),
        "selected_model_ids": model_ids,
        "selected_repetitions": REPETITIONS,
        "selected_items_per_repetition": 24,
        "planned_application_posts": 144,
        "new_model_calls_for_selection": 0,
        "new_route_outputs_used_for_selection": False,
        "adaptive_stopping_allowed": False,
        "conditional_success_subset_allowed": False,
        "docs_url": DOCS_URL,
        "docs_response_sha256": sha256_bytes(docs_raw),
        "published_typical_request_reference": {
            "qwen3.7-max": {
                "five_hour_requests": 340,
                "weekly_requests": 840,
                "allocated_requests": 72,
            },
            "deepseek-v4-flash": {
                "five_hour_requests": 7600,
                "weekly_requests": 18900,
                "allocated_requests": 72,
            },
        },
        "workflow_initiated_purchase_or_recharge": False,
    }
    selection["self_digest"] = self_digest(selection)
    STUDY_ROOT.mkdir(parents=True, exist_ok=False)
    catalog_path, selection_path, plan_path, schedule_path = targets
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    selection_path.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lane_rows = [dict(row) for row in lanes()]
    response_contract = {
        "strict_top_level_json_only": True,
        "duplicate_keys_rejected": True,
        "code_fence_or_substring_repair": False,
        "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
        "record_schema_sha256": sha256_file(RUN_SCHEMA),
    }
    plan: Json = {
        "schema_version": "1.0.0",
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "study_id": STUDY_ID,
        "frozen_at_utc": recorded_at,
        "research_role": "TIME_STAMPED_WITHIN_ROUTE_REPETITION_ON_HISTORICAL_REVISIONS",
        "purpose": (
            "Measure action, output-contract, and complete-decision behavior across three exact "
            "repetitions of two existing service routes on traceable historical policy revisions."
        ),
        "source": {
            "study_root": repo_relative(SOURCE_ROOT),
            "artifact_manifest_path": repo_relative(SOURCE_MANIFEST_PATH),
            "artifact_manifest_sha256": sha256_file(SOURCE_MANIFEST_PATH),
            "packet_path": repo_relative(PACKET_PATH),
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(PACKET_PATH),
            "gold_path": repo_relative(GOLD_PATH),
            "gold_file_sha256": sha256_file(GOLD_PATH),
            "pairs_path": repo_relative(PAIRS_PATH),
            "pairs_file_sha256": sha256_file(PAIRS_PATH),
            "items": 24,
            "pairs": 12,
            "historical_revisions": 2,
            "source_gold_locked_before_route_outputs": True,
        },
        "formal_lanes": lane_rows,
        "design": {
            "repetitions": REPETITIONS,
            "same_prompt_packet_each_repetition": True,
            "lane_order_interleaved_within_item": True,
            "selection_uses_new_outputs": False,
            "endpoints": {
                "strict_action": (
                    "Extract ALLOW or HOLD only from a strict top-level JSON object and compare "
                    "it with the gold action."
                ),
                "contract_action": (
                    "Require syntax, schema, and semantic validity before comparing action."
                ),
                "full_decision_exact": (
                    "Require the complete decision to equal gold after witness-order normalization."
                ),
            },
            "pair_rule": "Both members must be correct at the corresponding item endpoint.",
            "repeat_agreement_unit": "The three terminal outcomes for one lane and item.",
        },
        "response_contract": response_contract,
        "execution": {
            "base_lane_order": [str(row["lane_id"]) for row in lane_rows],
            "planned_application_posts": 144,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "default_timeout_seconds": 180.0,
            "minimum_global_request_interval_seconds": 0.25,
            "failure_rule": FAILURE_RULE,
        },
        "budget": {
            "billing_mode": "PREEXISTING_OPENCODE_GO_ALLOWANCE",
            "planned_calls_by_model": {model_id: 72 for model_id in model_ids},
            "planned_calls_total": 144,
            "workflow_initiated_purchase_or_recharge": False,
        },
        "interpretation_boundary": (
            "Results describe these time-stamped model-service routes and frozen historical "
            "revision contexts. Cross-route differences are descriptive. Population reliability, "
            "model-family ranking, and causal service-ablation claims remain outside scope."
        ),
        "catalog_snapshot": {
            "path": repo_relative(catalog_path),
            "file_sha256": sha256_file(catalog_path),
            "self_digest": catalog["self_digest"],
        },
        "selection_receipt": {
            "path": repo_relative(selection_path),
            "file_sha256": sha256_file(selection_path),
            "self_digest": selection["self_digest"],
        },
        "runtime_source_sha256": {
            relative: sha256_file(ROOT / relative) for relative in RUNTIME_SOURCES
        },
    }
    schedule = build_schedule(plan, packet)
    plan["execution"]["schedule_path"] = repo_relative(schedule_path)
    plan["execution"]["schedule_sha256"] = schedule["schedule_sha256"]
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schedule_path.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": "UPSTREAM_ROUTE_REPETITION_FROZEN",
        "study_id": STUDY_ID,
        "lanes": len(lane_rows),
        "repetitions": REPETITIONS,
        "planned_calls": len(schedule["cells"]),
        "schedule_sha256": schedule["schedule_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-env", default="OPENCODE_GO_API_KEY")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if api_key is None:
        fail(f"{args.api_key_env} is absent")
    print(canonical_json(freeze(api_key)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
