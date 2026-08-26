#!/usr/bin/env python3
"""Validate the upstream policy route-repetition freeze without credentials."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_upstream_policy_route_repetition import (  # noqa: E402
    FAILURE_RULE,
    RUNTIME_SOURCES,
    build_schedule,
    self_digest,
)
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
    STUDY_ID,
    STUDY_ROOT,
    lanes,
    request_body,
)
from validate_upstream_policy_revision_study import validate as validate_source  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-validate: {message}")


def load_object(path: Path) -> Json:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate_freeze(
    plan_path: Path = STUDY_ROOT / "study-plan.json",
    schedule_path: Path = STUDY_ROOT / "request-schedule.json",
) -> Json:
    source_report = validate_source()
    plan_path = plan_path.resolve()
    schedule_path = schedule_path.resolve()
    if plan_path.parent != STUDY_ROOT or schedule_path.parent != STUDY_ROOT:
        fail("freeze files must use the designated study root")
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    packet = load_object(PACKET_PATH)
    expected_lanes = [dict(row) for row in lanes()]
    if (
        plan.get("schema_version") != "1.0.0"
        or plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("study_id") != STUDY_ID
        or schedule.get("study_id") != STUDY_ID
        or plan.get("research_role")
        != "TIME_STAMPED_WITHIN_ROUTE_REPETITION_ON_HISTORICAL_REVISIONS"
    ):
        fail("study identity or freeze status changed")
    if plan.get("formal_lanes") != expected_lanes:
        fail("route identity, adapter, or request protocol changed")
    for lane in expected_lanes:
        body = request_body(lane, "probe")
        if set(body) != {"model", "max_tokens", "messages", "stream"}:
            fail("prompt-only request gained a native constraint or sampling field")

    source = plan.get("source", {})
    if (
        source.get("artifact_manifest_sha256") != sha256_file(SOURCE_MANIFEST_PATH)
        or source.get("packet_sha256") != packet.get("packet_sha256")
        or source.get("packet_file_sha256") != sha256_file(PACKET_PATH)
        or source.get("gold_file_sha256") != sha256_file(GOLD_PATH)
        or source.get("pairs_file_sha256") != sha256_file(PAIRS_PATH)
        or source.get("items") != 24
        or source.get("pairs") != 12
        or source.get("historical_revisions") != 2
        or source.get("source_gold_locked_before_route_outputs") is not True
    ):
        fail("historical source binding changed")
    contract = plan.get("response_contract", {})
    if (
        contract.get("strict_top_level_json_only") is not True
        or contract.get("duplicate_keys_rejected") is not True
        or contract.get("code_fence_or_substring_repair") is not False
        or contract.get("decision_schema_sha256") != sha256_file(DECISION_SCHEMA)
        or contract.get("record_schema_sha256") != sha256_file(RUN_SCHEMA)
    ):
        fail("response contract changed")

    execution = plan.get("execution", {})
    if (
        plan.get("design", {}).get("repetitions") != REPETITIONS
        or plan.get("design", {}).get("same_prompt_packet_each_repetition") is not True
        or plan.get("design", {}).get("selection_uses_new_outputs") is not False
        or execution.get("planned_application_posts") != 144
        or execution.get("base_lane_order") != [str(row["lane_id"]) for row in expected_lanes]
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume") != "FORBIDDEN"
        or execution.get("failure_rule") != FAILURE_RULE
        or plan.get("budget", {}).get("planned_calls_total") != 144
        or plan.get("budget", {}).get("planned_calls_by_model")
        != {"deepseek-v4-flash": 72, "qwen3.7-max": 72}
        or plan.get("budget", {}).get("workflow_initiated_purchase_or_recharge") is not False
    ):
        fail("repeat, denominator, retry, or budget boundary changed")

    catalog_path = ROOT / str(plan.get("catalog_snapshot", {}).get("path"))
    selection_path = ROOT / str(plan.get("selection_receipt", {}).get("path"))
    catalog = load_object(catalog_path)
    selection = load_object(selection_path)
    if (
        plan["catalog_snapshot"].get("file_sha256") != sha256_file(catalog_path)
        or plan["catalog_snapshot"].get("self_digest") != catalog.get("self_digest")
        or catalog.get("self_digest") != self_digest(catalog)
        or catalog.get("status") != "AUTHENTICATED_CATALOG_SNAPSHOT_BEFORE_INFERENCE"
        or catalog.get("catalog_url") != CATALOG_URL
        or catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]
        or [row.get("id") for row in catalog.get("selected_model_entries", [])]
        != ["qwen3.7-max", "deepseek-v4-flash"]
        or catalog.get("credentials_retained") is not False
        or catalog.get("account_identifiers_retained") is not False
        or catalog.get("provider_response_identifiers_retained") is not False
        or catalog.get("model_outputs_available_before_freeze") is not False
    ):
        fail("preinference authenticated catalog snapshot changed")
    if (
        plan["selection_receipt"].get("file_sha256") != sha256_file(selection_path)
        or plan["selection_receipt"].get("self_digest") != selection.get("self_digest")
        or selection.get("self_digest") != self_digest(selection)
        or selection.get("status") != "ROUTES_AND_REPETITIONS_SELECTED_BEFORE_NEW_OUTPUTS"
        or selection.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]
        or selection.get("selected_repetitions") != REPETITIONS
        or selection.get("planned_application_posts") != 144
        or selection.get("new_model_calls_for_selection") != 0
        or selection.get("new_route_outputs_used_for_selection") is not False
        or selection.get("adaptive_stopping_allowed") is not False
        or selection.get("conditional_success_subset_allowed") is not False
        or selection.get("docs_url") != DOCS_URL
        or selection.get("workflow_initiated_purchase_or_recharge") is not False
    ):
        fail("preinference selection or quota boundary changed")

    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    cells = schedule.get("cells")
    lane_ids = [str(row["lane_id"]) for row in expected_lanes]
    if (
        schedule.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_path") != schedule_path.relative_to(ROOT).as_posix()
        or schedule.get("planned_cells") != 144
        or schedule.get("repetitions") != REPETITIONS
        or schedule.get("base_lane_order") != lane_ids
        or schedule.get("packet_sha256") != packet.get("packet_sha256")
        or schedule.get("packet_file_sha256") != sha256_file(PACKET_PATH)
        or schedule.get("contains_prompts") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_credentials") is not False
        or not isinstance(cells, list)
        or len(cells) != 144
        or [int(cell["sequence"]) for cell in cells] != list(range(144))
        or len({str(cell["cell_id"]) for cell in cells}) != 144
        or Counter(str(cell["lane_id"]) for cell in cells)
        != Counter({lane_id: 72 for lane_id in lane_ids})
        or Counter(int(cell["repetition"]) for cell in cells) != Counter({1: 48, 2: 48, 3: 48})
    ):
        fail("request schedule or zero-disclosure boundary changed")
    if canonical_json(schedule) != canonical_json(build_schedule(plan, packet)):
        fail("schedule differs from a clean deterministic rebuild")

    runtime = plan.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_SOURCES):
        fail("runtime-source inventory changed")
    for relative, expected in runtime.items():
        if sha256_file(ROOT / relative) != expected:
            fail(f"runtime source changed after freeze: {relative}")
    for path in (plan_path, schedule_path, catalog_path, selection_path):
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in ACCOUNT_MARKERS:
            if marker.lower() in lowered:
                fail(f"account marker retained in freeze artifact: {path}: {marker}")
    return {
        "status": "UPSTREAM_ROUTE_REPETITION_FREEZE_VALID",
        "credentials_loaded": False,
        "source_pairs": source_report["pairs"],
        "lanes": 2,
        "repetitions": REPETITIONS,
        "planned_calls": 144,
        "schedule_sha256": schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=STUDY_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=STUDY_ROOT / "request-schedule.json")
    args = parser.parse_args()
    print(canonical_json(validate_freeze(args.plan, args.schedule)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
