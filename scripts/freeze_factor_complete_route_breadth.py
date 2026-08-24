#!/usr/bin/env python3
"""Freeze the factor-complete route-breadth plan before benchmark inference."""

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

from factor_complete_route_breadth import (  # noqa: E402
    CATALOG_URL,
    CONFIGURATIONS,
    DATASET_ROOT,
    MAX_OUTPUT_TOKENS,
    PACKET_PATH,
    REPLICATIONS,
    STUDY_ID,
    STUDY_ROOT,
    conservative_cost_upper_bound_usd,
    expanded_lanes,
    schedule_payload,
    selected_action_counts,
    selected_item_ids,
    selected_pairs,
)

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUNTIME_SOURCES = (
    "schemas/agent-decision.schema.json",
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_factor_complete_route_breadth.py",
    "scripts/factor_complete_route_breadth.py",
    "scripts/freeze_factor_complete_route_breadth.py",
    "scripts/run_factor_complete_route_breadth.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/validate_factor_complete_route_breadth.py",
    "scripts/validate_factor_complete_route_breadth_results.py",
    "v2/schemas/stronger-model-run-record.schema.json",
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"factor-complete-route-breadth-freeze: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_new_json(path: Path, value: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fetch_catalog(api_key: str) -> tuple[bytes, Json]:
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"Authorization": f"Bearer {api_key}", "User-Agent": "ClaimPromoteBench/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            status = response.status
    except (urllib.error.URLError, OSError) as exc:
        fail(f"authenticated catalog request failed: {exc.__class__.__name__}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        fail("authenticated catalog returned non-JSON content")
    if status != 200 or not isinstance(value, dict) or not isinstance(value.get("data"), list):
        fail("authenticated catalog response is malformed")
    return raw, value


def catalog_snapshot(raw: bytes, value: Json) -> Json:
    rows = value["data"]
    model_ids = [str(row.get("id")) for row in rows if isinstance(row, dict)]
    selected_ids = [str(row["model"]) for row in CONFIGURATIONS]
    selected_entries: list[Json] = []
    for model_id in selected_ids:
        matches = [row for row in rows if isinstance(row, dict) and row.get("id") == model_id]
        if len(matches) != 1:
            fail(f"authenticated catalog does not contain exactly one {model_id} entry")
        row = matches[0]
        selected_entries.append(
            {
                key: row[key]
                for key in ("id", "object", "owned_by", "created")
                if key in row and isinstance(row[key], (str, int, float, bool))
            }
        )
    return {
        "schema_version": "1.0.0",
        "status": "CREDENTIAL_AUTHENTICATED_MODEL_CATALOG_SNAPSHOT",
        "fetched_at_utc": utc_now(),
        "endpoint": CATALOG_URL,
        "http_status": 200,
        "catalog_response_sha256": sha256_bytes(raw),
        "model_count": len(model_ids),
        "model_ids": model_ids,
        "selected_model_ids": selected_ids,
        "selected_model_entries": selected_entries,
        "credentials_retained": False,
        "account_identifiers_retained": False,
        "provider_response_identifiers_retained": False,
        "contains_model_outputs": False,
    }


def build_plan(catalog_path: Path, schedule_path: Path, schedule: Json) -> Json:
    packet = load_json(PACKET_PATH)
    pairs = load_json(DATASET_ROOT / "pairs.json")
    gold = load_jsonl(DATASET_ROOT / "gold.jsonl")
    if not isinstance(pairs, list):
        fail("balanced pair file is not a list")
    items = selected_item_ids(pairs)
    actions = selected_action_counts(gold, items)
    if actions != {"ALLOW": 15, "HOLD": 5, "DEMOTE": 5, "ESCALATE": 5}:
        fail(f"factor-complete action balance changed: {dict(actions)}")
    lanes = expanded_lanes()
    cost_upper = conservative_cost_upper_bound_usd()
    if cost_upper >= 7.0:
        fail(f"conservative quota bound is unexpectedly high: {cost_upper}")
    return {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "truth_status": "OPEN",
        "frozen_at_utc": utc_now(),
        "purpose": (
            "A factor-complete, repeated route-breadth screen on the already public balanced "
            "challenge using seven newly configured OpenCode Go routes."
        ),
        "interpretation_boundary": (
            "This is a public robustness screen over one deterministic witness per registered "
            "factor. It is not a hidden-generalization estimate, deployment study, model-family "
            "ranking, or causal ablation of weights, provider, API, time, or output adapter."
        ),
        "design": {
            "analysis_split": "PUBLIC_PRECOMMITTED_FACTOR_COMPLETE_ROUTE_BREADTH",
            "public_before_inference": True,
            "selection_uses_prior_benchmark_outputs": False,
            "selection_rule": "LEXICOGRAPHICALLY_FIRST_PAIR_PER_REGISTERED_FACTOR",
            "factors": 15,
            "selected_pairs": 15,
            "selected_items": 30,
            "configurations": len(CONFIGURATIONS),
            "replications_per_configuration": REPLICATIONS,
            "planned_model_item_cells": schedule["planned_cells"],
            "primary_replication": 1,
            "secondary_repeated_route_analysis": [1, 2, 3],
            "historical_anchor_routes_reissued": False,
            "completed_singleton_workflow_rerun": False,
            "held_out_generalization_claim": False,
            "naturalistic_case_count": 0,
        },
        "prestudy_adapter_smoke_disclosure": {
            "requests": 9,
            "benchmark_prompts_used": False,
            "benchmark_labels_used": False,
            "accuracy_observed_or_used": False,
            "purpose": "Credential and endpoint-shape checks with a trivial exact-JSON echo.",
            "selection_effect": (
                "Only catalog presence, privacy terms, family coverage, and adapter viability were "
                "used. No benchmark output informed configuration or item selection."
            ),
            "retained_as_study_evidence": False,
        },
        "catalog": {
            "path": catalog_path.relative_to(ROOT).as_posix(),
            "file_sha256": sha256_file(catalog_path),
            "selected_before_benchmark_outputs": True,
            "selected_model_ids": [str(row["model"]) for row in CONFIGURATIONS],
        },
        "dataset": {
            "path": DATASET_ROOT.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256_file(DATASET_ROOT / "manifest.json"),
            "pairs_file_sha256": sha256_file(DATASET_ROOT / "pairs.json"),
            "gold_file_sha256": sha256_file(DATASET_ROOT / "gold.jsonl"),
            "selected_pair_ids": [str(row["pair_id"]) for row in selected_pairs(pairs)],
            "selected_item_ids": items,
            "selected_gold_action_counts": dict(sorted(actions.items())),
            "public_before_inference": True,
        },
        "prompt": {
            "path": PACKET_PATH.relative_to(ROOT).as_posix(),
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(PACKET_PATH),
            "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
            "output_contract": (
                "PROMPT_ONLY_JSON_PLUS_DETERMINISTIC_SINGLE_OBJECT_EXTRACTION_AND_LOCAL_SCHEMA_"
                "VALIDATION"
            ),
            "same_prompt_bytes_for_every_configuration": True,
        },
        "formal_lanes": lanes,
        "historical_anchors": [
            {
                "lane_id": "opencode-go-qwen3.7-max",
                "model": "qwen3.7-max",
                "model_family": "Qwen",
                "run_path": (
                    "v2/balanced-public-challenge/results/runs/opencode-go-qwen3.7-max-full.jsonl"
                ),
                "reissued": False,
            },
            {
                "lane_id": "opencode-go-deepseek-v4-flash-matched",
                "model": "deepseek-v4-flash",
                "model_family": "DeepSeek",
                "run_path": (
                    "v2/balanced-public-challenge/results/runs/"
                    "opencode-go-deepseek-v4-flash-matched-full.jsonl"
                ),
                "reissued": False,
            },
        ],
        "execution": {
            "schedule_path": schedule_path.relative_to(ROOT).as_posix(),
            "schedule_file_sha256": sha256_file(schedule_path),
            "schedule_sha256": schedule["schedule_sha256"],
            "grouping_rule": "ONE_ITEM_REPLICATION_GROUP_WITH_ONE_CELL_PER_CONFIGURATION",
            "group_lane_rotation": "CYCLIC_BY_ZERO_BASED_GROUP_INDEX",
            "max_concurrent_requests": len(CONFIGURATIONS),
            "minimum_inter_group_interval_seconds": 0.1,
            "default_timeout_seconds": 240,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "interruption_rule": (
                "Seal ambiguous and unattempted cells as incorrect without resuming the schedule."
            ),
            "quota_exhaustion": "TERMINAL_TRANSPORT_ERROR_NO_RETRY",
        },
        "budget": {
            "authorization_scope": "USER_AUTHORIZED_AVAILABLE_OPENCODE_GO_USAGE",
            "incremental_cash_cap_usd": 0.0,
            "subscription_quota_only": True,
            "use_balance_after_subscription_limit": False,
            "workflow_initiated_purchase_or_recharge": False,
            "official_limit_source": "https://opencode.ai/docs/go/",
            "official_limit_checked_at": "2026-08-25",
            "five_hour_usage_limit_usd": 12.0,
            "weekly_usage_limit_usd": 30.0,
            "monthly_usage_limit_usd": 60.0,
            "conservative_input_tokens_per_call": 5000,
            "max_output_tokens_per_call": MAX_OUTPUT_TOKENS,
            "conservative_schedule_quota_value_upper_bound_usd": cost_upper,
            "actual_usage_value": "POSTHOC_DESCRIPTIVE_ONLY_NOT_CASH_SPEND",
        },
        "statistics": {
            "primary": (
                "Replication-one end-to-end item accuracy, pair accuracy, decision coverage, "
                "complete four-by-five confusion matrix, and per-action recall."
            ),
            "secondary": (
                "Pooled three-replication endpoints, per-replication endpoints, and all-three "
                "valid/correct stability for each item and pair."
            ),
            "failure_rule": (
                "Every transport, syntax, schema, semantic, adapter, timeout, quota, ambiguous, "
                "and unattempted cell remains incorrect in its registered end-to-end denominator."
            ),
            "pair_rule": "A pair is correct only when both members are valid and correct.",
            "comparison_boundary": (
                "Configurations are descriptive route stacks; model identity, provider, API, "
                "serving state, time, and output implementation are not causally isolated."
            ),
        },
        "reporting": {
            "retain_final_raw_response_text_private": True,
            "retain_provider_response_id": False,
            "retain_hidden_reasoning_content": False,
            "release_public_safe_terminal_records_after_privacy_scan": True,
            "raw_model_outputs_in_aggregate": False,
        },
        "runtime_source_sha256": {
            relative: sha256_file(ROOT / relative) for relative in RUNTIME_SOURCES
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-env", default="OPENCODE_GO_API_KEY")
    parser.add_argument("--out-dir", type=Path, default=STUDY_ROOT)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    if output != STUDY_ROOT:
        fail(f"study output must be {STUDY_ROOT}")
    api_key = os.environ.get(args.api_key_env)
    if not api_key or api_key != api_key.strip():
        fail(f"{args.api_key_env} is absent or malformed")
    targets = [
        output / "catalog-snapshot.json",
        output / "request-schedule.json",
        output / "study-plan.json",
    ]
    if any(path.exists() for path in targets):
        fail("refusing to overwrite an existing frozen artifact")
    raw, catalog_value = fetch_catalog(api_key)
    write_new_json(targets[0], catalog_snapshot(raw, catalog_value))
    packet = load_json(PACKET_PATH)
    pairs = load_json(DATASET_ROOT / "pairs.json")
    if not isinstance(pairs, list):
        fail("balanced pair file is not a list")
    provisional = {"formal_lanes": expanded_lanes()}
    schedule = schedule_payload(provisional, packet, pairs)
    write_new_json(targets[1], schedule)
    write_new_json(targets[2], build_plan(targets[0], targets[1], schedule))
    print(
        json.dumps(
            {
                "status": "FROZEN_BEFORE_SCORED_INFERENCE",
                "study_id": STUDY_ID,
                "configurations": len(CONFIGURATIONS),
                "replications": REPLICATIONS,
                "cells": schedule["planned_cells"],
                "quota_upper_bound_usd": conservative_cost_upper_bound_usd(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
