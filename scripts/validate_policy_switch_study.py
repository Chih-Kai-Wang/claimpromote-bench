#!/usr/bin/env python3
"""Validate the counterfactual policy dataset and prospective execution freeze."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_policy_switch_study import (  # noqa: E402
    BASE_POLICY_PATH,
    DECISION_SCHEMA,
    SOURCE_REGISTRY,
    SWITCH_POLICY_PATH,
    changed_paths,
    render_prompt,
)
from freeze_slsa_portability_study import request_body  # noqa: E402
from policy_switch import evaluate_policy_switch, load_switch_policy  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402

from claimpromotebench.hashing import (  # noqa: E402
    canonical_json,
    sha256_bytes,
    sha256_file,
)

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        fail(f"{path} contains a non-object row")
    return rows


def validate_dataset(dataset_root: Path) -> Json:
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    switch_policy = load_switch_policy(SWITCH_POLICY_PATH, base_policy)
    if manifest.get("status") != "SYNTHETIC_COUNTERFACTUAL_POLICY_SWITCH_DATASET":
        fail("dataset manifest status differs")
    if packet.get("study_id") != manifest.get("study_id"):
        fail("prompt packet and manifest study IDs differ")
    if packet.get("contains_gold") is not False or packet.get("contains_credentials") is not False:
        fail("prompt packet scope differs")

    expected_sizes = {"development": (72, 36), "evaluation": (120, 60)}
    expected_actions = {
        "development": Counter({"ALLOW": 36, "HOLD": 12, "DEMOTE": 12, "ESCALATE": 12}),
        "evaluation": Counter({"ALLOW": 60, "HOLD": 20, "DEMOTE": 20, "ESCALATE": 20}),
    }
    split_rows: dict[str, tuple[list[Json], list[Json], list[Json]]] = {}
    for split, (item_count, pair_count) in expected_sizes.items():
        items = load_jsonl(dataset_root / f"{split}-items.jsonl")
        gold = load_jsonl(dataset_root / f"{split}-gold.jsonl")
        pairs_value = json.loads((dataset_root / f"{split}-pairs.json").read_text(encoding="utf-8"))
        if not isinstance(pairs_value, list) or not all(
            isinstance(row, dict) for row in pairs_value
        ):
            fail(f"{split} pairs are malformed")
        pairs: list[Json] = pairs_value
        if len(items) != item_count or len(gold) != item_count or len(pairs) != pair_count:
            fail(f"{split} coverage differs")
        items_by_id = {str(row["id"]): row for row in items}
        gold_by_id = {str(row["id"]): row for row in gold}
        if len(items_by_id) != item_count or set(items_by_id) != set(gold_by_id):
            fail(f"{split} item and gold IDs differ or repeat")
        observed_actions: Counter[str] = Counter()
        member_ids: set[str] = set()
        for pair in pairs:
            ids = [str(value) for value in pair.get("member_ids", [])]
            if (
                len(ids) != 2
                or len(set(ids)) != 2
                or pair.get("controlled_path") != "/active_policy_profile"
            ):
                fail(f"malformed pair contract: {pair.get('pair_id')}")
            if set(ids) - set(items_by_id) or member_ids & set(ids):
                fail(f"pair membership differs: {pair.get('pair_id')}")
            member_ids.update(ids)
            left = items_by_id[ids[0]]["model_visible"]
            right = items_by_id[ids[1]]["model_visible"]
            if changed_paths(left, right) != ["/active_policy_profile"]:
                fail(f"pair changes more than the policy profile: {pair.get('pair_id')}")
            pair_actions: list[str] = []
            for item_id in ids:
                gold_row = gold_by_id[item_id]
                decision = evaluate_policy_switch(
                    items_by_id[item_id]["model_visible"], switch_policy, base_policy
                )
                if gold_row.get("decision") != decision:
                    fail(f"gold differs from policy executor: {item_id}")
                action = str(decision["action"])
                observed_actions[action] += 1
                pair_actions.append(action)
            if "ALLOW" not in pair_actions or len(set(pair_actions)) != 2:
                fail(
                    "pair does not require a policy-conditioned action change: "
                    f"{pair.get('pair_id')}"
                )
        if member_ids != set(items_by_id) or observed_actions != expected_actions[split]:
            fail(f"{split} support differs")
        split_rows[split] = (items, gold, pairs)

    evaluation_items = split_rows["evaluation"][0]
    profile_counts = Counter(
        str(row["model_visible"]["active_policy_profile"]) for row in evaluation_items
    )
    if profile_counts != Counter({"POLICY_BLUE": 60, "POLICY_AMBER": 60}):
        fail("evaluation profile support differs")
    packet_records = packet.get("records")
    if not isinstance(packet_records, list) or len(packet_records) != 120:
        fail("prompt packet coverage differs")
    item_by_id = {str(row["id"]): row for row in evaluation_items}
    if {str(row["item_id"]) for row in packet_records} != set(item_by_id):
        fail("prompt packet item IDs differ")
    for row in packet_records:
        item_id = str(row["item_id"])
        prompt = render_prompt(item_by_id[item_id]["model_visible"], base_policy, switch_policy)
        if row.get("prompt") != prompt or row.get("prompt_sha256") != sha256_bytes(
            prompt.encode("utf-8")
        ):
            fail(f"prompt differs from deterministic rendering: {item_id}")
    packet_payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if packet.get("packet_sha256") != sha256_bytes(canonical_json(packet_payload).encode("utf-8")):
        fail("prompt packet self-digest differs")

    named_files = (
        "development-gold.jsonl",
        "development-items.jsonl",
        "development-pairs.json",
        "evaluation-gold.jsonl",
        "evaluation-items.jsonl",
        "evaluation-pairs.json",
    )
    observed_hashes = {name: sha256_file(dataset_root / name) for name in named_files}
    if manifest.get("data_file_sha256") != observed_hashes:
        fail("dataset file hashes differ")
    fingerprint = sha256_bytes(
        canonical_json(
            {
                "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
                "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
                "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "data_file_sha256": observed_hashes,
            }
        ).encode("utf-8")
    )
    if manifest.get("dataset_fingerprint") != fingerprint:
        fail("dataset fingerprint differs")
    if packet.get("dataset_fingerprint") != fingerprint:
        fail("packet dataset fingerprint differs")
    if manifest.get("packet_sha256") != packet.get("packet_sha256"):
        fail("manifest packet digest differs")
    if manifest.get("packet_file_sha256") != sha256_file(
        dataset_root / "evaluation-prompt-packet.json"
    ):
        fail("manifest packet-file digest differs")
    return {
        "status": "POLICY_SWITCH_DATASET_VALID",
        "development_items": 72,
        "evaluation_items": 120,
        "evaluation_pairs": 60,
        "dataset_fingerprint": fingerprint,
    }


def validate_baselines(dataset_root: Path, baseline_root: Path) -> Json:
    report = load_object(baseline_root / "report.json")
    if report.get("status") != "FROZEN_DEVELOPMENT_TRAINED_POLICY_SWITCH_COMPARATORS":
        fail("baseline report status differs")
    if (
        report.get("evaluation_gold_loaded") is not False
        or report.get("model_outputs_loaded") is not False
    ):
        fail("baseline data-access boundary differs")
    evaluation_ids = {str(row["id"]) for row in load_jsonl(dataset_root / "evaluation-items.jsonl")}
    pairs_value = json.loads((dataset_root / "evaluation-pairs.json").read_text(encoding="utf-8"))
    if not isinstance(pairs_value, list):
        fail("evaluation pairs are malformed")
    pairs: list[Json] = pairs_value
    prediction_counts: Json = {}
    for comparator_id in ("policy_aware", "profile_blind"):
        path = baseline_root / f"{comparator_id}-predictions.jsonl"
        rows = load_jsonl(path)
        if len(rows) != 120 or {str(row["item_id"]) for row in rows} != evaluation_ids:
            fail(f"{comparator_id} prediction coverage differs")
        expected_hash = report["comparators"][comparator_id]["predictions_sha256"]
        if expected_hash != sha256_file(path):
            fail(f"{comparator_id} prediction digest differs")
        prediction_counts[comparator_id] = len(rows)
        if comparator_id == "profile_blind":
            action_by_id = {str(row["item_id"]): str(row["predicted_action"]) for row in rows}
            for pair in pairs:
                ids = [str(value) for value in pair["member_ids"]]
                if action_by_id[ids[0]] != action_by_id[ids[1]]:
                    fail("profile-blind comparator changes action within an identical-feature pair")
    return {
        "status": "POLICY_SWITCH_BASELINES_VALID",
        "prediction_counts": prediction_counts,
        "evaluation_gold_loaded": False,
    }


def validate_freeze(
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
) -> Json:
    dataset_report = validate_dataset(dataset_root)
    baseline_report = validate_baselines(dataset_root, baseline_root)
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("plan status is not frozen")
    if plan.get("truth_status") != "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST":
        fail("plan truth status differs")
    if plan.get("study_id") != manifest.get("study_id") or schedule.get("study_id") != plan.get(
        "study_id"
    ):
        fail("study IDs differ across freeze files")
    if plan["dataset"].get("dataset_fingerprint") != manifest.get("dataset_fingerprint"):
        fail("plan dataset fingerprint differs")
    if plan["dataset"].get("manifest_file_sha256") != sha256_file(dataset_root / "manifest.json"):
        fail("plan dataset-manifest digest differs")
    if plan["prompt"].get("packet_sha256") != packet.get("packet_sha256"):
        fail("plan packet digest differs")
    if plan["prompt"].get("packet_file_sha256") != sha256_file(
        dataset_root / "evaluation-prompt-packet.json"
    ):
        fail("plan packet-file digest differs")
    for key, expected_path in (
        ("base_policy_sha256", BASE_POLICY_PATH),
        ("switch_policy_sha256", SWITCH_POLICY_PATH),
        ("registry_sha256", SOURCE_REGISTRY),
    ):
        if plan["sources"].get(key) != sha256_file(expected_path):
            fail(f"plan source digest differs: {key}")
    source_receipt_path = ROOT / str(plan["sources"]["validation_receipt_path"])
    if plan["sources"].get("validation_receipt_sha256") != sha256_file(source_receipt_path):
        fail("source receipt digest differs")
    if load_object(source_receipt_path).get("upstream_sources_verified") is not True:
        fail("source receipt did not verify upstream bytes")

    catalog_path = ROOT / str(plan["catalog"]["path"])
    if plan["catalog"].get("file_sha256") != sha256_file(catalog_path):
        fail("catalog digest differs")
    if load_object(catalog_path).get("selected_model_ids") != [
        "qwen3.7-max",
        "deepseek-v4-flash",
    ]:
        fail("catalog model selection differs")
    if plan["baselines"].get("report_sha256") != sha256_file(baseline_root / "report.json"):
        fail("baseline report digest differs")
    requirements_path = ROOT / str(plan["baselines"]["requirements_path"])
    if plan["baselines"].get("requirements_sha256") != sha256_file(requirements_path):
        fail("baseline requirements digest differs")
    for comparator_id in ("policy_aware", "profile_blind"):
        path = baseline_root / f"{comparator_id}-predictions.jsonl"
        if plan["baselines"]["comparators"][comparator_id]["predictions_sha256"] != sha256_file(
            path
        ):
            fail(f"plan baseline prediction digest differs: {comparator_id}")

    lane_ids = [str(row["lane_id"]) for row in plan["formal_lanes"]]
    if lane_ids != plan["execution"]["base_lane_order"] or len(lane_ids) != 2:
        fail("formal lanes differ from execution order")
    if [str(row["model"]) for row in plan["formal_lanes"]] != [
        "qwen3.7-max",
        "deepseek-v4-flash",
    ]:
        fail("formal model configurations differ")
    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    if schedule.get("schedule_sha256") != schedule_hash:
        fail("schedule self-digest differs")
    if plan["execution"].get("schedule_sha256") != schedule_hash:
        fail("plan schedule digest differs")
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != 240:
        fail("schedule coverage differs")
    if len({str(cell["cell_id"]) for cell in cells}) != 240:
        fail("schedule cell IDs repeat")
    if Counter(str(cell["lane_id"]) for cell in cells) != Counter(
        {lane_id: 120 for lane_id in lane_ids}
    ):
        fail("schedule lane coverage differs")
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    for cell in cells:
        record = packet_by_id[str(cell["item_id"])]
        body = request_body(lanes[str(cell["lane_id"])], str(record["prompt"]))
        if cell.get("request_body_sha256") != sha256_bytes(canonical_json(body).encode("utf-8")):
            fail(f"request body differs: {cell['cell_id']}")
    for path, expected in plan["runtime_source_sha256"].items():
        if sha256_file(ROOT / path) != expected:
            fail(f"runtime source digest differs: {path}")
    if plan["execution"].get("client_retry_count") != 0:
        fail("client retries must remain zero")
    return {
        "status": "POLICY_SWITCH_EXECUTION_FREEZE_VALID",
        "credentials_loaded": False,
        "dataset": dataset_report["status"],
        "baselines": baseline_report["status"],
        "items": 120,
        "lanes": 2,
        "cells": 240,
        "schedule_sha256": schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--schedule", type=Path)
    args = parser.parse_args()
    dataset_root = args.dataset_root.resolve()
    if args.plan is None and args.schedule is None and args.baseline_root is None:
        print(canonical_json(validate_dataset(dataset_root)))
        return 0
    if args.plan is None or args.schedule is None or args.baseline_root is None:
        fail("--plan, --schedule, and --baseline-root must be supplied together")
    report = validate_freeze(
        args.plan.resolve(),
        args.schedule.resolve(),
        dataset_root,
        args.baseline_root.resolve(),
    )
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
