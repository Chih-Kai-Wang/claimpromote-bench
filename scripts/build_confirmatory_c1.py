#!/usr/bin/env python3
"""Freeze all 600 request bodies and emit a public-safe C1 receipt before any POST."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from confirmatory_subscription_authorization import (  # noqa: E402
    validate_schedule_authorization,
)

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def c1_portable_decision_schema(schema: Json) -> Json:
    """Independently derive the frozen portable schema used in C1 request bodies."""

    cleaned = deepcopy(schema)
    cleaned.pop("$schema", None)
    cleaned.pop("$id", None)
    cleaned.pop("title", None)
    definitions = cleaned.pop("$defs", {})
    state = definitions.get("state")
    proposed = cleaned.get("properties", {}).get("proposed_state")
    if not isinstance(state, dict) or not isinstance(proposed, dict):
        raise ValueError("C1 decision schema state definition changed")
    cleaned["properties"]["proposed_state"] = deepcopy(state)

    def subset(value: Any) -> Any:
        unsupported = {"uniqueItems", "pattern", "minimum", "maximum"}
        if isinstance(value, dict):
            return {key: subset(child) for key, child in value.items() if key not in unsupported}
        if isinstance(value, list):
            return [subset(child) for child in value]
        return value

    return subset(cleaned)


def c1_request_body_for_lane(lane: Json, prompt: str, schema: Json) -> Json:
    """Construct C1 bodies without importing the scored runner implementation."""

    if lane["api_kind"] == "anthropic_messages":
        if lane.get("response_format") != "prompt_only_json":
            raise ValueError("C1 Messages lane must remain prompt-only JSON")
        return {
            "model": lane["model"],
            "max_tokens": int(lane["max_output_tokens"]),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    if lane["api_kind"] == "openai_compatible":
        if lane.get("response_format") != "json_schema":
            raise ValueError("C1 chat-completions lane must retain strict JSON Schema")
        return {
            "model": lane["model"],
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                    "strict": True,
                    "schema": schema,
                },
            },
            "stream": False,
            "max_tokens": int(lane["max_output_tokens"]),
        }
    raise ValueError("C1 encountered an unsupported API kind")


def c1_request_headers_template(lane: Json) -> Json:
    headers: Json = {
        "Content-Type": "application/json",
        "User-Agent": "ClaimPromoteBench-Confirmatory/1",
        "Authorization": "<REDACTED_CREDENTIAL>",
    }
    if lane["api_kind"] == "anthropic_messages":
        headers["x-api-key"] = "<REDACTED_CREDENTIAL>"
        headers["anthropic-version"] = "2023-06-01"
    return headers


def build_c1(packet: Json, baselines: Json, plan: Json, plan_path: Path) -> tuple[Json, Json]:
    baseline_payload = deepcopy(baselines)
    baseline_sha = baseline_payload.pop("predictions_sha256", None)
    if baseline_sha != sha256_bytes(canonical_json(baseline_payload).encode("utf-8")):
        raise ValueError("baseline prediction digest mismatch")
    if baselines.get("contains_test_gold") is not False:
        raise ValueError("baseline artifact crossed the hidden-gold boundary")
    if baselines.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("baseline artifact is not bound to the hidden packet")
    schema = c1_portable_decision_schema(load_json(ROOT / "schemas" / "agent-decision.schema.json"))
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    lane_order = [str(value) for value in plan["execution"]["lane_order"]]
    if set(lane_order) != set(lanes) or len(lane_order) != 2:
        raise ValueError("confirmatory C1 requires exactly the two frozen lanes")
    records = sorted(packet["records"], key=lambda row: str(row["item_id"]))
    if len(records) != 300:
        raise ValueError("confirmatory C1 requires exactly 300 packet records")
    cells: list[Json] = []
    for lane_id in lane_order:
        lane = lanes[lane_id]
        for sequence, row in enumerate(records):
            body = c1_request_body_for_lane(lane, str(row["prompt"]), schema)
            body_sha = sha256_bytes(canonical_json(body).encode("utf-8"))
            cells.append(
                {
                    "cell_id": f"{lane_id}/{row['item_id']}",
                    "lane_id": lane_id,
                    "sequence": sequence,
                    "item_id": str(row["item_id"]),
                    "pair_id": str(row["pair_id"]),
                    "prompt_sha256": str(row["prompt_sha256"]),
                    "request_body": body,
                    "request_body_sha256": body_sha,
                    "request_headers_template": c1_request_headers_template(lane),
                }
            )
    schedule: Json = {
        "schema_version": "1.0.0",
        "study_id": str(plan["study_id"]),
        "packet_sha256": str(packet["packet_sha256"]),
        "baseline_predictions_sha256": str(baselines["predictions_sha256"]),
        "lane_order": lane_order,
        "item_order": "LEXICOGRAPHIC_OPAQUE_ITEM_ID_WITHIN_EACH_LANE",
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode("utf-8"))
    subscription_authorization = validate_schedule_authorization(plan, schedule)
    request_hashes = sorted(str(cell["request_body_sha256"]) for cell in cells)
    receipt: Json = {
        "schema_version": "1.0.0",
        "commitment_stage": "C1_BEFORE_ANY_MODEL_POST",
        "study_id": str(plan["study_id"]),
        "plan_file_sha256": sha256_file(plan_path),
        "dataset_manifest_sha256": str(packet["dataset_manifest_sha256"]),
        "packet_sha256": str(packet["packet_sha256"]),
        "baseline_predictions_sha256": str(baselines["predictions_sha256"]),
        "shallow_model_sha256": str(baselines["shallow_model_sha256"]),
        "schedule_sha256": str(schedule["schedule_sha256"]),
        "planned_cells": len(cells),
        "planned_lanes": 2,
        "planned_items_per_lane": 300,
        "request_body_hash_set_sha256": sha256_bytes(
            canonical_json(request_hashes).encode("utf-8")
        ),
        "subscription_authorization": subscription_authorization,
        "contains_request_bodies": False,
        "contains_prompts": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "contains_seed_bytes": False,
        "no_model_post_before_receipt": True,
    }
    receipt["c1_receipt_sha256"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    return schedule, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 11, 16):
        raise SystemExit("confirmatory C1 runtime must be exact CPython 3.11.16")
    plan_path = args.plan.resolve()
    schedule, receipt = build_c1(
        load_json(args.packet.resolve()),
        load_json(args.baselines.resolve()),
        load_json(plan_path),
        plan_path,
    )
    args.schedule_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.schedule_out.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "C1_READY_BEFORE_ANY_MODEL_POST",
                "planned_cells": receipt["planned_cells"],
                "schedule_sha256": receipt["schedule_sha256"],
                "c1_receipt_sha256": receipt["c1_receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
