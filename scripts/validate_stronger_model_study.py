#!/usr/bin/env python3
"""Validate the frozen stronger-model plan, prompt packet, and optional run artifacts."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_dataset,
    validate_with_schema,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
DEFAULT_PLAN = ROOT / "v2" / "stronger-model-study-plan.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"stronger-model-validation: {message}")


def lanes_by_id(plan: Json) -> tuple[dict[str, Json], set[str]]:
    lanes: dict[str, Json] = {}
    formal_ids: set[str] = set()
    for key, formal in (("formal_lanes", True), ("exploratory_lanes", False)):
        rows = plan.get(key)
        if not isinstance(rows, list) or (formal and not rows):
            qualifier = "a non-empty list" if formal else "a list"
            fail(f"plan.{key} must be {qualifier}")
        for lane in rows:
            if not isinstance(lane, dict) or not isinstance(lane.get("lane_id"), str):
                fail(f"plan.{key} contains a malformed lane")
            lane_id = str(lane["lane_id"])
            if lane_id in lanes:
                fail(f"duplicate lane_id: {lane_id}")
            lanes[lane_id] = lane
            if formal:
                formal_ids.add(lane_id)
    return lanes, formal_ids


def validate_plan(plan: Json) -> tuple[dict[str, Json], set[str]]:
    if plan.get("status") not in {
        "DRAFT_NOT_YET_FROZEN",
        "FROZEN_BEFORE_SCORED_INFERENCE",
    }:
        fail("plan has an unknown status")
    if plan.get("truth_status") != "OPEN":
        fail("new study must remain OPEN before validated results")
    lanes, formal_ids = lanes_by_id(plan)
    budget = plan.get("budget")
    if not isinstance(budget, dict):
        fail("plan budget is malformed")
    subscription_quota_only = budget.get("mode") == "PREEXISTING_SUBSCRIPTION_QUOTA_ONLY"
    subscription_or_promo = isinstance(budget.get("incremental_cash_cap_usd"), (int, float))
    if not subscription_or_promo and not isinstance(budget.get("total_paid_cap_usd"), (int, float)):
        fail("plan budget lacks a cash ceiling")
    total_cap = 0.0
    for lane_id in formal_ids:
        lane = lanes[lane_id]
        required_rates = (
            "input_usd_per_million",
            "cached_input_usd_per_million",
            "output_usd_per_million",
        )
        if any(not isinstance(lane.get(key), (int, float)) for key in required_rates):
            fail(f"formal lane lacks frozen descriptive rates: {lane_id}")
        if not isinstance(lane.get("auth_env"), str):
            fail(f"formal lane lacks an auth environment name: {lane_id}")
        if subscription_quota_only:
            if lane.get("spend_cap_usd") is not None:
                fail(f"subscription-only lane reintroduced a token-USD cap: {lane_id}")
        elif not isinstance(lane.get("spend_cap_usd"), (int, float)):
            fail(f"formal lane lacks a frozen spend cap: {lane_id}")
        else:
            total_cap += float(lane["spend_cap_usd"])
    declared_cap = float(
        budget["incremental_cash_cap_usd"]
        if subscription_or_promo
        else budget["total_paid_cap_usd"]
    )
    if not subscription_or_promo and total_cap > declared_cap + 1e-12:
        fail(f"lane caps ${total_cap:.6f} exceed total cap ${declared_cap:.6f}")
    if declared_cap > 10.0 or declared_cap < 0.0:
        fail("declared paid cap exceeds the user-authorized USD 10 ceiling")
    if subscription_quota_only and declared_cap != 0.0:
        fail("subscription-only study must retain a zero incremental-cash cap")
    for lane_id, lane in lanes.items():
        if lane_id not in formal_ids:
            if lane.get("spend_cap_usd") is not None:
                fail(f"exploratory lane must not claim a paid cap: {lane_id}")
            if lane.get("evidence_ceiling") != "LLM_PATH_TESTED_NOT_PROMOTED":
                fail(f"exploratory lane has an unsafe evidence ceiling: {lane_id}")
    pilot = plan.get("pilot")
    if not isinstance(pilot, dict):
        fail("plan pilot is malformed")
    if pilot.get("retry_count") != 0:
        fail("pilot retries must remain disabled")
    requires_pilot = plan.get("design", {}).get("full_requires_pilot", True)
    if not isinstance(requires_pilot, bool):
        fail("plan.design.full_requires_pilot must be Boolean")
    pilot_pairs = pilot.get("pairs")
    pilot_instances = pilot.get("instances")
    if not isinstance(pilot_pairs, list) or not isinstance(pilot_instances, int):
        fail("pilot pairs or instance count is malformed")
    if not requires_pilot and (pilot_pairs or pilot_instances != 0):
        fail("a no-pilot plan must freeze zero pilot pairs and zero pilot instances")
    if plan.get("reporting", {}).get("retain_hidden_reasoning_content") is not False:
        fail("hidden reasoning retention must remain disabled")
    return lanes, formal_ids


def validate_packet(packet: Json, plan: Json, dataset_dir: Path) -> dict[str, Json]:
    observed = packet.get("packet_sha256")
    payload = deepcopy(packet)
    payload.pop("packet_sha256", None)
    recomputed = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if observed != recomputed:
        fail("packet_sha256 does not match the packet content")
    expected = plan.get("prompt", {}).get("expected_packet_sha256")
    if expected is not None and observed != expected:
        fail("packet_sha256 differs from the study plan")
    allowed_packet_bindings = {
        "FROZEN_DATASET_PLUS_DETERMINISTIC_RENDERER",
        "FROZEN_GENERATOR_PLUS_FUTURE_BEACON_SEED_PLUS_DETERMINISTIC_RENDERER_PLUS_C1_RECEIPT",
    }
    if (
        plan.get("status") == "FROZEN_BEFORE_SCORED_INFERENCE"
        and expected is None
        and plan.get("prompt", {}).get("packet_binding") not in allowed_packet_bindings
    ):
        fail("frozen plan lacks a packet digest or deterministic binding rule")
    if packet.get("selection_uses_model_outputs") is not False:
        fail("pilot selection must not use model outputs")
    expected_dataset_manifest = plan["dataset"].get("dataset_manifest_sha256")
    if isinstance(expected_dataset_manifest, str):
        if packet.get("dataset_manifest_sha256") != expected_dataset_manifest:
            fail("packet dataset digest differs from plan")
    elif not (
        expected_dataset_manifest is None
        and plan.get("design", {}).get("dataset_manifest_bound_at_c1") is True
    ):
        fail("plan lacks a dataset digest or registered C1 binding")
    for key in ("policy_sha256", "renderer_sha256", "decision_schema_sha256"):
        if packet.get(key) != plan.get("prompt", {}).get(key):
            fail(f"packet {key} differs from plan")
    records = packet.get("records")
    if not isinstance(records, list):
        fail("packet.records must be a list")
    packet_by_id: dict[str, Json] = {}
    confirmatory_packet = plan.get("design", {}).get("confirmatory_inference_packet", False)
    for row in records:
        if not isinstance(row, dict):
            fail("packet record must be an object")
        item_id = str(row.get("item_id"))
        prompt = row.get("prompt")
        if item_id in packet_by_id:
            fail(f"duplicate packet item_id: {item_id}")
        if not isinstance(prompt, str):
            fail(f"packet prompt is not text: {item_id}")
        encoded = prompt.encode("utf-8")
        if row.get("prompt_sha256") != sha256_bytes(encoded):
            fail(f"packet prompt hash mismatch: {item_id}")
        if row.get("utf8_bytes") != len(encoded):
            fail(f"packet prompt byte count mismatch: {item_id}")
        if confirmatory_packet:
            item = row.get("input_item")
            if not isinstance(item, dict) or str(item.get("id")) != item_id or "gold" in item:
                fail(f"confirmatory packet input boundary is malformed: {item_id}")
            if row.get("input_sha256") != sha256_bytes(canonical_json(item).encode("utf-8")):
                fail(f"confirmatory packet input digest mismatch: {item_id}")
            template_id = row.get("template_id")
            if not isinstance(template_id, str) or not template_id or template_id in prompt:
                fail(f"confirmatory template boundary is malformed: {item_id}")
        packet_by_id[item_id] = row
    dataset_ids = {str(row["id"]) for row in load_jsonl(dataset_dir / "inputs.jsonl")}
    if set(packet_by_id) != dataset_ids:
        fail("packet item IDs differ from the dataset")
    pilot_ids = {str(value) for value in packet.get("pilot_item_ids", [])}
    expected_pilot_ids = {
        str(item_id)
        for row in load_json(dataset_dir / "pairs.json")
        if str(row["pair_id"]) in {str(value) for value in plan["pilot"]["pairs"]}
        for item_id in row["member_ids"]
    }
    if pilot_ids != expected_pilot_ids or len(pilot_ids) != int(plan["pilot"]["instances"]):
        fail("packet pilot IDs differ from the frozen pair selection")
    return packet_by_id


def conservative_pilot_plus_full_bound(packet: Json, lane: Json) -> float:
    pilot_ids = {str(value) for value in packet["pilot_item_ids"]}
    rows = list(packet["records"])
    billed_rows = [*rows, *(row for row in rows if str(row["item_id"]) in pilot_ids)]
    input_tokens = sum(math.ceil(int(row["utf8_bytes"]) / 2) for row in billed_rows)
    output_tokens = len(billed_rows) * int(lane["max_output_tokens"])
    return (
        input_tokens * float(lane["input_usd_per_million"])
        + output_tokens * float(lane["output_usd_per_million"])
    ) / 1_000_000


def _reject_hidden_reasoning_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        forbidden = {"reasoning_content", "thought", "thoughts", "thinking_content"}
        overlap = forbidden & set(value)
        if overlap:
            fail(f"run retains hidden reasoning fields at {path}: {sorted(overlap)}")
        for key, child in value.items():
            _reject_hidden_reasoning_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_hidden_reasoning_fields(child, f"{path}[{index}]")


def validate_required_routed_provider(row: Json, lane: Json, item_id: str) -> None:
    """Check the routed provider only after a provider returned a response.

    Transport failures can occur before OpenRouter selects an upstream endpoint, so a
    missing routed-provider field is expected on those rows. The transport error and
    STOP gate remain part of the validated run.
    """
    required_routed_provider = lane.get("required_routed_provider")
    if (
        row.get("transport_status") == "OK"
        and isinstance(required_routed_provider, str)
        and row.get("routed_provider") != required_routed_provider
    ):
        fail(f"routed provider mismatch for {item_id}")


def validate_run(
    path: Path,
    plan: Json,
    packet: Json,
    packet_by_id: dict[str, Json],
    lanes: dict[str, Json],
    formal_ids: set[str],
) -> Json:
    rows = load_jsonl(path)
    if not rows:
        fail(f"empty run: {path}")
    _reject_hidden_reasoning_fields(rows)
    lane_ids = {str(row.get("lane_id")) for row in rows}
    phases = {str(row.get("phase")) for row in rows}
    frozen_commits = {str(row.get("frozen_plan_commit")) for row in rows}
    if len(lane_ids) != 1 or len(phases) != 1 or len(frozen_commits) != 1:
        fail(f"run mixes identities: {path}")
    lane_id = next(iter(lane_ids))
    phase = next(iter(phases))
    if lane_id not in lanes or phase not in {"pilot", "full"}:
        fail(f"run has an unknown lane or phase: {path}")
    formal = lane_id in formal_ids
    if phase == "full" and not formal:
        fail(f"exploratory full run is forbidden: {path}")
    lane = lanes[lane_id]
    expected_ids = (
        {str(value) for value in packet["pilot_item_ids"]}
        if phase == "pilot"
        else set(packet_by_id)
    )
    observed_ids: set[str] = set()
    computed_cost = 0.0
    known_costs = 0
    for row in rows:
        item_id = str(row.get("item_id"))
        if item_id in observed_ids:
            fail(f"duplicate run item_id in {path}: {item_id}")
        observed_ids.add(item_id)
        validate_with_schema(row, RUN_SCHEMA, item_id)
        if row.get("study_id") != plan["study_id"]:
            fail(f"study_id mismatch for {item_id}")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            fail(f"packet digest mismatch for {item_id}")
        if row.get("dataset_manifest_sha256") != packet["dataset_manifest_sha256"]:
            fail(f"dataset digest mismatch for {item_id}")
        if row.get("model_requested") != lane["model"]:
            fail(f"model mismatch for {item_id}")
        validate_required_routed_provider(row, lane, item_id)
        if item_id not in packet_by_id:
            fail(f"run item is absent from packet: {item_id}")
        if row.get("prompt_sha256") != packet_by_id[item_id]["prompt_sha256"]:
            fail(f"prompt hash mismatch for {item_id}")
        try:
            started = datetime.fromisoformat(
                str(row["request_started_at_utc"]).replace("Z", "+00:00")
            )
            received = datetime.fromisoformat(
                str(row["response_received_at_utc"]).replace("Z", "+00:00")
            )
        except ValueError as exc:
            fail(f"invalid request timestamp for {item_id}: {exc}")
        if received < started:
            fail(f"response timestamp precedes request timestamp: {item_id}")
        raw = row.get("raw_response_text")
        raw_hash = row.get("raw_response_sha256")
        if raw is None:
            if raw_hash is not None:
                fail(f"null response has a digest: {item_id}")
        elif raw_hash != sha256_bytes(str(raw).encode("utf-8")):
            fail(f"raw response digest mismatch: {item_id}")
        transport = row["transport_status"]
        parse_status = row["parse_status"]
        if transport == "ERROR" and parse_status != "TRANSPORT_ERROR":
            fail(f"transport/parse status mismatch: {item_id}")
        if transport == "OK" and parse_status == "TRANSPORT_ERROR":
            fail(f"transport/parse status mismatch: {item_id}")
        if parse_status == "OK":
            if not isinstance(row.get("raw_decision"), dict) or not isinstance(
                row.get("postgate_decision"), dict
            ):
                fail(f"parseable record lacks decisions: {item_id}")
        elif row.get("raw_decision") is not None or row.get("postgate_decision") is not None:
            fail(f"unparseable record retains a decision: {item_id}")
        cost = row.get("actual_cost_usd")
        if isinstance(cost, (int, float)):
            computed_cost += float(cost)
            known_costs += 1
            if row.get("cost_status") != "COMPUTED_FROM_HOST_USAGE":
                fail(f"computed cost has wrong status: {item_id}")
        elif row.get("cost_status") != "UNKNOWN":
            fail(f"unknown cost has wrong status: {item_id}")
        expected_ceiling = "COMPUTATIONAL" if formal else "LLM_PATH_TESTED_NOT_PROMOTED"
        if row.get("evidence_ceiling") != expected_ceiling:
            fail(f"evidence ceiling mismatch: {item_id}")
    if observed_ids != expected_ids:
        fail(f"run coverage differs from frozen {phase} IDs: {path}")
    lane_cap = lane.get("spend_cap_usd")
    if formal and isinstance(lane_cap, (int, float)) and computed_cost > float(lane_cap) + 1e-12:
        fail(f"run cost exceeds lane cap: {path}")
    return {
        "path": path,
        "lane_id": lane_id,
        "phase": phase,
        "formal": formal,
        "records": rows,
        "sha256": sha256_file(path),
        "computed_cost_usd": computed_cost if known_costs else None,
        "frozen_plan_commit": next(iter(frozen_commits)),
        "full_requires_pilot": plan.get("design", {}).get("full_requires_pilot", True),
    }


def load_frozen_plan(plan_path: Path, commit: str) -> tuple[Json, bytes]:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        fail(f"run has an invalid frozen-plan commit: {commit}")
    try:
        relative = plan_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        fail("plan path must be inside the repository")
    shown = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0:
        fail(f"run commit does not contain the registered plan: {commit}")
    try:
        value = json.loads(shown.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"run commit contains a malformed plan: {commit}: {exc}")
    if not isinstance(value, dict):
        fail(f"run commit plan is not an object: {commit}")
    return value, shown.stdout


def validate_full_run_gates(run_reports: list[Json]) -> None:
    identities: set[tuple[str, str]] = set()
    for report in run_reports:
        identity = (str(report["lane_id"]), str(report["phase"]))
        if identity in identities:
            fail(f"duplicate run identity: {identity}")
        identities.add(identity)
    pilots = {
        str(report["lane_id"]): report
        for report in run_reports
        if report["phase"] == "pilot" and report["formal"]
    }
    for report in run_reports:
        if report["phase"] != "full":
            continue
        lane_id = str(report["lane_id"])
        if report.get("full_requires_pilot") is False:
            continue
        pilot = pilots.get(lane_id)
        if pilot is None:
            fail(f"full run lacks matching pilot evidence: {lane_id}")
        rows = pilot["records"]
        transport_errors = sum(row["transport_status"] == "ERROR" for row in rows)
        parseable = sum(row["parse_status"] == "OK" for row in rows)
        if transport_errors != 0 or parseable < 10:
            fail(f"full run bypassed the frozen STOP gate: {lane_id}")


def validate_cumulative_costs(
    run_reports: list[Json], lanes: dict[str, Json], formal_ids: set[str]
) -> None:
    for lane_id in formal_ids:
        lane_cap = lanes[lane_id].get("spend_cap_usd")
        if not isinstance(lane_cap, (int, float)):
            continue
        known = [
            float(report["computed_cost_usd"])
            for report in run_reports
            if report["lane_id"] == lane_id
            and isinstance(report["computed_cost_usd"], (int, float))
        ]
        if sum(known) > float(lane_cap) + 1e-12:
            fail(f"cumulative run cost exceeds lane cap: {lane_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run", type=Path, action="append", default=[])
    args = parser.parse_args()

    dataset_dir = args.dataset.resolve()
    validate_dataset(dataset_dir, ROOT)
    plan_path = args.plan.resolve()
    plan = load_json(plan_path)
    expected_dataset_manifest = plan["dataset"].get("dataset_manifest_sha256")
    if isinstance(expected_dataset_manifest, str):
        if sha256_file(dataset_dir / "manifest.json") != expected_dataset_manifest:
            fail("dataset manifest differs from the plan")
    elif not (
        expected_dataset_manifest is None
        and plan.get("design", {}).get("dataset_manifest_bound_at_c1") is True
    ):
        fail("plan lacks a dataset digest or registered C1 binding")
    lanes, formal_ids = validate_plan(plan)
    packet = load_json(args.packet.resolve())
    packet_by_id = validate_packet(packet, plan, dataset_dir)
    conservative_bounds = {
        lane_id: conservative_pilot_plus_full_bound(packet, lanes[lane_id])
        for lane_id in formal_ids
    }
    for lane_id, bound in conservative_bounds.items():
        lane_cap = lanes[lane_id].get("spend_cap_usd")
        if isinstance(lane_cap, (int, float)) and bound > float(lane_cap):
            fail(f"conservative pilot-plus-full bound exceeds lane cap: {lane_id}")

    run_commits: list[tuple[Path, str]] = []
    for path in args.run:
        resolved = path.resolve()
        rows = load_jsonl(resolved)
        commits = {str(row.get("frozen_plan_commit")) for row in rows}
        if len(commits) != 1:
            fail(f"run mixes frozen-plan commits: {path}")
        run_commits.append((resolved, next(iter(commits))))

    accepted_amendment_commits = {
        str(value)
        for value in plan.get("collection_amendment", {}).get("accepted_frozen_plan_commits", [])
    }
    frozen_contexts: dict[str, tuple[Json, dict[str, Json], set[str], dict[str, Json]]] = {}
    for commit in {commit for _, commit in run_commits}:
        frozen_plan, frozen_bytes = load_frozen_plan(plan_path, commit)
        if frozen_bytes != plan_path.read_bytes() and commit not in accepted_amendment_commits:
            fail(f"historical frozen plan is not registered by the collection amendment: {commit}")
        frozen_lanes, frozen_formal_ids = validate_plan(frozen_plan)
        frozen_packet_by_id = validate_packet(packet, frozen_plan, dataset_dir)
        frozen_contexts[commit] = (
            frozen_plan,
            frozen_lanes,
            frozen_formal_ids,
            frozen_packet_by_id,
        )

    reports: list[Json] = []
    for path, commit in run_commits:
        frozen_plan, frozen_lanes, frozen_formal_ids, frozen_packet_by_id = frozen_contexts[commit]
        report = validate_run(
            path,
            frozen_plan,
            packet,
            frozen_packet_by_id,
            frozen_lanes,
            frozen_formal_ids,
        )
        if str(report["lane_id"]) not in formal_ids:
            fail(f"historical run lane is absent from the current collection plan: {path}")
        reports.append(report)
    validate_full_run_gates(reports)
    validate_cumulative_costs(reports, lanes, formal_ids)
    print(
        json.dumps(
            {
                "status": "PASS",
                "plan_status": plan["status"],
                "packet_sha256": packet["packet_sha256"],
                "packet_records": len(packet_by_id),
                "pilot_records": len(packet["pilot_item_ids"]),
                "formal_lane_cap_usd": (
                    sum(float(lanes[lane_id]["spend_cap_usd"]) for lane_id in formal_ids)
                    if all(
                        isinstance(lanes[lane_id].get("spend_cap_usd"), (int, float))
                        for lane_id in formal_ids
                    )
                    else None
                ),
                "conservative_pilot_plus_full_bounds_usd": conservative_bounds,
                "validated_frozen_plan_commits": sorted(frozen_contexts),
                "validated_runs": [
                    {
                        "lane_id": report["lane_id"],
                        "phase": report["phase"],
                        "records": len(report["records"]),
                        "sha256": report["sha256"],
                        "computed_cost_usd": report["computed_cost_usd"],
                    }
                    for report in reports
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
