#!/usr/bin/env python3
"""Validate the frozen external agent-policy sources, cases, prompts, and schedule."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from external_agent_policy_revision import (  # noqa: E402
    BASE_URL,
    CASES,
    CATALOG_URL,
    CONFIGURATIONS,
    DATASET_ROOT,
    DECISION_SCHEMA,
    ITEMS_PER_REPLICATION,
    MAX_OUTPUT_TOKENS,
    PACKET_PATH,
    PLANNED_CELLS,
    PLANNED_LANES,
    REPLICATIONS,
    SOURCES,
    STUDY_ID,
    conservative_cost_upper_bound_usd,
    expanded_lanes,
    lane_id,
    request_body,
    source_license_path,
    source_snapshot_path,
)
from freeze_external_agent_policy_revision import (  # noqa: E402
    RUNTIME_SOURCES,
    prompt_for,
    source_by_case,
)

from claimpromotebench.dataset import load_json, load_jsonl, validate_with_schema  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"external agent-policy validation: {message}")


def validate_sources(plan: Json) -> None:
    receipt_path = ROOT / str(plan["sources"]["receipt_path"])
    receipt = load_json(receipt_path)
    receipt_payload = dict(receipt)
    receipt_digest = receipt_payload.pop("receipt_sha256", None)
    if (
        receipt.get("status") != "PINNED_EXTERNAL_AGENT_POLICY_SOURCES_VERIFIED"
        or receipt.get("source_count") != len(SOURCES)
        or receipt.get("prevalence_claimed") is not False
        or receipt.get("credentials_used_or_retained") is not False
        or receipt.get("model_calls") != 0
        or receipt_digest != sha256_bytes(canonical_json(receipt_payload).encode("utf-8"))
        or plan["sources"].get("receipt_sha256") != sha256_file(receipt_path)
    ):
        fail("source receipt identity or scope changed")
    receipt_rows = {str(row["source_id"]): row for row in receipt["sources"]}
    if set(receipt_rows) != {str(row["source_id"]) for row in SOURCES}:
        fail("source receipt set changed")
    for source in SOURCES:
        source_id = str(source["source_id"])
        row = receipt_rows[source_id]
        if (
            row.get("repository") != source["repository"]
            or row.get("path") != source["path"]
            or row.get("change_url") != source["change_url"]
            or row.get("review_url") != source["review_url"]
            or row.get("source_authors_independent_of_study_author") is not True
            or row.get("source_selected_before_case_model_outputs") is not True
        ):
            fail(f"source provenance changed: {source_id}")
        for version in ("before", "after"):
            path = source_snapshot_path(source, version)
            if (
                sha256_file(path) != source[f"{version}_sha256"]
                or row["snapshots"][version]["sha256"] != sha256_file(path)
                or row["snapshots"][version]["commit"] != source[f"{version}_commit"]
            ):
                fail(f"source snapshot changed: {source_id}/{version}")
        license_path = source_license_path(source)
        if (
            sha256_file(license_path) != source["license_sha256"]
            or row["license"]["sha256"] != sha256_file(license_path)
            or row["license"]["spdx"] != source["license_spdx"]
        ):
            fail(f"source license changed: {source_id}")
        before = source_snapshot_path(source, "before").read_text(encoding="utf-8")
        after = source_snapshot_path(source, "after").read_text(encoding="utf-8")
        if source_id == "opa-agent-security-policy":
            required = ("govulncheck", "not considered urgent", "before continuing")
        else:
            required = (
                "backward-compatibility impact",
                "Deprecate, don't rename",
                "stop and flag it to the user",
            )
        if any(token in before or token not in after for token in required):
            fail(f"registered policy addition changed: {source_id}")


def expected_rows() -> tuple[list[Json], list[Json], list[Json], list[Json]]:
    inputs: list[Json] = []
    gold: list[Json] = []
    pairs: list[Json] = []
    packet_records: list[Json] = []
    for case in CASES:
        source = source_by_case(case)
        members: list[str] = []
        for version in ("before", "after"):
            policy_version = version.upper()
            item_id = f"{case['case_id']}-{version}"
            members.append(item_id)
            source_path = source_snapshot_path(source, version)
            prompt = prompt_for(case, version, source_path.read_text(encoding="utf-8"))
            inputs.append(
                {
                    "id": item_id,
                    "pair_id": case["case_id"],
                    "case_id": case["case_id"],
                    "factor_id": case["factor_id"],
                    "source_id": case["source_id"],
                    "policy_version": policy_version,
                    "scenario": case["scenario"],
                    "source_snapshot_sha256": sha256_file(source_path),
                }
            )
            gold.append(
                {
                    "id": item_id,
                    "decision": {
                        "case_id": case["case_id"],
                        "policy_version": policy_version,
                        "action": case[version]["action"],
                        "reason_codes": case[version]["reason_codes"],
                    },
                }
            )
            packet_records.append(
                {
                    "item_id": item_id,
                    "pair_id": case["case_id"],
                    "factor_id": case["factor_id"],
                    "source_id": case["source_id"],
                    "policy_version": policy_version,
                    "prompt": prompt,
                    "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                    "utf8_bytes": len(prompt.encode("utf-8")),
                }
            )
        pairs.append(
            {
                "pair_id": case["case_id"],
                "factor_id": case["factor_id"],
                "family": case["source_id"],
                "source_id": case["source_id"],
                "changed": case["changed"],
                "member_ids": members,
            }
        )
    for rows, key in (
        (inputs, "id"),
        (gold, "id"),
        (pairs, "pair_id"),
        (packet_records, "item_id"),
    ):
        rows.sort(key=lambda row: str(row[key]))
    return inputs, gold, pairs, packet_records


def validate_dataset_and_packet(plan: Json) -> tuple[Json, list[Json], list[Json]]:
    manifest_path = DATASET_ROOT / "manifest.json"
    inputs_path = DATASET_ROOT / "inputs.jsonl"
    gold_path = DATASET_ROOT / "gold.jsonl"
    pairs_path = DATASET_ROOT / "pairs.json"
    manifest = load_json(manifest_path)
    inputs = load_jsonl(inputs_path)
    gold = load_jsonl(gold_path)
    pairs = load_json(pairs_path)
    packet = load_json(PACKET_PATH)
    expected_inputs, expected_gold, expected_pairs, expected_packet = expected_rows()
    if not isinstance(pairs, list):
        fail("pair file is not a list")
    if inputs != expected_inputs or gold != expected_gold or pairs != expected_pairs:
        fail("source-mapped dataset differs from the registered cases")
    if (
        manifest.get("status") != "FROZEN_BEFORE_CASE_MODEL_OUTPUTS"
        or manifest.get("items") != 20
        or manifest.get("pairs") != 10
        or manifest.get("changed_pairs") != 6
        or manifest.get("stable_control_pairs") != 4
        or manifest.get("source_count") != 2
        or manifest.get("inputs_sha256") != sha256_file(inputs_path)
        or manifest.get("gold_sha256") != sha256_file(gold_path)
        or manifest.get("pairs_sha256") != sha256_file(pairs_path)
        or manifest.get("decision_schema_sha256") != sha256_file(DECISION_SCHEMA)
        or manifest.get("model_outputs_used_for_selection_or_labels") is not False
        or manifest.get("deployment_outcome_claimed") is not False
    ):
        fail("dataset manifest changed")
    packet_without_digest = dict(packet)
    packet_digest = packet_without_digest.pop("packet_sha256", None)
    if (
        packet.get("study_id") != STUDY_ID
        or packet.get("status") != "FROZEN_BEFORE_CASE_MODEL_OUTPUTS"
        or packet.get("contains_gold") is not False
        or packet.get("dataset_manifest_sha256") != sha256_file(manifest_path)
        or packet.get("records") != expected_packet
        or packet_digest != sha256_bytes(canonical_json(packet_without_digest).encode("utf-8"))
        or plan["prompt"].get("packet_sha256") != packet_digest
        or plan["prompt"].get("packet_file_sha256") != sha256_file(PACKET_PATH)
    ):
        fail("prompt packet changed")
    for decision in (row["decision"] for row in gold):
        validate_with_schema(decision, DECISION_SCHEMA, str(decision["case_id"]))
    action_counts = Counter(str(row["decision"]["action"]) for row in gold)
    if action_counts != Counter({"ALLOW": 14, "HOLD": 3, "ESCALATE": 2, "DEMOTE": 1}):
        fail(f"gold action support changed: {dict(action_counts)}")
    return packet, gold, pairs


def validate_schedule(plan: Json, schedule: Json, packet: Json) -> None:
    digest_payload = dict(schedule)
    digest = digest_payload.pop("schedule_sha256", None)
    if digest != sha256_bytes(canonical_json(digest_payload).encode("utf-8")):
        fail("schedule self-digest changed")
    if (
        schedule.get("study_id") != STUDY_ID
        or schedule.get("status") != "FROZEN_BEFORE_MODEL_CALLS"
        or schedule.get("contains_prompts") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_credentials") is not False
        or schedule.get("packet_sha256") != packet["packet_sha256"]
        or schedule.get("dataset_manifest_sha256") != packet["dataset_manifest_sha256"]
        or schedule.get("replications") != REPLICATIONS
        or schedule.get("planned_configurations") != len(CONFIGURATIONS)
        or schedule.get("planned_lanes") != PLANNED_LANES
        or schedule.get("planned_items_per_lane") != ITEMS_PER_REPLICATION
        or schedule.get("planned_groups") != ITEMS_PER_REPLICATION * REPLICATIONS
        or schedule.get("planned_cells") != PLANNED_CELLS
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
    ):
        fail("schedule identity or scope changed")
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != PLANNED_CELLS:
        fail("schedule cells are incomplete")
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    configuration_order = [str(row["configuration_id"]) for row in CONFIGURATIONS]
    if schedule.get("configuration_order") != configuration_order:
        fail("schedule configuration order changed")
    item_ids = sorted(packet_by_id)
    lane_counts: Counter[str] = Counter()
    group_counts: Counter[int] = Counter()
    position_counts: dict[str, Counter[int]] = {
        configuration_id: Counter() for configuration_id in configuration_order
    }
    cell_ids: set[str] = set()
    for sequence, cell in enumerate(cells):
        if set(cell) != {
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
            fail(f"schedule cell schema changed: {sequence}")
        current_lane_id = str(cell["lane_id"])
        item_id = str(cell["item_id"])
        group_index = sequence // len(CONFIGURATIONS)
        within = sequence % len(CONFIGURATIONS)
        replication = group_index // len(item_ids) + 1
        item_index = group_index % len(item_ids)
        rotation = group_index % len(configuration_order)
        rotated = configuration_order[rotation:] + configuration_order[:rotation]
        expected_configuration = rotated[within]
        expected_lane = lane_id(expected_configuration, replication)
        expected_item = item_ids[item_index]
        if (
            int(cell["sequence"]) != sequence
            or int(cell["group_index"]) != group_index
            or int(cell["within_group_position"]) != within
            or int(cell["replication"]) != replication
            or int(cell["item_index"]) != item_index
            or cell["configuration_id"] != expected_configuration
            or current_lane_id != expected_lane
            or item_id != expected_item
            or current_lane_id not in lanes
        ):
            fail(f"schedule sequence or lane changed: {sequence}")
        packet_row = packet_by_id[item_id]
        body = request_body(lanes[current_lane_id], str(packet_row["prompt"]))
        if (
            cell["cell_id"] != f"{current_lane_id}/{item_id}"
            or cell["pair_id"] != packet_row["pair_id"]
            or cell["prompt_sha256"] != packet_row["prompt_sha256"]
            or cell["request_body_sha256"] != sha256_bytes(canonical_json(body).encode("utf-8"))
        ):
            fail(f"schedule request binding changed: {sequence}")
        lane_counts[current_lane_id] += 1
        group_counts[int(cell["group_index"])] += 1
        position_counts[expected_configuration][within] += 1
        cell_ids.add(str(cell["cell_id"]))
    if (
        len(cell_ids) != PLANNED_CELLS
        or set(lane_counts.values()) != {ITEMS_PER_REPLICATION}
        or set(group_counts.values()) != {len(CONFIGURATIONS)}
        or any(
            max(counts.values()) - min(counts.values()) > 1 for counts in position_counts.values()
        )
    ):
        fail("schedule balance changed")


def validate_study(plan_path: Path, schedule_path: Path) -> Json:
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    if (
        plan.get("study_id") != STUDY_ID
        or plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "OPEN"
        or plan.get("model_outputs_observed_before_freeze") is not False
        or plan.get("design", {}).get("human_annotators") != 0
        or plan.get("design", {}).get("agreement_statistic") is not None
        or plan.get("design", {}).get("author_policy_mapping") is not True
        or plan.get("design", {}).get("sources") != 2
        or plan.get("design", {}).get("pairs") != 10
        or plan.get("design", {}).get("items_per_replication") != ITEMS_PER_REPLICATION
        or plan.get("design", {}).get("changed_pairs") != 6
        or plan.get("design", {}).get("stable_control_pairs") != 4
        or plan.get("design", {}).get("configurations") != len(CONFIGURATIONS)
        or plan.get("design", {}).get("replications_per_configuration") != REPLICATIONS
        or plan.get("design", {}).get("planned_model_item_cells") != PLANNED_CELLS
        or plan.get("design", {}).get("source_selection_uses_case_outputs") is not False
        or plan.get("design", {}).get("case_selection_uses_case_outputs") is not False
        or plan.get("design", {}).get("labels_use_case_outputs") is not False
        or plan.get("execution", {}).get("client_retry_count") != 0
        or plan.get("execution", {}).get("partial_resume") != "FORBIDDEN"
        or plan.get("execution", {}).get("schedule_sha256") != schedule["schedule_sha256"]
        or plan.get("execution", {}).get("schedule_file_sha256") != sha256_file(schedule_path)
    ):
        fail("study plan identity or boundary changed")
    if plan.get("runtime_source_sha256") != {
        relative: sha256_file(ROOT / relative) for relative in RUNTIME_SOURCES
    }:
        fail("runtime source closure changed")
    catalog_path = ROOT / str(plan.get("catalog", {}).get("path"))
    catalog = load_json(catalog_path)
    expected_models = [str(row["model"]) for row in CONFIGURATIONS]
    if (
        plan["catalog"].get("file_sha256") != sha256_file(catalog_path)
        or plan["catalog"].get("selected_model_ids") != expected_models
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
    if lanes != expanded_lanes():
        fail("formal lane declarations changed")
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
    budget = plan.get("budget", {})
    if (
        budget.get("new_schedule_quota_value_upper_bound_usd")
        != conservative_cost_upper_bound_usd()
        or not isinstance(budget.get("combined_five_hour_upper_bound_usd"), (int, float))
        or float(budget["combined_five_hour_upper_bound_usd"]) >= 12.0
        or budget.get("incremental_cash_cap_usd") != 0.0
        or budget.get("subscription_quota_only") is not True
        or budget.get("use_balance_after_subscription_limit") is not False
        or budget.get("workflow_initiated_purchase_or_recharge") is not False
    ):
        fail("quota boundary changed")
    validate_sources(plan)
    packet, gold, pairs = validate_dataset_and_packet(plan)
    validate_schedule(plan, schedule, packet)
    return {
        "status": "EXTERNAL_AGENT_POLICY_STUDY_VALID",
        "study_id": STUDY_ID,
        "sources": len(SOURCES),
        "pairs": len(pairs),
        "items": len(gold),
        "configurations": len(CONFIGURATIONS),
        "replications": REPLICATIONS,
        "planned_cells": schedule["planned_cells"],
        "combined_five_hour_upper_bound_usd": budget["combined_five_hour_upper_bound_usd"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_json(validate_study(args.plan.resolve(), args.schedule.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
