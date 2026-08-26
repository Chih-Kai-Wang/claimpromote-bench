#!/usr/bin/env python3
"""Validate the frozen Ox Alpha minimum-route study without loading credentials."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_ox_alpha_minimal_route_study import (  # noqa: E402
    CATALOG_URL,
    DATASET_ROOT,
    EXPECTED_ROOT,
    FAILURE_RULE,
    LANE_ID,
    MINIMAL_SUITE_PATH,
    MODEL_ID,
    RUNTIME_SOURCES,
    STUDY_ID,
    build_schedule,
    request_body,
    self_digest,
)

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"ox-alpha-minimal-route-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate_freeze(plan_path: Path, schedule_path: Path) -> Json:
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(DATASET_ROOT / "manifest.json")
    packet = load_object(DATASET_ROOT / "evaluation-prompt-packet.json")
    suite = load_object(MINIMAL_SUITE_PATH)
    if (
        plan_path.parent != EXPECTED_ROOT
        or schedule_path.parent != EXPECTED_ROOT
        or plan.get("study_id") != STUDY_ID
        or schedule.get("study_id") != STUDY_ID
        or plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST"
        or plan.get("research_role") != "POSTHOC_TIME_STAMPED_AUXILIARY_ROUTE_SMOKE_REPLAY"
    ):
        fail("study identity, path, or truth status changed")

    route = plan.get("route")
    if not isinstance(route, dict):
        fail("route declaration is missing")
    if (
        route.get("lane_id") != LANE_ID
        or route.get("provider") != "OpenCode Go"
        or route.get("base_url") != "https://opencode.ai/zen/go/v1"
        or route.get("api_kind") != "openai_compatible"
        or route.get("auth_env") != "OPENCODE_GO_API_KEY"
        or route.get("model") != MODEL_ID
        or route.get("model_identity_status") != "UNDISCLOSED_STEALTH_MODEL"
        or route.get("response_format") != "prompt_only_json_plus_deterministic_postvalidation"
        or route.get("max_output_tokens") != 4096
        or route.get("sampling_parameters_sent") != []
        or route.get("incremental_cash_cost_usd") != 0.0
    ):
        fail("route identity, adapter, decoding, or cost declaration changed")
    probe_body = request_body(route, "probe")
    if set(probe_body) != {"model", "max_tokens", "messages", "stream"}:
        fail("prompt-only request unexpectedly gained an API-native constraint or sampling field")

    expected_identity_boundary = (
        "Ox Alpha is a stealth label. This study makes no claim about its developer, weights, "
        "architecture, or model family."
    )
    if (
        plan.get("identity_boundary") != expected_identity_boundary
        or "rank providers" not in str(plan.get("reporting_boundary"))
        or "independent policy replication" not in str(plan.get("reporting_boundary"))
    ):
        fail("stealth-model or reporting boundary changed")
    execution = plan.get("execution", {})
    if (
        execution.get("planned_application_posts") != 20
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume") != "FORBIDDEN"
        or execution.get("failure_rule") != FAILURE_RULE
        or plan.get("budget", {}).get("incremental_cash_cap_usd") != 0.0
        or plan.get("budget", {}).get("workflow_initiated_purchase_or_recharge") is not False
    ):
        fail("execution, failure, or budget boundary changed")

    if (
        plan.get("dataset", {}).get("source_study_id") != manifest.get("study_id")
        or plan.get("dataset", {}).get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or plan.get("dataset", {}).get("manifest_file_sha256")
        != sha256_file(DATASET_ROOT / "manifest.json")
        or plan.get("prompt", {}).get("packet_sha256") != packet.get("packet_sha256")
        or plan.get("prompt", {}).get("packet_file_sha256")
        != sha256_file(DATASET_ROOT / "evaluation-prompt-packet.json")
        or plan.get("prompt", {}).get("provider_native_schema_constraint") is not False
    ):
        fail("dataset or prompt binding changed")
    minimum = plan.get("minimum_suite", {})
    if (
        minimum.get("path") != MINIMAL_SUITE_PATH.relative_to(ROOT).as_posix()
        or minimum.get("file_sha256") != sha256_file(MINIMAL_SUITE_PATH)
        or minimum.get("self_digest") != suite.get("self_digest")
        or minimum.get("selected_pairs") != 10
        or minimum.get("selected_items") != 20
        or minimum.get("reachable_edges_covered") != 10
        or minimum.get("changed_rules_covered") != 12
        or suite.get("model_or_client_calls_to_derive") != 0
    ):
        fail("minimum-suite binding or adequacy declaration changed")

    catalog_path = ROOT / str(plan.get("catalog_snapshot", {}).get("path"))
    selection_path = ROOT / str(plan.get("selection_receipt", {}).get("path"))
    catalog = load_object(catalog_path)
    selection = load_object(selection_path)
    if (
        plan["catalog_snapshot"].get("file_sha256") != sha256_file(catalog_path)
        or plan["catalog_snapshot"].get("self_digest") != catalog.get("self_digest")
        or catalog.get("self_digest") != self_digest(catalog)
        or catalog.get("catalog_url") != CATALOG_URL
        or catalog.get("selected_model_entry", {}).get("id") != MODEL_ID
        or catalog.get("contains_credentials") is not False
        or catalog.get("contains_model_outputs") is not False
        or plan["catalog_snapshot"].get("selected_before_model_outputs") is not True
    ):
        fail("preinference public catalog snapshot changed")
    if (
        plan["selection_receipt"].get("file_sha256") != sha256_file(selection_path)
        or plan["selection_receipt"].get("self_digest") != selection.get("self_digest")
        or selection.get("self_digest") != self_digest(selection)
        or selection.get("outcomes_used_for_selection") is not False
        or selection.get("new_model_calls_for_selection") != 0
        or selection.get("conditional_success_subset_allowed") is not False
        or selection.get("selected_item_ids") != suite.get("selected_item_ids")
        or selection.get("selected_pair_ids") != suite.get("selected_pair_ids")
        or selection.get("failure_rule") != FAILURE_RULE
    ):
        fail("preinference route or suite selection receipt changed")

    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    cells = schedule.get("cells")
    if (
        schedule.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_path") != schedule_path.relative_to(ROOT).as_posix()
        or schedule.get("packet_sha256") != packet.get("packet_sha256")
        or schedule.get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or schedule.get("minimum_suite_sha256") != sha256_file(MINIMAL_SUITE_PATH)
        or schedule.get("contains_prompts") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_credentials") is not False
        or not isinstance(cells, list)
        or len(cells) != 20
        or [int(cell["sequence"]) for cell in cells] != list(range(20))
        or len({str(cell["cell_id"]) for cell in cells}) != 20
        or [str(cell["item_id"]) for cell in cells]
        != [str(value) for value in suite["selected_item_ids"]]
        or {str(cell["lane_id"]) for cell in cells} != {LANE_ID}
    ):
        fail("request schedule or zero-disclosure boundary changed")
    expected_schedule = build_schedule(plan, packet, suite)
    if canonical_json(schedule) != canonical_json(expected_schedule):
        fail("schedule differs from a clean deterministic rebuild")

    runtime = plan.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_SOURCES):
        fail("runtime-source inventory changed")
    for relative, expected in runtime.items():
        if sha256_file(ROOT / relative) != expected:
            fail(f"runtime source changed after freeze: {relative}")
    return {
        "status": "OX_ALPHA_MINIMAL_ROUTE_FREEZE_VALID",
        "credentials_loaded": False,
        "items": 20,
        "pairs": 10,
        "lanes": 1,
        "planned_calls": 20,
        "schedule_sha256": schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=EXPECTED_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=EXPECTED_ROOT / "request-schedule.json")
    args = parser.parse_args()
    print(canonical_json(validate_freeze(args.plan.resolve(), args.schedule.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
