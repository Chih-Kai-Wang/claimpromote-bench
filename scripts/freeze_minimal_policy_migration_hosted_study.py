#!/usr/bin/env python3
"""Freeze a minimum graph-and-rule-complete hosted policy-migration smoke study."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
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
)
from freeze_slsa_portability_study import request_body  # noqa: E402
from validate_policy_switch_study import validate_baselines  # noqa: E402
from validate_policy_transition_graph_study import validate as validate_graph  # noqa: E402

from claimpromotebench.dataset import load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ID = "claimpromotebench-minimal-policy-migration-hosted-2026-08-v1"
EXPECTED_ROOT = ROOT / "v2" / "policy-transition-graph-v1" / "hosted-minimal-v1"
DATASET_ROOT = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset"
BASELINE_ROOT = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "baseline"
COVERAGE_PATH = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
MINIMAL_SUITE_PATH = ROOT / "v2" / "policy-transition-graph-v1" / "minimal-release-suite.json"
SOURCE_HOSTED_PLAN = ROOT / "v2" / "policy-transition-graph-v1" / "hosted-v1" / "study-plan.json"
CATALOG_PATH = ROOT / "v2" / "policy-transition-graph-v1" / "hosted-v1" / "catalog-snapshot.json"
SOURCE_VALIDATION_RECEIPT = (
    ROOT / "v2" / "slsa-portability-v1" / "replacement-v2" / "source-validation-receipt.json"
)
BASELINE_REQUIREMENTS = ROOT / "v2" / "slsa-portability-v1" / "requirements-baseline.txt"
RUNTIME_SOURCES = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_minimal_policy_migration_hosted_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/derive_minimal_policy_migration_hosted_eligibility.py",
    "scripts/derive_minimal_policy_migration_suite.py",
    "scripts/finalize_minimal_policy_migration_hosted_results.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/freeze_minimal_policy_migration_hosted_study.py",
    "scripts/freeze_slsa_portability_study.py",
    "scripts/policy_switch.py",
    "scripts/run_minimal_policy_migration_hosted_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/slsa_policy.py",
    "scripts/validate_minimal_policy_migration_hosted_study.py",
    "scripts/validate_policy_switch_study.py",
    "scripts/validate_policy_transition_graph_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/decision_validation.py",
    "src/claimpromotebench/hashing.py",
    "v2/policy-switch-v1/policy-contract.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/schemas/stronger-model-run-record.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
    "v2/slsa-portability-v1/requirements-baseline.txt",
)
RESOURCE_EXHAUSTION_RULE = (
    "Ordinary service, syntax, schema, semantic, adapter, and rate-limit failures remain "
    "incorrect in the complete 40-cell end-to-end denominator. If a terminal provider error "
    "explicitly states that the shared subscription quota or usage allowance is exhausted, "
    "at least 20 scheduled cells remain, and every later cell is a transport failure, the "
    "complete hosted minimum-suite study is ineligible for route-conformance reporting. In "
    "that case, retain only a redacted full-study exclusion receipt; never select a successful "
    "subset."
)


def fail(message: str) -> None:
    raise SystemExit(f"minimal-policy-migration-hosted-freeze: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        fail(f"path is outside the repository: {path}")


def self_digest(value: Json, field: str = "self_digest") -> str:
    payload = {key: child for key, child in value.items() if key != field}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def hosted_lanes() -> list[Json]:
    source = load_object(SOURCE_HOSTED_PLAN)
    lanes = deepcopy(source.get("formal_lanes"))
    if not isinstance(lanes, list) or [str(row.get("model")) for row in lanes] != [
        "qwen3.7-max",
        "deepseek-v4-flash",
    ]:
        fail("source hosted configurations changed")
    suffixes = ("qwen3.7-max", "deepseek-v4-flash")
    for lane, suffix in zip(lanes, suffixes, strict=True):
        lane["lane_id"] = f"opencode-go-{suffix}-minimal-policy-migration-hosted-v1"
    return lanes


def selected_gold_support(suite: Json) -> Json:
    selected_ids = {str(value) for value in suite["selected_item_ids"]}
    rows = [
        row
        for row in load_jsonl(DATASET_ROOT / "evaluation-gold.jsonl")
        if str(row["id"]) in selected_ids
    ]
    if len(rows) != 20:
        fail("minimal suite does not select twenty gold rows")
    return dict(sorted(Counter(str(row["decision"]["action"]) for row in rows).items()))


def build_schedule(plan: Json, packet: Json, suite: Json) -> Json:
    lane_ids = [str(value) for value in plan["execution"]["base_lane_order"]]
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    records_by_id = {str(row["item_id"]): row for row in packet["records"]}
    selected_ids = [str(value) for value in suite["selected_item_ids"]]
    if len(selected_ids) != 20 or len(set(selected_ids)) != 20 or lane_ids != list(lanes):
        fail("minimal item coverage or lane order differs")
    records: list[Json] = []
    for item_id in selected_ids:
        record = records_by_id.get(item_id)
        if record is None:
            fail(f"selected item is absent from the frozen packet: {item_id}")
        records.append(record)
    cells: list[Json] = []
    for item_index, record in enumerate(records):
        rotation = item_index % len(lane_ids)
        for lane_id in lane_ids[rotation:] + lane_ids[:rotation]:
            body = request_body(lanes[lane_id], str(record["prompt"]))
            cells.append(
                {
                    "sequence": len(cells),
                    "item_index": item_index,
                    "cell_id": f"{lane_id}/{record['item_id']}",
                    "lane_id": lane_id,
                    "item_id": record["item_id"],
                    "pair_id": record["pair_id"],
                    "prompt_sha256": record["prompt_sha256"],
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
                }
            )
    schedule: Json = {
        "schema_version": "1.0.0",
        "study_id": plan["study_id"],
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "packet_sha256": packet["packet_sha256"],
        "dataset_fingerprint": packet["dataset_fingerprint"],
        "minimal_suite_sha256": sha256_file(MINIMAL_SUITE_PATH),
        "base_lane_order": lane_ids,
        "order_rule": "SELECTED_ITEM_MAJOR_WITH_CYCLIC_LANE_ROTATION",
        "planned_items": 20,
        "planned_lanes": 2,
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode("utf-8"))
    return schedule


def build_selection_receipt(suite: Json, catalog: Json) -> Json:
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "PREINFERENCE_MINIMUM_POLICY_MIGRATION_HOSTED_SELECTION",
        "recorded_at_utc": utc_now(),
        "study_id": STUDY_ID,
        "selection_basis": (
            "Reuse the deterministically derived minimum witness: one controlled pair per "
            "reachable action edge while jointly covering all twelve authored policy-difference "
            "rules. Lexicographic tie-breaking and no model output determine the selected IDs."
        ),
        "known_result_boundary": (
            "Earlier balanced-challenge results and complete resource-excluded hosted studies "
            "were known. They did not select pairs, items, prompts, endpoints, or pass criteria."
        ),
        "selected_pair_ids": suite["selected_pair_ids"],
        "selected_item_ids": suite["selected_item_ids"],
        "selected_pairs": 10,
        "selected_items": 20,
        "reachable_edges_covered": 10,
        "authored_difference_rules_covered": 12,
        "outcomes_used_for_selection": False,
        "new_model_calls_for_selection": 0,
        "conditional_success_subset_allowed": False,
        "minimal_suite_sha256": sha256_file(MINIMAL_SUITE_PATH),
        "catalog_selected_model_ids": catalog["selected_model_ids"],
        "resource_exhaustion_rule": RESOURCE_EXHAUSTION_RULE,
    }
    receipt["self_digest"] = self_digest(receipt)
    return receipt


def freeze(plan_path: Path, schedule_path: Path, selection_path: Path) -> Json:
    if any(path.exists() for path in (plan_path, schedule_path, selection_path)):
        fail("refusing to overwrite a plan, schedule, or selection receipt")
    if any(path.parent != EXPECTED_ROOT for path in (plan_path, schedule_path, selection_path)):
        fail("freeze files must use the designated hosted-minimal-v1 root")

    coverage = validate_graph(DATASET_ROOT)
    validate_baselines(DATASET_ROOT, BASELINE_ROOT)
    manifest = load_object(DATASET_ROOT / "manifest.json")
    packet = load_object(DATASET_ROOT / "evaluation-prompt-packet.json")
    suite = load_object(MINIMAL_SUITE_PATH)
    catalog = load_object(CATALOG_PATH)
    source_receipt = load_object(SOURCE_VALIDATION_RECEIPT)
    if (
        suite.get("status") != "PROVABLY_MINIMUM_GRAPH_AND_RULE_COMPLETE_SUITE"
        or suite.get("optimality_certificate", {}).get("bound_met") is not True
        or suite.get("coverage", {}).get("reachable_edges") != {"covered": 10, "total": 10}
        or suite.get("coverage", {}).get("changed_rules") != {"covered": 12, "total": 12}
    ):
        fail("minimum suite adequacy certificate changed")
    if (
        catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]
        or catalog.get("credentials_retained") is not False
        or source_receipt.get("upstream_sources_verified") is not True
    ):
        fail("catalog or source-validation boundary changed")

    selection_path.parent.mkdir(parents=True, exist_ok=True)
    selection = build_selection_receipt(suite, catalog)
    selection_path.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lanes = hosted_lanes()
    plan: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "truth_status": "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST",
        "frozen_at_utc": utc_now(),
        "purpose": (
            "Execute a low-cost structural release gate that preserves reachable-edge and "
            "authored-rule coverage for the frozen policy migration."
        ),
        "promotion_rule": (
            "Only the complete set of all 40 terminal outcomes may enter reporting. No partial, "
            "resumed, or selectively retained run is eligible. A lane passes the strict smoke "
            "gate only with 20 valid and action-correct items and 10 correct pairs."
        ),
        "interpretation_boundary": (
            "The minimum suite is a deterministic structural smoke gate over one author-defined "
            "synthetic policy migration. It does not preserve six-context balance, estimate "
            "stochastic reliability, or support unseen-policy, deployment, or model-family claims."
        ),
        "design": {
            "controlled_path": "/active_policy_profile",
            "source_evaluation_pairs": 60,
            "source_evaluation_items": 120,
            "selected_pairs": 10,
            "selected_items": 20,
            "selected_action_support": selected_gold_support(suite),
            "reachable_directed_nonself_transitions_covered": 10,
            "authored_policy_difference_rules_covered": 12,
            "contexts_per_transition": 1,
            "planned_lanes": 2,
            "planned_model_item_cells": 40,
            "attempts_per_cell": 1,
            "item_call_reduction_fraction_against_balanced_diagnostic_suite": 5 / 6,
            "selection_uses_model_outputs": False,
            "naturalistic_case_count": 0,
        },
        "sources": {
            "registry_path": repo_relative(SOURCE_REGISTRY),
            "registry_sha256": sha256_file(SOURCE_REGISTRY),
            "validation_receipt_path": repo_relative(SOURCE_VALIDATION_RECEIPT),
            "validation_receipt_sha256": sha256_file(SOURCE_VALIDATION_RECEIPT),
            "base_policy_path": repo_relative(BASE_POLICY_PATH),
            "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
            "switch_policy_path": repo_relative(SWITCH_POLICY_PATH),
            "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
            "external_requirements_author_labels_separated": True,
        },
        "dataset": {
            "root": repo_relative(DATASET_ROOT),
            "source_study_id": manifest["study_id"],
            "manifest_file_sha256": sha256_file(DATASET_ROOT / "manifest.json"),
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "pair_contract": manifest["pair_contract"],
            "private_git_freeze_before_inference": True,
            "public_before_inference": False,
        },
        "prompt": {
            "path": repo_relative(DATASET_ROOT / "evaluation-prompt-packet.json"),
            "source_study_id": packet["study_id"],
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(DATASET_ROOT / "evaluation-prompt-packet.json"),
            "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
            "complete_decision_schema_visible_to_every_lane": True,
            "numeric_probability_type_visible_to_every_lane": True,
            "same_prompt_bytes_for_every_lane": True,
        },
        "minimum_suite": {
            "path": repo_relative(MINIMAL_SUITE_PATH),
            "file_sha256": sha256_file(MINIMAL_SUITE_PATH),
            "self_digest": suite["self_digest"],
            "derivation_model_calls": suite["model_or_client_calls_to_derive"],
            "optimality_certificate": suite["optimality_certificate"],
            "coverage": suite["coverage"],
        },
        "transition_graph": {
            "coverage_path": repo_relative(COVERAGE_PATH),
            "coverage_sha256": sha256_file(COVERAGE_PATH),
            "directed_nonself_transitions_possible": coverage[
                "directed_nonself_action_transitions_possible"
            ],
            "directed_transitions_semantically_reachable": coverage[
                "directed_action_transitions_semantically_reachable"
            ],
            "structurally_unreachable_transitions": coverage[
                "structurally_unreachable_transitions"
            ],
        },
        "catalog": {
            "path": repo_relative(CATALOG_PATH),
            "file_sha256": sha256_file(CATALOG_PATH),
            "selected_model_ids": catalog["selected_model_ids"],
            "selected_before_new_study_outputs": True,
        },
        "baselines": {
            "root": repo_relative(BASELINE_ROOT),
            "requirements_path": repo_relative(BASELINE_REQUIREMENTS),
            "requirements_sha256": sha256_file(BASELINE_REQUIREMENTS),
            "report_sha256": sha256_file(BASELINE_ROOT / "report.json"),
            "evaluation_gold_loaded": False,
            "model_outputs_loaded": False,
            "comparators": load_object(BASELINE_ROOT / "report.json")["comparators"],
        },
        "formal_lanes": lanes,
        "execution": {
            "base_lane_order": [str(lane["lane_id"]) for lane in lanes],
            "order_rule": "SELECTED_ITEM_MAJOR_WITH_CYCLIC_LANE_ROTATION",
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "interruption_rule": "INCOMPLETE_STUDY_INELIGIBLE_FOR_REPORTING_NO_RESUME",
            "planned_application_posts": 40,
            "minimum_global_request_interval_seconds": 0.75,
            "timeout_seconds": 180,
            "quota_error_rule": "TERMINAL_ERROR_RETAINED_IN_END_TO_END_DENOMINATOR",
            "resource_exhaustion_eligibility_rule": RESOURCE_EXHAUSTION_RULE,
        },
        "budget": {
            "authorization_scope": "USER_AUTHORIZED_CURRENT_AVAILABLE_OPENCODE_GO_QUOTA",
            "subscription_quota_only": True,
            "incremental_cash_cap_usd": 0.0,
            "workflow_initiated_purchase_or_recharge": False,
            "adaptive_stop_on_usage_or_results": False,
        },
        "statistics": {
            "primary_endpoints": [
                "strict_all_items_and_pairs_smoke_pass",
                "end_to_end_policy_transition_pair_accuracy",
                "end_to_end_item_accuracy",
            ],
            "secondary_endpoints": [
                "decision_coverage",
                "pair_coverage",
                "conditional_item_accuracy",
                "conditional_pair_accuracy",
                "per_action_recall",
                "balanced_action_recall",
                "macro_f1",
            ],
            "failure_rule": (
                "Every service, syntax, schema, semantic, quota, and adapter failure remains "
                "incorrect in the scheduled end-to-end denominator."
            ),
            "pair_rule": (
                "A migration pair is correct only when both profile members are valid and "
                "action-correct."
            ),
            "strict_smoke_pass_rule": (
                "A lane passes only if all 20 items yield valid, action-correct decisions and all "
                "10 controlled pairs are correct."
            ),
            "between_lane_boundary": (
                "Model, service adapter, and output-constraining mode differ between lanes; "
                "between-lane differences are descriptive."
            ),
        },
        "selection_receipt": {
            "path": repo_relative(selection_path),
            "file_sha256": sha256_file(selection_path),
            "self_digest": selection["self_digest"],
        },
        "runtime_source_sha256": {path: sha256_file(ROOT / path) for path in RUNTIME_SOURCES},
    }
    schedule = build_schedule(plan, packet, suite)
    plan["execution"]["schedule_path"] = repo_relative(schedule_path)
    plan["execution"]["schedule_sha256"] = schedule["schedule_sha256"]
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schedule_path.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-out", type=Path, default=EXPECTED_ROOT / "study-plan.json")
    parser.add_argument(
        "--schedule-out", type=Path, default=EXPECTED_ROOT / "request-schedule.json"
    )
    parser.add_argument(
        "--selection-out", type=Path, default=EXPECTED_ROOT / "selection-receipt.json"
    )
    args = parser.parse_args()
    plan = freeze(
        args.plan_out.resolve(), args.schedule_out.resolve(), args.selection_out.resolve()
    )
    print(
        canonical_json(
            {
                "status": plan["status"],
                "study_id": plan["study_id"],
                "planned_cells": plan["design"]["planned_model_item_cells"],
                "new_model_calls_before_freeze": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
