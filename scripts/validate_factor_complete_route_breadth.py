#!/usr/bin/env python3
"""Validate the factor-complete route-breadth freeze without loading credentials."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_complete_route_breadth import (  # noqa: E402
    BASE_URL,
    CATALOG_URL,
    CONFIGURATIONS,
    DATASET_ROOT,
    MAX_OUTPUT_TOKENS,
    PACKET_PATH,
    REPLICATIONS,
    STUDY_ID,
    conservative_cost_upper_bound_usd,
    expanded_lanes,
    lane_id,
    request_body,
    selected_action_counts,
    selected_item_ids,
    selected_pairs,
)

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def fail(message: str) -> None:
    raise ValueError(f"factor-complete route-breadth validation: {message}")


def git_blob_sha256(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"cannot read frozen source from commit: {relative}")
    return sha256_bytes(result.stdout)


def validate_study(
    plan_path: Path,
    schedule_path: Path,
    *,
    frozen_plan_commit: str | None = None,
) -> Json:
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(PACKET_PATH)
    pairs = load_json(DATASET_ROOT / "pairs.json")
    gold = load_jsonl(DATASET_ROOT / "gold.jsonl")
    if not isinstance(pairs, list):
        fail("balanced pair file is not a list")
    if (
        plan.get("study_id") != STUDY_ID
        or plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "OPEN"
    ):
        fail("plan identity or pre-inference status changed")
    design = plan.get("design", {})
    if (
        design.get("analysis_split") != "PUBLIC_PRECOMMITTED_FACTOR_COMPLETE_ROUTE_BREADTH"
        or design.get("public_before_inference") is not True
        or design.get("selection_uses_prior_benchmark_outputs") is not False
        or design.get("factors") != 15
        or design.get("selected_pairs") != 15
        or design.get("selected_items") != 30
        or design.get("configurations") != len(CONFIGURATIONS)
        or design.get("replications_per_configuration") != REPLICATIONS
        or design.get("planned_model_item_cells") != 630
        or design.get("primary_replication") != 1
        or design.get("historical_anchor_routes_reissued") is not False
        or design.get("completed_singleton_workflow_rerun") is not False
        or design.get("held_out_generalization_claim") is not False
    ):
        fail("design boundary changed")

    selected = selected_pairs(pairs)
    item_ids = selected_item_ids(pairs)
    actions = selected_action_counts(gold, item_ids)
    if actions != Counter({"ALLOW": 15, "HOLD": 5, "DEMOTE": 5, "ESCALATE": 5}):
        fail("selected action balance changed")
    dataset = plan.get("dataset", {})
    if (
        dataset.get("manifest_sha256") != sha256_file(DATASET_ROOT / "manifest.json")
        or dataset.get("pairs_file_sha256") != sha256_file(DATASET_ROOT / "pairs.json")
        or dataset.get("gold_file_sha256") != sha256_file(DATASET_ROOT / "gold.jsonl")
        or dataset.get("selected_pair_ids") != [str(row["pair_id"]) for row in selected]
        or dataset.get("selected_item_ids") != item_ids
        or dataset.get("selected_gold_action_counts") != dict(sorted(actions.items()))
        or dataset.get("public_before_inference") is not True
    ):
        fail("dataset selection or source binding changed")
    prompt = plan.get("prompt", {})
    if (
        prompt.get("path") != PACKET_PATH.relative_to(ROOT).as_posix()
        or prompt.get("packet_sha256") != packet.get("packet_sha256")
        or prompt.get("packet_file_sha256") != sha256_file(PACKET_PATH)
        or prompt.get("dataset_manifest_sha256") != packet.get("dataset_manifest_sha256")
        or prompt.get("same_prompt_bytes_for_every_configuration") is not True
    ):
        fail("prompt binding changed")

    catalog_path = ROOT / str(plan.get("catalog", {}).get("path"))
    catalog = load_json(catalog_path)
    expected_models = [str(row["model"]) for row in CONFIGURATIONS]
    if (
        plan["catalog"].get("file_sha256") != sha256_file(catalog_path)
        or plan["catalog"].get("selected_model_ids") != expected_models
        or plan["catalog"].get("selected_before_benchmark_outputs") is not True
        or catalog.get("status") != "CREDENTIAL_AUTHENTICATED_MODEL_CATALOG_SNAPSHOT"
        or catalog.get("endpoint") != CATALOG_URL
        or catalog.get("http_status") != 200
        or catalog.get("selected_model_ids") != expected_models
        or not set(expected_models).issubset(set(catalog.get("model_ids", [])))
        or catalog.get("credentials_retained") is not False
        or catalog.get("account_identifiers_retained") is not False
        or catalog.get("provider_response_identifiers_retained") is not False
        or catalog.get("contains_model_outputs") is not False
    ):
        fail("catalog selection or privacy boundary changed")

    lanes = plan.get("formal_lanes")
    expected_lanes = expanded_lanes()
    if lanes != expected_lanes:
        fail("expanded lane declarations changed")
    lane_by_id = {str(row["lane_id"]): row for row in lanes}
    if len(lane_by_id) != 21:
        fail("formal lane IDs are not unique")
    for lane in lanes:
        if (
            lane.get("provider") != "OpenCode Go"
            or lane.get("base_url") != BASE_URL
            or lane.get("auth_env") != "OPENCODE_GO_API_KEY"
            or lane.get("response_format") != "prompt_only_json"
            or lane.get("allow_single_json_object_extraction") is not True
            or lane.get("max_output_tokens") != MAX_OUTPUT_TOKENS
            or lane.get("billing_mode") != "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA"
        ):
            fail(f"lane contract changed: {lane.get('lane_id')}")

    if schedule_path != ROOT / str(plan.get("execution", {}).get("schedule_path")):
        fail("schedule path binding changed")
    if sha256_file(schedule_path) != plan["execution"].get("schedule_file_sha256"):
        fail("schedule file digest changed")
    schedule_copy = deepcopy(schedule)
    observed_schedule_sha = schedule_copy.pop("schedule_sha256", None)
    if observed_schedule_sha != sha256_bytes(canonical_json(schedule_copy).encode("utf-8")):
        fail("schedule self-digest is invalid")
    configuration_order = [str(row["configuration_id"]) for row in CONFIGURATIONS]
    if (
        observed_schedule_sha != plan["execution"].get("schedule_sha256")
        or schedule.get("study_id") != STUDY_ID
        or schedule.get("status") != "FROZEN_BEFORE_MODEL_CALLS"
        or schedule.get("contains_prompts") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_credentials") is not False
        or schedule.get("packet_sha256") != packet.get("packet_sha256")
        or schedule.get("dataset_manifest_sha256") != packet.get("dataset_manifest_sha256")
        or schedule.get("selection_rule") != "LEXICOGRAPHICALLY_FIRST_PAIR_PER_REGISTERED_FACTOR"
        or schedule.get("selected_pair_ids") != dataset.get("selected_pair_ids")
        or schedule.get("selected_item_ids") != item_ids
        or schedule.get("configuration_order") != configuration_order
        or schedule.get("replications") != REPLICATIONS
        or schedule.get("planned_configurations") != len(CONFIGURATIONS)
        or schedule.get("planned_lanes") != 21
        or schedule.get("planned_items_per_lane") != 30
        or schedule.get("planned_groups") != 90
        or schedule.get("planned_cells") != 630
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
    ):
        fail("schedule top-level contract changed")

    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != 630:
        fail("schedule cell count changed")
    seen: set[str] = set()
    lane_counts: Counter[str] = Counter()
    position_counts: dict[str, Counter[int]] = {
        str(configuration["configuration_id"]): Counter() for configuration in CONFIGURATIONS
    }
    for sequence, cell in enumerate(cells):
        if not isinstance(cell, dict) or set(cell) != {
            "sequence",
            "group_index",
            "replication",
            "item_index",
            "within_group_position",
            "cell_id",
            "configuration_id",
            "lane_id",
            "item_id",
            "pair_id",
            "prompt_sha256",
            "request_body_sha256",
        }:
            fail(f"schedule cell schema changed at {sequence}")
        group_index = sequence // len(CONFIGURATIONS)
        within = sequence % len(CONFIGURATIONS)
        replication = group_index // len(item_ids) + 1
        item_index = group_index % len(item_ids)
        rotation = group_index % len(configuration_order)
        rotated = configuration_order[rotation:] + configuration_order[:rotation]
        configuration_id = rotated[within]
        current_lane_id = lane_id(configuration_id, replication)
        item_id = item_ids[item_index]
        packet_row = packet_by_id[item_id]
        if (
            cell["sequence"] != sequence
            or cell["group_index"] != group_index
            or cell["replication"] != replication
            or cell["item_index"] != item_index
            or cell["within_group_position"] != within
            or cell["configuration_id"] != configuration_id
            or cell["lane_id"] != current_lane_id
            or cell["item_id"] != item_id
            or cell["cell_id"] != f"{current_lane_id}/{item_id}"
            or cell["cell_id"] in seen
            or cell["pair_id"] != packet_row["pair_id"]
            or cell["prompt_sha256"] != packet_row["prompt_sha256"]
            or cell["request_body_sha256"]
            != sha256_bytes(
                canonical_json(
                    request_body(lane_by_id[current_lane_id], str(packet_row["prompt"]))
                ).encode("utf-8")
            )
        ):
            fail(f"schedule ordering or request binding changed at {sequence}")
        seen.add(str(cell["cell_id"]))
        lane_counts[current_lane_id] += 1
        position_counts[configuration_id][within] += 1
    if lane_counts != Counter({lane: 30 for lane in lane_by_id}):
        fail("schedule is not exactly 30 cells per lane-replication")
    if any(max(counts.values()) - min(counts.values()) > 1 for counts in position_counts.values()):
        fail("cyclic configuration positions are imbalanced")

    execution = plan.get("execution", {})
    if (
        execution.get("max_concurrent_requests") != len(CONFIGURATIONS)
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume") != "FORBIDDEN"
        or execution.get("quota_exhaustion") != "TERMINAL_TRANSPORT_ERROR_NO_RETRY"
    ):
        fail("execution boundary changed")
    budget = plan.get("budget", {})
    expected_upper = conservative_cost_upper_bound_usd()
    if (
        budget.get("incremental_cash_cap_usd") != 0.0
        or budget.get("subscription_quota_only") is not True
        or budget.get("use_balance_after_subscription_limit") is not False
        or budget.get("five_hour_usage_limit_usd") != 12.0
        or budget.get("conservative_schedule_quota_value_upper_bound_usd") != expected_upper
        or expected_upper >= budget.get("five_hour_usage_limit_usd", 0)
    ):
        fail("quota boundary changed")
    smoke = plan.get("prestudy_adapter_smoke_disclosure", {})
    if (
        smoke.get("requests") != 9
        or smoke.get("benchmark_prompts_used") is not False
        or smoke.get("benchmark_labels_used") is not False
        or smoke.get("accuracy_observed_or_used") is not False
        or smoke.get("retained_as_study_evidence") is not False
    ):
        fail("prestudy adapter-smoke disclosure changed")

    anchors = plan.get("historical_anchors")
    if not isinstance(anchors, list) or len(anchors) != 2:
        fail("historical anchor declaration changed")
    for anchor in anchors:
        path = ROOT / str(anchor.get("run_path"))
        if not path.is_file() or anchor.get("reissued") is not False:
            fail("historical anchor source changed")

    runtime_hashes = plan.get("runtime_source_sha256")
    if not isinstance(runtime_hashes, dict) or not runtime_hashes:
        fail("runtime source registry is missing")
    changed_sources = [
        relative
        for relative, expected_hash in runtime_hashes.items()
        if sha256_file(ROOT / relative) != expected_hash
    ]
    source_validation = "CURRENT_WORKTREE"
    if changed_sources:
        if frozen_plan_commit is None:
            fail(f"runtime source changed after freeze: {changed_sources[0]}")
        if _COMMIT_RE.fullmatch(frozen_plan_commit) is None:
            fail(f"runtime source changed after freeze: {changed_sources[0]}")
        for bound_path in (plan_path, schedule_path):
            try:
                relative = bound_path.relative_to(ROOT).as_posix()
            except ValueError:
                fail(f"frozen artifact is outside the repository: {bound_path}")
            if git_blob_sha256(frozen_plan_commit, relative) != sha256_file(bound_path):
                fail(f"frozen commit does not bind current artifact: {relative}")
        for relative, expected_hash in runtime_hashes.items():
            if git_blob_sha256(frozen_plan_commit, relative) != expected_hash:
                fail(f"frozen commit source digest changed: {relative}")
        source_validation = "FROZEN_COMMIT"
    return {
        "status": "FACTOR_COMPLETE_ROUTE_BREADTH_FREEZE_VALID",
        "study_id": STUDY_ID,
        "configurations": len(CONFIGURATIONS),
        "replications": REPLICATIONS,
        "pairs": 15,
        "items": 30,
        "cells": 630,
        "quota_upper_bound_usd": expected_upper,
        "schedule_sha256": observed_schedule_sha,
        "runtime_source_validation": source_validation,
        "credentials_loaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", type=Path, default=ROOT / "v2/factor-complete-route-breadth-v2/study-plan.json"
    )
    parser.add_argument(
        "--schedule",
        type=Path,
        default=ROOT / "v2/factor-complete-route-breadth-v2/request-schedule.json",
    )
    parser.add_argument("--frozen-plan-commit")
    args = parser.parse_args()
    print(
        canonical_json(
            validate_study(
                args.plan.resolve(),
                args.schedule.resolve(),
                frozen_plan_commit=args.frozen_plan_commit,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
