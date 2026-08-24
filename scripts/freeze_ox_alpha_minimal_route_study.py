#!/usr/bin/env python3
"""Freeze a one-route Ox Alpha replay of the minimum policy-migration smoke suite."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ID = "claimpromotebench-ox-alpha-minimal-route-2026-08-v1"
EXPECTED_ROOT = ROOT / "v2" / "ox-alpha-minimal-route-v1"
DATASET_ROOT = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset"
MINIMAL_SUITE_PATH = ROOT / "v2" / "policy-transition-graph-v1" / "minimal-release-suite.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "route-smoke-run-record.schema.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"
CATALOG_URL = "https://opencode.ai/zen/go/v1/models"
OFFICIAL_DOCS_URL = "https://opencode.ai/docs/go/"
MODEL_ID = "ox-alpha-free"
LANE_ID = "opencode-go-ox-alpha-free-minimal-route-v1"
RUNTIME_SOURCES = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_ox_alpha_minimal_route_study.py",
    "scripts/freeze_ox_alpha_minimal_route_study.py",
    "scripts/run_ox_alpha_minimal_route_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/slsa_policy.py",
    "scripts/validate_ox_alpha_minimal_route_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/decision_validation.py",
    "src/claimpromotebench/hashing.py",
    "v2/policy-transition-graph-v1/frozen/dataset/evaluation-prompt-packet.json",
    "v2/policy-transition-graph-v1/minimal-release-suite.json",
    "v2/schemas/route-smoke-run-record.schema.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
)
FAILURE_RULE = (
    "All service, availability, syntax, schema, semantic, adapter, and rate-limit failures "
    "remain incorrect in the complete 20-item end-to-end denominator. No successful subset "
    "may replace the scheduled route. An interrupted run is ineligible and may not resume."
)


def fail(message: str) -> None:
    raise SystemExit(f"ox-alpha-minimal-route-freeze: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def request_body(lane: Json, prompt: str) -> Json:
    """Build the frozen prompt-only request for the OpenAI-compatible route."""

    return {
        "model": lane["model"],
        "max_tokens": int(lane["max_output_tokens"]),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }


def route_lane() -> Json:
    return {
        "lane_id": LANE_ID,
        "provider": "OpenCode Go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_kind": "openai_compatible",
        "auth_env": "OPENCODE_GO_API_KEY",
        "model": MODEL_ID,
        "model_identity_status": "UNDISCLOSED_STEALTH_MODEL",
        "response_format": "prompt_only_json_plus_deterministic_postvalidation",
        "allow_single_json_object_extraction": True,
        "max_output_tokens": 4096,
        "sampling_parameters_sent": [],
        "billing_mode": "OFFICIAL_LIMITED_TIME_FREE_ROUTE",
        "incremental_cash_cost_usd": 0.0,
    }


def fetch_catalog_snapshot() -> tuple[Json, str]:
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "ClaimPromoteBench/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        fail(f"could not fetch the public model catalog: {exc}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        fail("public model catalog returned non-JSON content")
    rows = value.get("data") if isinstance(value, dict) else None
    matches = [row for row in rows or [] if isinstance(row, dict) and row.get("id") == MODEL_ID]
    if len(matches) != 1:
        fail("public model catalog does not contain exactly one ox-alpha-free entry")
    return matches[0], sha256_bytes(raw)


def build_schedule(plan: Json, packet: Json, suite: Json) -> Json:
    records_by_id = {str(row["item_id"]): row for row in packet["records"]}
    selected_ids = [str(value) for value in suite["selected_item_ids"]]
    lane = plan["route"]
    cells: list[Json] = []
    for item_id in selected_ids:
        record = records_by_id.get(item_id)
        if record is None:
            fail(f"minimum-suite item is absent from the frozen prompt packet: {item_id}")
        body = request_body(lane, str(record["prompt"]))
        cells.append(
            {
                "sequence": len(cells),
                "cell_id": f"{LANE_ID}/{item_id}",
                "lane_id": LANE_ID,
                "item_id": item_id,
                "pair_id": record["pair_id"],
                "prompt_sha256": record["prompt_sha256"],
                "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
            }
        )
    schedule: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "packet_sha256": packet["packet_sha256"],
        "dataset_fingerprint": packet["dataset_fingerprint"],
        "minimum_suite_sha256": sha256_file(MINIMAL_SUITE_PATH),
        "order_rule": "PREEXISTING_MINIMUM_SUITE_ITEM_ORDER",
        "planned_items": 20,
        "planned_lanes": 1,
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return schedule


def freeze(out_root: Path) -> Json:
    expected_files = (
        out_root / "catalog-snapshot.json",
        out_root / "selection-receipt.json",
        out_root / "study-plan.json",
        out_root / "request-schedule.json",
    )
    if out_root != EXPECTED_ROOT or any(path.exists() for path in expected_files):
        fail("freeze root changed or a frozen artifact already exists")

    manifest = load_json(DATASET_ROOT / "manifest.json")
    packet = load_json(DATASET_ROOT / "evaluation-prompt-packet.json")
    suite = load_json(MINIMAL_SUITE_PATH)
    if (
        suite.get("status") != "PROVABLY_MINIMUM_GRAPH_AND_RULE_COMPLETE_SUITE"
        or suite.get("coverage")
        != {
            "changed_rules": {"covered": 12, "total": 12},
            "reachable_edges": {"covered": 10, "total": 10},
        }
        or suite.get("model_or_client_calls_to_derive") != 0
        or len(suite.get("selected_item_ids", [])) != 20
    ):
        fail("minimum suite adequacy certificate changed")
    if packet.get("dataset_fingerprint") != manifest.get("dataset_fingerprint"):
        fail("prompt packet and dataset manifest differ")

    out_root.mkdir(parents=True, exist_ok=True)
    model_entry, raw_catalog_sha256 = fetch_catalog_snapshot()
    catalog: Json = {
        "schema_version": "1.0.0",
        "status": "PREINFERENCE_PUBLIC_CATALOG_SNAPSHOT",
        "retrieved_at_utc": utc_now(),
        "catalog_url": CATALOG_URL,
        "catalog_response_sha256": raw_catalog_sha256,
        "selected_model_entry": model_entry,
        "official_docs_url": OFFICIAL_DOCS_URL,
        "official_docs_observation": (
            "OpenCode lists Ox Alpha Free as a limited-time free OpenCode Go route and reports "
            "that its data are not used for training and retained for zero days."
        ),
        "identity_boundary": (
            "Ox Alpha is a stealth label. This study makes no claim about its developer, "
            "weights, architecture, or model family."
        ),
        "contains_credentials": False,
        "contains_model_outputs": False,
    }
    catalog["self_digest"] = self_digest(catalog)
    catalog_path = out_root / "catalog-snapshot.json"
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    selection: Json = {
        "schema_version": "1.0.0",
        "status": "PREINFERENCE_ROUTE_AND_SUITE_SELECTION",
        "recorded_at_utc": utc_now(),
        "study_id": STUDY_ID,
        "route_label": "OpenCode Go / Ox Alpha Free",
        "route_selected_because": (
            "The user requested an evaluation of the newly listed free route. The route was "
            "not selected from ClaimPromoteBench outcomes."
        ),
        "known_result_boundary": (
            "Prior Qwen and Flash route results were known. No Ox Alpha call had been made by "
            "this study before this freeze."
        ),
        "suite_selection_basis": (
            "Reuse the previously derived ten-pair minimum witness covering all ten reachable "
            "action edges and all twelve authored policy-difference rules."
        ),
        "selected_item_ids": suite["selected_item_ids"],
        "selected_pair_ids": suite["selected_pair_ids"],
        "outcomes_used_for_selection": False,
        "new_model_calls_for_selection": 0,
        "conditional_success_subset_allowed": False,
        "minimum_suite_sha256": sha256_file(MINIMAL_SUITE_PATH),
        "failure_rule": FAILURE_RULE,
    }
    selection["self_digest"] = self_digest(selection)
    selection_path = out_root / "selection-receipt.json"
    selection_path.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    plan: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "truth_status": "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST",
        "frozen_at_utc": utc_now(),
        "research_role": "POSTHOC_TIME_STAMPED_AUXILIARY_ROUTE_SMOKE_REPLAY",
        "route": route_lane(),
        "identity_boundary": catalog["identity_boundary"],
        "dataset": {
            "source_study_id": manifest["study_id"],
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "manifest_file_sha256": sha256_file(DATASET_ROOT / "manifest.json"),
            "evaluation_items": 120,
            "evaluation_pairs": 60,
        },
        "prompt": {
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(DATASET_ROOT / "evaluation-prompt-packet.json"),
            "contract": "ONE_JSON_OBJECT_NO_SURROUNDING_TEXT",
            "deterministic_single_object_extraction": True,
            "provider_native_schema_constraint": False,
        },
        "minimum_suite": {
            "path": MINIMAL_SUITE_PATH.relative_to(ROOT).as_posix(),
            "file_sha256": sha256_file(MINIMAL_SUITE_PATH),
            "self_digest": suite["self_digest"],
            "selected_pairs": 10,
            "selected_items": 20,
            "reachable_edges_covered": 10,
            "changed_rules_covered": 12,
            "interpretation": (
                "A structural smoke gate with one context per reachable edge; not an estimate "
                "of stochastic reliability or generalization."
            ),
        },
        "catalog_snapshot": {
            "path": catalog_path.relative_to(ROOT).as_posix(),
            "file_sha256": sha256_file(catalog_path),
            "self_digest": catalog["self_digest"],
            "selected_before_model_outputs": True,
        },
        "selection_receipt": {
            "path": selection_path.relative_to(ROOT).as_posix(),
            "file_sha256": sha256_file(selection_path),
            "self_digest": selection["self_digest"],
        },
        "execution": {
            "planned_application_posts": 20,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "minimum_global_request_interval_seconds": 0.75,
            "timeout_seconds": 240,
            "interruption_rule": "INCOMPLETE_STUDY_INELIGIBLE_FOR_REPORTING_NO_RESUME",
            "failure_rule": FAILURE_RULE,
        },
        "statistics": {
            "primary_metrics": [
                "end_to_end_item_accuracy",
                "end_to_end_pair_accuracy",
                "decision_coverage",
            ],
            "secondary_metrics": [
                "conditional_item_accuracy_with_coverage",
                "conditional_pair_accuracy_with_coverage",
                "action_recall",
                "confusion_matrix",
            ],
            "strict_smoke_pass_rule": (
                "The route passes only if all 20 scheduled decisions are valid and correct and "
                "all ten controlled pairs are jointly correct."
            ),
        },
        "reporting_boundary": (
            "Report only the time-stamped OpenCode Go route label. Do not infer a model family, "
            "rank providers, treat this as an independent policy replication, or promote the "
            "minimum suite into a reliability estimate."
        ),
        "budget": {
            "authorization_scope": "USER_AUTHORIZED_OPENCODE_EXPERIMENT",
            "official_route_price": "FREE_FOR_LIMITED_TIME",
            "incremental_cash_cap_usd": 0.0,
            "workflow_initiated_purchase_or_recharge": False,
        },
        "privacy": {
            "retain_final_response_text_in_private_repository": True,
            "retain_hidden_reasoning_content": False,
            "retain_provider_response_id": False,
            "anonymous_release_contains_raw_response_text": False,
        },
        "runtime_source_sha256": {path: sha256_file(ROOT / path) for path in RUNTIME_SOURCES},
    }
    schedule = build_schedule(plan, packet, suite)
    plan["execution"]["schedule_path"] = (
        (out_root / "request-schedule.json").relative_to(ROOT).as_posix()
    )
    plan["execution"]["schedule_sha256"] = schedule["schedule_sha256"]
    plan_path = out_root / "study-plan.json"
    schedule_path = out_root / "request-schedule.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schedule_path.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": "OX_ALPHA_MINIMAL_ROUTE_FREEZE_CREATED",
        "study_id": STUDY_ID,
        "items": 20,
        "pairs": 10,
        "planned_calls": 20,
        "model_calls_during_freeze": 0,
        "schedule_sha256": schedule["schedule_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=EXPECTED_ROOT)
    args = parser.parse_args()
    print(canonical_json(freeze(args.out_root.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
