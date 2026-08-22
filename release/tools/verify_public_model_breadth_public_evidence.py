"""Verify and replay the privacy-minimized public model-breadth evidence."""

from __future__ import annotations

import argparse
import copy
import math
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import (  # type: ignore[import-not-found]  # noqa: E402
    combine_lane_metrics,
    derive_reporting_metrics,
)

from claimpromotebench.dataset import load_json, load_jsonl, validate_with_schema  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from release.tools import build_public_model_breadth_public_evidence as builder  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            equivalent(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equivalent(left_value, right_value)
            for left_value, right_value in zip(left, right, strict=True)
        )
    return bool(left == right)


def verify_public_evidence(
    evidence_root: Path,
    plan_path: Path,
    packet_path: Path,
    dataset_dir: Path,
    *,
    api_key: str = "",
) -> Json:
    evidence_root = evidence_root.resolve()
    plan_path = plan_path.resolve()
    packet_path = packet_path.resolve()
    dataset_dir = dataset_dir.resolve()
    receipt = load_json(evidence_root / "privacy-receipt.json")
    plan = load_json(plan_path)
    packet = load_json(packet_path)
    aggregate = load_json(evidence_root / "reported-aggregate.json")
    execution = load_json(evidence_root / "execution-receipt.json")
    if not all(isinstance(value, dict) for value in (receipt, plan, packet, aggregate, execution)):
        fail("public evidence metadata is malformed")

    receipt_payload = copy.deepcopy(receipt)
    observed_receipt_digest = receipt_payload.pop("privacy_receipt_sha256", None)
    if observed_receipt_digest != sha256_bytes(canonical_json(receipt_payload).encode("utf-8")):
        fail("privacy receipt self-digest differs")
    actual_files = builder._file_map(evidence_root, exclude={"privacy-receipt.json"})
    if receipt.get("derived_files_sha256") != actual_files:
        fail("privacy receipt file map differs from the public evidence tree")
    if (
        receipt.get("status") != "POST_EXECUTION_PUBLIC_SAFE_DERIVATIVE"
        or receipt.get("terminal_records_validated") != 1260
        or receipt.get("raw_final_response_text_included") is not False
        or receipt.get("free_form_error_detail_included") is not False
        or receipt.get("provider_response_identifiers_included") is not False
        or receipt.get("system_fingerprints_included") is not False
        or receipt.get("hidden_reasoning_fields_included") is not False
        or receipt.get("credentials_included") is not False
        or receipt.get("scientific_fields_unchanged") is not True
        or receipt.get("model_calls_performed") != 0
    ):
        fail("privacy receipt scope differs")
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("planned_cells") != 1260
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
    ):
        fail("execution receipt no longer records a complete zero-retry run")

    lane_order = plan.get("execution", {}).get("base_lane_order")
    lane_files = receipt.get("public_lane_files")
    lane_hashes = receipt.get("public_lane_files_sha256")
    if (
        not isinstance(lane_order, list)
        or len(lane_order) != 7
        or not isinstance(lane_files, dict)
        or not isinstance(lane_hashes, dict)
        or set(lane_files) != {str(value) for value in lane_order}
        or set(lane_hashes) != set(lane_files)
    ):
        fail("public lane map differs from the seven-lane plan")

    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        fail("dataset pair index is malformed")
    expected_item_ids = {str(row["id"]) for row in gold}
    if len(expected_item_ids) != 180 or len(pairs) != 90:
        fail("public challenge coverage differs")

    aggregate_lanes = {
        str(lane.get("lane_id")): lane
        for lane in aggregate.get("lanes", [])
        if isinstance(lane, dict)
    }
    if set(aggregate_lanes) != set(lane_files):
        fail("reported aggregate lane set differs from public records")

    row_map_rows = load_jsonl(evidence_root / "source-to-public-row-hashes.jsonl")
    row_map = {(str(row.get("lane_id")), str(row.get("item_id"))): row for row in row_map_rows}
    if len(row_map_rows) != 1260 or len(row_map) != 1260:
        fail("source-to-public row map coverage differs")

    metrics_by_lane: list[Json] = []
    parseable_total = 0
    for lane_id_value in lane_order:
        lane_id = str(lane_id_value)
        run_path = evidence_root / str(lane_files[lane_id])
        if sha256_file(run_path) != lane_hashes[lane_id]:
            fail(f"public lane digest differs: {lane_id}")
        rows = load_jsonl(run_path)
        if (
            len(rows) != 180
            or {str(row.get("item_id")) for row in rows} != expected_item_ids
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
        ):
            fail(f"public lane coverage differs: {lane_id}")
        for row in rows:
            item_id = str(row.get("item_id"))
            validate_with_schema(row, RUN_SCHEMA, f"{lane_id}:{item_id}")
            if any(row.get(field) is not None for field in builder.PRIVATE_TEXT_FIELDS):
                fail(f"public lane retains private text: {lane_id}:{item_id}")
            if (
                row.get("provider_response_id") is not None
                or row.get("system_fingerprint") is not None
            ):
                fail(f"public lane retains a provider identifier: {lane_id}:{item_id}")
            if builder._walk_hidden_reasoning_keys(row):
                fail(f"public lane retains hidden reasoning: {lane_id}:{item_id}")
            findings = builder._scan_text(canonical_json(row), api_key=api_key)
            if findings:
                fail(f"public lane contains privacy finding classes: {sorted(set(findings))}")
            mapping = row_map.get((lane_id, item_id))
            if (
                not isinstance(mapping, dict)
                or mapping.get("derived_row_sha256")
                != sha256_bytes(canonical_json(row).encode("utf-8"))
                or mapping.get("scientific_fields_unchanged") is not True
            ):
                fail(f"public row-map binding differs: {lane_id}:{item_id}")
        metrics = derive_reporting_metrics(gold, pairs, rows)
        reported_lane = aggregate_lanes[lane_id]
        if not equivalent(metrics, reported_lane.get("metrics")):
            fail(f"reported metrics differ from public rows: {lane_id}")
        if reported_lane.get("run_sha256") != sha256_file(run_path):
            fail(f"reported lane digest differs: {lane_id}")
        metrics_by_lane.append(metrics)
        parseable_total += int(metrics["parseable_items"])

    pooled = combine_lane_metrics(metrics_by_lane)
    if not equivalent(pooled, aggregate.get("pooled_model_item_cells")):
        fail("reported pooled metrics differ from public rows")
    if (
        aggregate.get("design") != "PUBLIC_PRECOMMITTED_MODEL_BREADTH_SUPPLEMENT"
        or aggregate.get("service_comparison", {}).get("causal_model_ablation_claimed") is not False
        or aggregate.get("scope_limits")
        != {
            "breadth_dimension_added": "MODEL_FAMILY_ONLY",
            "hidden_generalization_claimed": False,
            "naturalistic_cases": 0,
            "ontology_count": 1,
            "policy_count": 1,
            "public_known_challenge": True,
        }
        or aggregate.get("deterministic_policy_executor", {}).get("label")
        != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    ):
        fail("reported interpretation boundary differs")

    return {
        "status": "PUBLIC_MODEL_BREADTH_EVIDENCE_PASS",
        "lanes": len(lane_order),
        "items_per_lane": 180,
        "pairs_per_lane": 90,
        "terminal_records": 1260,
        "parseable_records": parseable_total,
        "privacy_receipt_sha256": observed_receipt_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    result = verify_public_evidence(
        args.evidence,
        args.plan,
        args.packet,
        args.dataset,
        api_key=os.environ.get("OPENCODE_GO_API_KEY", ""),
    )
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
