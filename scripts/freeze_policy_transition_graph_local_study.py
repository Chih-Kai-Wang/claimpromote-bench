#!/usr/bin/env python3
"""Freeze the local-model execution plan for the reachable policy-transition graph."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from policy_transition_graph_local import (  # noqa: E402
    DATASET_KEY,
    RUNTIME_PATHS,
    register_only_transition_graph,
    self_digest,
)

register_only_transition_graph()

from freeze_local_model_replications import (  # noqa: E402
    build_study,
    load_tokenizers,
    validate_receipts,
    write_json,
)
from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    VOID_RECEIPT_PATH,
    load_catalog,
    validate_void_receipt,
)
from validate_policy_transition_graph_study import validate as validate_graph  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-local-freeze: {message}")


def runtime_hashes() -> Json:
    missing = [relative for relative in RUNTIME_PATHS if not (ROOT / relative).is_file()]
    if missing:
        fail(f"runtime source is missing: {missing}")
    return {relative: sha256_file(ROOT / relative) for relative in RUNTIME_PATHS}


def build_design_receipt(dataset_root: Path, baseline_root: Path, coverage_path: Path) -> Json:
    coverage = validate_graph(dataset_root)
    expected = load_json(coverage_path)
    if canonical_json(coverage) != canonical_json(expected):
        fail("transition coverage does not recompute byte-exactly")
    report = load_json(baseline_root / "report.json")
    if (
        report.get("evaluation_gold_loaded") is not False
        or report.get("model_outputs_loaded") is not False
        or report.get("evaluation_predictions_per_comparator") != 120
    ):
        fail("development-trained comparator boundary changed")
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "PREINFERENCE_POLICY_TRANSITION_GRAPH_DESIGN_DECISION",
        "basis": (
            "Static reachability analysis of the published policy executor and profile "
            "contracts, not accuracy from this evaluation."
        ),
        "design_decision": (
            "Cover all ten semantically reachable directed nonself action transitions with six "
            "contexts each and certify the two impossible HOLD/DEMOTE directions."
        ),
        "known_prior_results": (
            "Earlier hosted policy-switch routes were already known to be resource-confounded "
            "and excluded. An unrelated local SLSA run was active. Neither supplied an edge, "
            "label, prompt, or outcome to this graph construction."
        ),
        "outcomes_used_to_choose_edges_or_contexts": False,
        "transition_graph_model_calls_before_freeze": 0,
        "evaluation_gold_used_to_train_comparators": False,
        "dataset_manifest_sha256": sha256_file(dataset_root / "manifest.json"),
        "transition_coverage_sha256": sha256_file(coverage_path),
        "baseline_report_sha256": sha256_file(baseline_root / "report.json"),
        "baseline_prediction_sha256": {
            name: sha256_file(baseline_root / name)
            for name in (
                "policy_aware-predictions.jsonl",
                "profile_blind-predictions.jsonl",
            )
        },
    }
    receipt["self_digest"] = self_digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    parser.add_argument("--void-receipt", type=Path, default=VOID_RECEIPT_PATH)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    catalog_path = args.catalog.resolve()
    snapshot_path = args.snapshot_receipt.resolve()
    qualification_path = args.qualification_receipt.resolve()
    void_path = args.void_receipt.resolve()
    out_root = args.out_root.resolve()
    study_root = out_root / DATASET_KEY
    if study_root.exists():
        fail(f"frozen study already exists: {study_root}")

    catalog = load_catalog(catalog_path)
    validate_receipts(catalog_path, snapshot_path, qualification_path)
    validate_void_receipt(void_path)
    tokenizers = load_tokenizers(catalog)
    plan, schedule = build_study(
        DATASET_KEY,
        catalog,
        tokenizers,
        catalog_path,
        snapshot_path,
        qualification_path,
        void_path,
        out_root,
    )
    dataset_root = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset"
    baseline_root = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "baseline"
    coverage_path = (
        ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
    )
    study_root.mkdir(parents=True)
    decision_path = study_root / "design-decision-receipt.json"
    write_json(
        decision_path,
        build_design_receipt(dataset_root, baseline_root, coverage_path),
    )
    manifest = load_json(dataset_root / "manifest.json")
    plan["dataset"]["evaluation_factors"] = 10
    plan["dataset"]["transition_coverage_sha256"] = sha256_file(coverage_path)
    plan["dataset"]["baseline_report_sha256"] = sha256_file(baseline_root / "report.json")
    plan["dataset"]["evaluation_action_support"] = manifest["evaluation"]["action_counts"]
    plan["freeze"]["runtime_source_sha256"] = runtime_hashes()
    plan["freeze"]["design_decision_receipt_sha256"] = sha256_file(decision_path)
    plan["freeze"]["transition_graph_model_calls_before_freeze"] = 0
    plan["selection_audit"] = {
        "graph_selected_from_executable_policy_reachability": True,
        "evaluation_accuracy_consulted": False,
        "transition_graph_model_outputs_consulted": False,
        "same_two_models_and_generation_contract_as_prior_local_replications": True,
    }
    plan["promotion_rule"] = (
        "Only the complete set of all 240 sealed terminal outcomes may enter reporting; no "
        "partial, resumed, or selectively retained run is eligible."
    )
    write_json(study_root / "study-plan.json", plan)
    write_json(study_root / "request-schedule.json", schedule)
    print(
        canonical_json(
            {
                "status": plan["status"],
                "study_id": plan["study_id"],
                "planned_cells": schedule["planned_cells"],
                "transition_graph_model_calls_before_freeze": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
