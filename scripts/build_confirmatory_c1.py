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

from run_confirmatory_service_study import (  # noqa: E402
    portable_decision_schema,
    request_body_for_lane,
    request_headers_template,
)

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def build_c1(packet: Json, baselines: Json, plan: Json, plan_path: Path) -> tuple[Json, Json]:
    baseline_payload = deepcopy(baselines)
    baseline_sha = baseline_payload.pop("predictions_sha256", None)
    if baseline_sha != sha256_bytes(canonical_json(baseline_payload).encode("utf-8")):
        raise ValueError("baseline prediction digest mismatch")
    if baselines.get("contains_test_gold") is not False:
        raise ValueError("baseline artifact crossed the hidden-gold boundary")
    if baselines.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("baseline artifact is not bound to the hidden packet")
    schema = portable_decision_schema(load_json(ROOT / "schemas" / "agent-decision.schema.json"))
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
            body = request_body_for_lane(lane, str(row["prompt"]), schema)
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
                    "request_headers_template": request_headers_template(lane),
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
