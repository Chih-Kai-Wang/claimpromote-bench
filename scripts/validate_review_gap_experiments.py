#!/usr/bin/env python3
"""Validate frozen reviewer-gap plans without credentials or hosted calls."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from review_gap_experiments import (  # noqa: E402
    BALANCED_PACKET,
    MODELS,
    NONALLOW_DECISION_SCHEMA,
    NONALLOW_REASON_ACTION,
    NONALLOW_ROOT,
    OUTPUT_ROOT,
    REQUEST_SEED,
    REQUEST_TEMPERATURE,
    REQUEST_TOP_P,
    SYNTHETIC_DECISION_SCHEMA,
    output_prompt,
    request_body,
    source_snapshot_path,
)

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"review-gap-validation: {message}")


def verify_commit_bytes(path: Path, commit: str) -> None:
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        fail("frozen commit must be a full lowercase SHA")
    relative = path.relative_to(ROOT).as_posix()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    shown = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0 or shown.returncode != 0 or shown.stdout != path.read_bytes():
        fail(f"frozen bytes are not present at commit: {relative}")


def packet_prompt(packet_row: Json, variant: str, *, output_study: bool) -> str:
    if output_study:
        return output_prompt(str(packet_row["prompt"]), variant)
    prompts = packet_row.get("prompts")
    if not isinstance(prompts, dict) or not isinstance(prompts.get(variant), str):
        fail(f"non-ALLOW packet lacks prompt variant: {variant}")
    return str(prompts[variant])


def verify_embedded_digest(record: Json, field: str, label: str) -> None:
    payload = json.loads(json.dumps(record))
    observed = payload.pop(field, None)
    expected = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if observed != expected:
        fail(f"{label} embedded digest changed")


def current_runtime_environment() -> Json:
    packages = ("attrs", "jsonschema", "jsonschema-specifications", "referencing", "rpds-py")
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in packages},
    }


def validate_frozen(root: Path, frozen_commit: str | None = None) -> Json:
    plan_path = root / "study-plan.json"
    schedule_path = root / "request-schedule.json"
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    if root.resolve() not in {OUTPUT_ROOT.resolve(), NONALLOW_ROOT.resolve()}:
        fail("study root is not registered")
    output_study = root.resolve() == OUTPUT_ROOT.resolve()
    bound_files = {plan_path, schedule_path}
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "OPEN"
        or schedule.get("status") != "FROZEN_BEFORE_SCORED_MODEL_CALLS"
        or plan.get("study_id") != schedule.get("study_id")
        or plan.get("execution", {}).get("client_retry_count") != 0
        or schedule.get("client_retry_count") != 0
        or plan.get("execution", {}).get("partial_resume") != "FORBIDDEN"
        or "voids the entire study"
        not in str(plan.get("execution", {}).get("interruption_rule", ""))
        or plan.get("prior_workflow_rerun") is not False
        or plan.get("budget", {}).get("incremental_cash_spend_observable") is not False
        or plan.get("budget", {}).get("incremental_cash_cap_usd") is not None
    ):
        fail("freeze, zero-retry, or no-rerun boundary changed")
    digest_payload = json.loads(json.dumps(schedule))
    observed_schedule_sha = digest_payload.pop("schedule_sha256", None)
    recomputed_schedule_sha = sha256_bytes(canonical_json(digest_payload).encode("utf-8"))
    if observed_schedule_sha != recomputed_schedule_sha:
        fail("schedule content digest changed")
    if (
        plan["execution"]["schedule_sha256"] != schedule["schedule_sha256"]
        or plan["execution"]["schedule_file_sha256"] != sha256_file(schedule_path)
        or int(schedule["planned_cells"]) != len(schedule["cells"])
        or len({str(row["cell_id"]) for row in schedule["cells"]}) != len(schedule["cells"])
        or any(int(row["sequence"]) != index for index, row in enumerate(schedule["cells"]))
    ):
        fail("schedule binding or coverage changed")
    for relative, expected in plan.get("runtime_sources", {}).items():
        source_path = ROOT / str(relative)
        bound_files.add(source_path)
        if sha256_file(source_path) != expected:
            fail(f"runtime source changed: {relative}")
    if plan.get("runtime_environment") != current_runtime_environment():
        fail("runtime environment differs from the frozen package versions")
    catalog_path = ROOT / str(plan["catalog"]["path"])
    bound_files.add(catalog_path)
    if sha256_file(catalog_path) != plan["catalog"]["file_sha256"]:
        fail("catalog snapshot changed")
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    if len(lanes) != len(plan["formal_lanes"]):
        fail("duplicate lane IDs")
    if any(
        row.get("provider") != "OpenCode Go"
        or row.get("base_url") != "https://opencode.ai/zen/go/v1"
        or row.get("auth_env") != "OPENCODE_GO_API_KEY"
        or row.get("api_kind") != "openai_compatible"
        or row.get("temperature") != REQUEST_TEMPERATURE
        or row.get("top_p") != REQUEST_TOP_P
        or row.get("seed") != REQUEST_SEED
        for row in lanes.values()
    ):
        fail("registered endpoint, adapter, or sampling request changed")
    registered_models = {str(row["model"]) for row in MODELS}
    if {str(row["model"]) for row in lanes.values()} != registered_models:
        fail("registered route aliases changed")
    if output_study:
        packet = load_json(BALANCED_PACKET)
        schema = load_json(SYNTHETIC_DECISION_SCHEMA)
        dataset = ROOT / str(plan["dataset"]["path"])
        dataset_manifest_path = dataset / "manifest.json"
        dataset_manifest = load_json(dataset_manifest_path)
        inputs_path = dataset / "inputs.jsonl"
        pairs_path = dataset / "pairs.json"
        gold_path = dataset / "gold.jsonl"
        bound_files.update(
            {
                BALANCED_PACKET,
                SYNTHETIC_DECISION_SCHEMA,
                dataset_manifest_path,
                inputs_path,
                pairs_path,
                gold_path,
            }
        )
        if (
            sha256_file(dataset_manifest_path) != plan["dataset"]["manifest_sha256"]
            or sha256_file(inputs_path) != dataset_manifest["files"]["inputs.jsonl"]
            or sha256_file(pairs_path) != plan["dataset"]["pairs_sha256"]
            or sha256_file(gold_path) != plan["dataset"]["gold_sha256"]
            or sha256_file(BALANCED_PACKET) != plan["prompt"]["packet_file_sha256"]
            or packet.get("packet_sha256") != plan["prompt"]["packet_sha256"]
            or packet.get("dataset_manifest_sha256") != sha256_file(dataset_manifest_path)
            or sha256_file(SYNTHETIC_DECISION_SCHEMA)
            != plan["prompt"]["decision_schema_sha256"]
        ):
            fail("output-study dataset, packet, or schema binding changed")
        verify_embedded_digest(packet, "packet_sha256", "output packet")
        if len(schedule["cells"]) != 360 or len(lanes) != 12:
            fail("output-ablation size changed")
        if {int(row["max_output_tokens"]) for row in lanes.values()} != {4096, 8192, 12288}:
            fail("output-ablation ceilings changed")
    else:
        packet_path = NONALLOW_ROOT / "prompt-packet.json"
        packet = load_json(packet_path)
        schema = load_json(NONALLOW_DECISION_SCHEMA)
        manifest_path = NONALLOW_ROOT / "dataset" / "manifest.json"
        inputs_path = NONALLOW_ROOT / "dataset" / "inputs.jsonl"
        gold_path = NONALLOW_ROOT / "dataset" / "gold.jsonl"
        pairs_path = NONALLOW_ROOT / "dataset" / "pairs.json"
        mapping_path = NONALLOW_ROOT / "mapping-audit.json"
        source_receipt_path = NONALLOW_ROOT / "source-receipt.json"
        manifest = load_json(manifest_path)
        gold = load_jsonl(gold_path)
        inputs = load_jsonl(inputs_path)
        pairs = load_json(pairs_path)
        mapping = load_json(mapping_path)
        source_receipt = load_json(source_receipt_path)
        bound_files.update(
            {
                packet_path,
                NONALLOW_DECISION_SCHEMA,
                manifest_path,
                inputs_path,
                gold_path,
                pairs_path,
                mapping_path,
                source_receipt_path,
            }
        )
        if (
            sha256_file(manifest_path) != plan["dataset"]["manifest_sha256"]
            or sha256_file(inputs_path) != manifest["inputs_sha256"]
            or sha256_file(gold_path) != manifest["gold_sha256"]
            or sha256_file(pairs_path) != manifest["pairs_sha256"]
            or sha256_file(packet_path) != plan["prompt"]["packet_file_sha256"]
            or packet.get("packet_sha256") != plan["prompt"]["packet_sha256"]
            or packet.get("dataset_manifest_sha256") != sha256_file(manifest_path)
            or sha256_file(NONALLOW_DECISION_SCHEMA)
            != plan["prompt"]["decision_schema_sha256"]
            or sha256_file(source_receipt_path) != plan["sources"]["receipt_sha256"]
            or sha256_file(source_receipt_path) != manifest["source_receipt_sha256"]
        ):
            fail("non-ALLOW dataset, packet, source, or schema binding changed")
        verify_embedded_digest(packet, "packet_sha256", "non-ALLOW packet")
        verify_embedded_digest(mapping, "mapping_audit_sha256", "mapping audit")
        verify_embedded_digest(source_receipt, "receipt_sha256", "source receipt")
        for source in source_receipt.get("sources", []):
            for snapshot in source.get("snapshots", {}).values():
                path = ROOT / str(snapshot["path"])
                bound_files.add(path)
                if sha256_file(path) != snapshot["sha256"]:
                    fail(f"source snapshot changed: {path.name}")
            license_path = ROOT / str(source["license"]["path"])
            bound_files.add(license_path)
            if sha256_file(license_path) != source["license"]["sha256"]:
                fail(f"source license changed: {license_path.name}")
        if (
            len(schedule["cells"]) != 240
            or len(lanes) != 15
            or manifest.get("contains_allow_gold") is not False
            or Counter(str(row["decision"]["action"]) for row in gold)
            != Counter({"HOLD": 6, "ESCALATE": 6, "DEMOTE": 4})
            or len(pairs) != 8
            or sum(not bool(row["changed"]) for row in pairs) != 6
            or sum(bool(row["changed"]) for row in pairs) != 2
        ):
            fail("non-ALLOW support or action balance changed")
        if (
            mapping.get("status") != "AUTHOR_MAPPING_BOUND_BEFORE_SCORED_MODEL_CALLS"
            or mapping.get("items") != 16
            or mapping.get("model_outputs_used") is not False
            or mapping.get("policy_owner_labels") != 0
            or mapping.get("human_annotators") != 0
            or mapping.get("agreement_statistic") is not None
            or manifest.get("mapping_audit_sha256")
            != sha256_file(NONALLOW_ROOT / "mapping-audit.json")
            or plan["dataset"].get("mapping_audit_sha256")
            != sha256_file(NONALLOW_ROOT / "mapping-audit.json")
        ):
            fail("author-mapping audit boundary changed")
        gold_by_id = {str(row["id"]): row["decision"] for row in gold}
        input_by_id = {str(row["id"]): row for row in inputs}
        if set(gold_by_id) != set(input_by_id):
            fail("non-ALLOW input and gold IDs differ")
        for record in mapping.get("records", []):
            item_id = str(record.get("item_id"))
            if (
                item_id not in gold_by_id
                or record.get("mapping_author") != "STUDY_AUTHOR"
                or record.get("policy_owner_label") is not False
                or record.get("human_annotation") is not False
                or record.get("model_output_used") is not False
                or record.get("action") != gold_by_id[item_id]["action"]
                or record.get("reason_codes") != gold_by_id[item_id]["reason_codes"]
                or not isinstance(record.get("mapping_rationale"), str)
                or not str(record["mapping_rationale"]).strip()
            ):
                fail(f"author mapping changed: {item_id}")
            if any(
                NONALLOW_REASON_ACTION.get(str(reason)) != record["action"]
                for reason in record["reason_codes"]
            ):
                fail(f"author mapping reason/action mismatch: {item_id}")
            version = str(input_by_id[item_id]["policy_version"]).lower()
            source_path = source_snapshot_path(str(record["source_id"]), version)
            source_text = source_path.read_text(encoding="utf-8")
            if (
                record.get("source_snapshot_sha256") != sha256_file(source_path)
                or input_by_id[item_id].get("source_snapshot_sha256") != sha256_file(source_path)
            ):
                fail(f"author mapping source digest changed: {item_id}")
            for evidence in record.get("source_evidence", []):
                quote = str(evidence.get("quote", ""))
                start = int(evidence.get("start_line", 0))
                end = int(evidence.get("end_line", 0))
                observed = "\n".join(source_text.splitlines()[start - 1 : end])
                if (
                    not quote
                    or source_text.count(quote) != 1
                    or quote not in observed
                    or evidence.get("quote_sha256")
                    != sha256_bytes(quote.encode("utf-8"))
                ):
                    fail(f"author mapping quote binding changed: {item_id}")
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    group_counts = Counter(int(row["group_index"]) for row in schedule["cells"])
    if set(group_counts.values()) != {3}:
        fail("every request group must contain exactly three model routes")
    groups: dict[int, list[Json]] = defaultdict(list)
    for cell in schedule["cells"]:
        groups[int(cell["group_index"])].append(cell)
    for group_index, rows in groups.items():
        if (
            len({str(row["item_id"]) for row in rows}) != 1
            or len({str(row["condition_id"]) for row in rows}) != 1
            or {int(row["within_group_position"]) for row in rows} != {0, 1, 2}
            or {str(lanes[str(row["lane_id"])]["model"]) for row in rows}
            != registered_models
        ):
            fail(f"request-group counterbalancing changed: {group_index}")
    expected_conditions = {str(row["condition_id"]) for row in plan["conditions"]}
    item_conditions: dict[str, set[str]] = defaultdict(set)
    for cell in schedule["cells"]:
        item_conditions[str(cell["item_id"])].add(str(cell["condition_id"]))
    if any(value != expected_conditions for value in item_conditions.values()):
        fail("an item does not cover every registered condition")
    lane_counts = Counter(str(row["lane_id"]) for row in schedule["cells"])
    expected_lane_count = len(schedule["selected_item_ids"])
    if set(lane_counts.values()) != {expected_lane_count} or set(lane_counts) != set(lanes):
        fail("lane coverage changed")
    for cell in schedule["cells"]:
        item_id = str(cell["item_id"])
        lane_row = lanes[str(cell["lane_id"])]
        prompt = packet_prompt(
            packet_by_id[item_id], str(cell["prompt_variant"]), output_study=output_study
        )
        encoded = prompt.encode("utf-8")
        body = request_body(lane_row, prompt, schema)
        if (
            cell.get("prompt_sha256") != sha256_bytes(encoded)
            or cell.get("prompt_utf8_bytes") != len(encoded)
            or cell.get("request_body_utf8_bytes")
            != len(canonical_json(body).encode("utf-8"))
            or cell.get("request_body_sha256") != sha256_bytes(canonical_json(body).encode("utf-8"))
        ):
            fail(f"frozen request reconstruction changed: {cell['cell_id']}")
    upper = float(plan["budget"]["conservative_schedule_quota_value_upper_bound_usd"])
    margin = float(plan["budget"]["conservative_schedule_quota_value_with_10pct_margin_usd"])
    if upper <= 0 or upper >= 11.5 or abs(margin - upper * 1.1) > 1e-12 or margin >= 12.0:
        fail("registered quota bound is invalid")
    if frozen_commit is not None:
        verify_commit_bytes(plan_path, frozen_commit)
        for path in sorted(bound_files):
            verify_commit_bytes(path, frozen_commit)
    return {
        "status": "FROZEN_REVIEW_GAP_STUDY_VALID",
        "study_id": plan["study_id"],
        "cells": len(schedule["cells"]),
        "lanes": len(lanes),
        "quota_upper_bound_usd": upper,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--frozen-plan-commit")
    args = parser.parse_args()
    print(
        canonical_json(validate_frozen(args.root.resolve(), frozen_commit=args.frozen_plan_commit))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
