#!/usr/bin/env python3
"""Validate the independently frozen local policy-transition graph study."""

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
    REQUIREMENTS_PATH,
    VOID_RECEIPT_PATH,
    lane_id,
    load_catalog,
    load_object,
    validate_void_receipt,
)
from policy_transition_graph_local import (  # noqa: E402
    DATASET_KEY,
    RUNTIME_PATHS,
    STUDY_SPEC,
    register_only_transition_graph,
    self_digest,
)
from validate_local_model_replications import validate_receipts  # noqa: E402
from validate_policy_transition_graph_study import (  # noqa: E402
    runtime_source_hash_matches,
    validate_coverage_expectation,
)
from validate_policy_transition_graph_study import (  # noqa: E402
    validate as validate_graph,
)

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-local-validate: {message}")


def validate_all(
    root: Path,
    catalog_path: Path,
    snapshot_path: Path,
    qualification_path: Path,
    void_receipt_path: Path = VOID_RECEIPT_PATH,
) -> None:
    register_only_transition_graph()
    catalog = load_catalog(catalog_path)
    validate_receipts(catalog_path, snapshot_path, qualification_path)
    void_receipt = validate_void_receipt(void_receipt_path)
    study_root = root / DATASET_KEY
    plan = load_object(study_root / "study-plan.json")
    schedule = load_object(study_root / "request-schedule.json")
    decision = load_object(study_root / "design-decision-receipt.json")
    dataset_root = Path(STUDY_SPEC["dataset_root"])
    baseline_root = Path(STUDY_SPEC["baseline_root"])
    manifest = load_json(dataset_root / "manifest.json")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    coverage_path = dataset_root.parent / "transition-coverage.json"
    coverage = validate_graph(dataset_root)
    validate_coverage_expectation(coverage, load_json(coverage_path), coverage_path)
    if (
        decision.get("status") != "PREINFERENCE_POLICY_TRANSITION_GRAPH_DESIGN_DECISION"
        or decision.get("outcomes_used_to_choose_edges_or_contexts") is not False
        or decision.get("transition_graph_model_calls_before_freeze") != 0
        or decision.get("evaluation_gold_used_to_train_comparators") is not False
        or decision.get("self_digest") != self_digest(decision)
    ):
        fail("design-decision boundary changed")

    expected_lanes = [lane_id(lane, DATASET_KEY) for lane in catalog["lanes"]]
    if (
        plan.get("status") != "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION_REPLACEMENT_V2"
        or plan.get("study_id") != STUDY_SPEC["study_id"]
        or plan.get("design") != STUDY_SPEC["design"]
        or [row.get("lane_id") for row in plan.get("formal_lanes", [])] != expected_lanes
        or plan.get("execution", {}).get("base_lane_order") != expected_lanes
        or plan.get("execution", {}).get("planned_application_posts") != 240
        or plan.get("execution", {}).get("client_retry_count") != 0
        or plan.get("selection_audit", {}).get("evaluation_accuracy_consulted") is not False
        or plan.get("selection_audit", {}).get("transition_graph_model_outputs_consulted")
        is not False
    ):
        fail("frozen plan contract changed")
    dataset = plan.get("dataset", {})
    if (
        dataset.get("dataset_fingerprint") != STUDY_SPEC["expected_dataset_fingerprint"]
        or dataset.get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or dataset.get("manifest_sha256") != sha256_file(dataset_root / "manifest.json")
        or dataset.get("packet_sha256") != packet.get("packet_sha256")
        or dataset.get("evaluation_items") != 120
        or dataset.get("evaluation_pairs") != 60
        or dataset.get("evaluation_factors") != 10
        or dataset.get("transition_coverage_sha256") != sha256_file(coverage_path)
        or dataset.get("baseline_report_sha256") != sha256_file(baseline_root / "report.json")
    ):
        fail("dataset, graph, or comparator binding changed")
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
        or freeze.get("void_attempt_receipt_sha256") != sha256_file(void_receipt_path)
        or freeze.get("void_attempt_receipt_self_digest") != void_receipt.get("self_digest")
        or freeze.get("design_decision_receipt_sha256")
        != sha256_file(study_root / "design-decision-receipt.json")
        or freeze.get("transition_graph_model_calls_before_freeze") != 0
    ):
        fail("environment or preinference receipt binding changed")
    runtime = freeze.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_PATHS):
        fail("exact runtime-source closure changed")
    for relative in RUNTIME_PATHS:
        if not runtime_source_hash_matches(relative, runtime[relative]):
            fail(f"runtime source changed after freeze: {relative}")

    records = {str(row["item_id"]): row for row in packet["records"]}
    cells = schedule.get("cells")
    if (
        schedule.get("status") != "FROZEN_LOCAL_MODEL_REQUEST_SCHEDULE_REPLACEMENT_V2"
        or schedule.get("study_id") != STUDY_SPEC["study_id"]
        or schedule.get("planned_cells") != 240
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
        or schedule.get("schedule_sha256") != self_digest(schedule, "schedule_sha256")
        or schedule.get("schedule_sha256") != plan.get("execution", {}).get("schedule_sha256")
        or not isinstance(cells, list)
        or len(cells) != 240
        or [cell.get("sequence") for cell in cells] != list(range(240))
        or len({str(cell.get("cell_id")) for cell in cells}) != 240
    ):
        fail("request schedule changed")
    if Counter(str(cell.get("lane_id")) for cell in cells) != Counter(
        {lane: 120 for lane in expected_lanes}
    ):
        fail("lane coverage changed")
    for lane in expected_lanes:
        if {str(cell.get("item_id")) for cell in cells if cell.get("lane_id") == lane} != set(
            records
        ):
            fail(f"item coverage changed: {lane}")
    for cell in cells:
        packet_row = records.get(str(cell.get("item_id")))
        if (
            packet_row is None
            or cell.get("pair_id") != packet_row.get("pair_id")
            or cell.get("prompt_sha256") != packet_row.get("prompt_sha256")
            or not str(cell.get("formatted_prompt_sha256", "")).startswith("sha256:")
            or not str(cell.get("request_body_sha256", "")).startswith("sha256:")
        ):
            fail(f"cell binding changed: {cell.get('cell_id')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    parser.add_argument("--void-receipt", type=Path, default=VOID_RECEIPT_PATH)
    args = parser.parse_args()
    validate_all(
        args.root.resolve(),
        args.catalog.resolve(),
        args.snapshot_receipt.resolve(),
        args.qualification_receipt.resolve(),
        args.void_receipt.resolve(),
    )
    print("POLICY_TRANSITION_GRAPH_LOCAL_FREEZE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
