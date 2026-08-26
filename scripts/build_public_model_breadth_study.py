#!/usr/bin/env python3
"""Build the credential-free request schedule for the public model-breadth supplement."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"public-model-breadth-build: {message}")


def request_body(lane: Json, prompt: str) -> Json:
    """Return the common prompt-only body frozen for both supported API adapters."""

    if lane.get("api_kind") not in {"openai_compatible", "anthropic_messages"}:
        fail(f"unsupported API adapter: {lane.get('api_kind')}")
    if lane.get("response_format") != "prompt_only_json":
        fail(f"lane is not prompt-only JSON: {lane.get('lane_id')}")
    return {
        "model": lane["model"],
        "max_tokens": int(lane["max_output_tokens"]),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }


def build_schedule(plan: Json, packet: Json) -> Json:
    lane_ids = [str(value) for value in plan["execution"]["base_lane_order"]]
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    if lane_ids != list(lanes):
        fail("base lane order must equal formal-lane declaration order")
    records = sorted(packet.get("records", []), key=lambda row: str(row.get("item_id")))
    expected_items = int(plan["design"]["planned_instances"])
    if len(records) != expected_items:
        fail(f"packet has {len(records)} records, expected {expected_items}")

    cells: list[Json] = []
    for item_index, record in enumerate(records):
        rotation = item_index % len(lane_ids)
        rotated = lane_ids[rotation:] + lane_ids[:rotation]
        for within_item_position, lane_id in enumerate(rotated):
            lane = lanes[lane_id]
            body = request_body(lane, str(record["prompt"]))
            item_id = str(record["item_id"])
            cells.append(
                {
                    "sequence": len(cells),
                    "item_index": item_index,
                    "within_item_position": within_item_position,
                    "cell_id": f"{lane_id}/{item_id}",
                    "lane_id": lane_id,
                    "item_id": item_id,
                    "pair_id": str(record["pair_id"]),
                    "prompt_sha256": str(record["prompt_sha256"]),
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
                }
            )

    payload: Json = {
        "schema_version": "1.0.0",
        "study_id": plan["study_id"],
        "status": "FROZEN_BEFORE_MODEL_CALLS",
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": plan["prompt"]["packet_file_sha256"],
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "base_lane_order": lane_ids,
        "order_rule": plan["execution"]["order_rule"],
        "planned_items": expected_items,
        "planned_lanes": len(lane_ids),
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    payload["schedule_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing schedule: {output}")
    schedule = build_schedule(load_json(args.plan.resolve()), load_json(args.packet.resolve()))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": schedule["status"],
                "planned_cells": schedule["planned_cells"],
                "schedule_sha256": schedule["schedule_sha256"],
                "out": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
