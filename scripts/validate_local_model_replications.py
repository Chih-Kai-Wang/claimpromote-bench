#!/usr/bin/env python3
"""Validate frozen local-model plans without loading model weights."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    DATASETS,
    REQUIREMENTS_PATH,
    lane_id,
    load_catalog,
    load_object,
)

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"local-model-validation: {message}")


def self_digest(value: Json, field: str = "self_digest") -> str:
    payload = {key: child for key, child in value.items() if key != field}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def validate_receipts(catalog_path: Path, snapshot_path: Path, qualification_path: Path) -> None:
    catalog_hash = sha256_file(catalog_path)
    snapshot = load_object(snapshot_path)
    qualification = load_object(qualification_path)
    if (
        snapshot.get("status") != "PINNED_LOCAL_MODEL_SNAPSHOTS_VALIDATED"
        or snapshot.get("catalog_sha256") != catalog_hash
        or snapshot.get("self_digest") != self_digest(snapshot)
    ):
        fail("model snapshot receipt changed")
    snapshots = snapshot.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 2:
        fail("model snapshot receipt does not contain two snapshots")
    for row in snapshots:
        payload = {key: value for key, value in row.items() if key != "snapshot_digest"}
        if row.get("snapshot_digest") != sha256_bytes(canonical_json(payload).encode("utf-8")):
            fail(f"model snapshot tree digest changed: {row.get('model_repo')}")
    if (
        qualification.get("status")
        != "LOCAL_MODEL_ENVIRONMENT_QUALIFIED_BEFORE_BENCHMARK_INFERENCE"
        or qualification.get("catalog_sha256") != catalog_hash
        or qualification.get("snapshot_receipt_self_digest") != snapshot.get("self_digest")
        or qualification.get("benchmark_inference_calls") != 0
        or qualification.get("self_digest") != self_digest(qualification)
        or qualification.get("credentials_used_or_retained") is not False
    ):
        fail("local environment qualification receipt changed")


def validate_study(
    dataset_key: str,
    study_root: Path,
    catalog: Json,
    catalog_path: Path,
    snapshot_path: Path,
    qualification_path: Path,
) -> None:
    spec = DATASETS[dataset_key]
    plan_path = study_root / "study-plan.json"
    schedule_path = study_root / "request-schedule.json"
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    dataset_root = Path(spec["dataset_root"])
    manifest = load_json(dataset_root / "manifest.json")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    records = {str(row["item_id"]): row for row in packet["records"]}
    expected_lanes = [lane_id(lane, dataset_key) for lane in catalog["lanes"]]
    formal_lanes = plan.get("formal_lanes")
    if (
        plan.get("status") != "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION"
        or plan.get("study_id") != spec["study_id"]
        or plan.get("design") != spec["design"]
        or not isinstance(formal_lanes, list)
        or [row.get("lane_id") for row in formal_lanes] != expected_lanes
        or plan.get("execution", {}).get("base_lane_order") != expected_lanes
        or plan.get("execution", {}).get("planned_application_posts") != 240
        or plan.get("execution", {}).get("client_retry_count") != 0
        or plan.get("freeze", {}).get("benchmark_inference_calls_before_freeze") != 0
    ):
        fail(f"local-model plan contract changed: {dataset_key}")
    dataset = plan.get("dataset", {})
    if (
        dataset.get("dataset_fingerprint") != spec["expected_dataset_fingerprint"]
        or dataset.get("manifest_sha256") != sha256_file(dataset_root / "manifest.json")
        or dataset.get("packet_sha256") != packet["packet_sha256"]
        or dataset.get("evaluation_items") != 120
        or dataset.get("evaluation_pairs") != 60
        or dataset.get("evaluation_factors") != 12
        or manifest.get("dataset_fingerprint") != spec["expected_dataset_fingerprint"]
    ):
        fail(f"local-model dataset binding changed: {dataset_key}")
    freeze = plan.get("freeze", {})
    snapshot = load_object(snapshot_path)
    qualification = load_object(qualification_path)
    if (
        freeze.get("catalog_sha256") != sha256_file(catalog_path)
        or freeze.get("requirements_sha256") != sha256_file(REQUIREMENTS_PATH)
        or freeze.get("snapshot_receipt_sha256") != sha256_file(snapshot_path)
        or freeze.get("snapshot_receipt_self_digest") != snapshot.get("self_digest")
        or freeze.get("qualification_receipt_sha256") != sha256_file(qualification_path)
        or freeze.get("qualification_receipt_self_digest") != qualification.get("self_digest")
    ):
        fail(f"local-model environment binding changed: {dataset_key}")
    runtime = freeze.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or not runtime:
        fail(f"local-model runtime manifest is absent: {dataset_key}")
    for relative, expected_hash in runtime.items():
        path = ROOT / str(relative)
        if not path.is_file() or sha256_file(path) != expected_hash:
            fail(f"local-model runtime source changed after freeze: {relative}")

    cells = schedule.get("cells")
    if (
        schedule.get("status") != "FROZEN_LOCAL_MODEL_REQUEST_SCHEDULE"
        or schedule.get("study_id") != spec["study_id"]
        or schedule.get("planned_cells") != 240
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
        or schedule.get("schedule_sha256") != self_digest(schedule, "schedule_sha256")
        or schedule.get("schedule_sha256") != plan.get("execution", {}).get("schedule_sha256")
        or not isinstance(cells, list)
        or len(cells) != 240
    ):
        fail(f"local-model request schedule changed: {dataset_key}")
    if [row.get("sequence") for row in cells] != list(range(240)):
        fail(f"local-model schedule sequence changed: {dataset_key}")
    if len({str(row.get("cell_id")) for row in cells}) != 240:
        fail(f"local-model schedule cell IDs are not unique: {dataset_key}")
    lane_counts = Counter(str(row.get("lane_id")) for row in cells)
    if lane_counts != Counter({lane: 120 for lane in expected_lanes}):
        fail(f"local-model lane coverage changed: {dataset_key}")
    for lane in expected_lanes:
        lane_items = {str(row.get("item_id")) for row in cells if row.get("lane_id") == lane}
        if lane_items != set(records):
            fail(f"local-model item coverage changed: {dataset_key}/{lane}")
    for cell in cells:
        item_id = str(cell.get("item_id"))
        packet_row = records.get(item_id)
        if (
            packet_row is None
            or cell.get("pair_id") != packet_row.get("pair_id")
            or cell.get("prompt_sha256") != packet_row.get("prompt_sha256")
            or not str(cell.get("formatted_prompt_sha256", "")).startswith("sha256:")
            or not str(cell.get("request_body_sha256", "")).startswith("sha256:")
        ):
            fail(f"local-model schedule cell binding changed: {cell.get('cell_id')}")


def validate_all(
    root: Path,
    catalog_path: Path,
    snapshot_path: Path,
    qualification_path: Path,
) -> None:
    catalog = load_catalog(catalog_path)
    validate_receipts(catalog_path, snapshot_path, qualification_path)
    for dataset_key in DATASETS:
        validate_study(
            dataset_key,
            root / dataset_key,
            catalog,
            catalog_path,
            snapshot_path,
            qualification_path,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    args = parser.parse_args()
    validate_all(
        args.root.resolve(),
        args.catalog.resolve(),
        args.snapshot_receipt.resolve(),
        args.qualification_receipt.resolve(),
    )
    print("LOCAL_MODEL_REPLICATION_FREEZE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
