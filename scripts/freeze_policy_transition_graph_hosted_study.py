#!/usr/bin/env python3
"""Freeze hosted evaluation on the complete reachable policy-transition graph."""

from __future__ import annotations

import argparse
import json
import sys
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
from freeze_policy_switch_study import build_schedule  # noqa: E402
from validate_policy_transition_graph_study import validate as validate_graph  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ID = "claimpromotebench-policy-transition-graph-hosted-2026-08-v1"
EXPECTED_ROOT = ROOT / "v2" / "policy-transition-graph-v1" / "hosted-v1"
SOURCE_HOSTED_PLAN = ROOT / "v2" / "policy-switch-v1" / "hosted-replacement-v2" / "study-plan.json"
SOURCE_VALIDATION_RECEIPT = (
    ROOT / "v2" / "slsa-portability-v1" / "replacement-v2" / "source-validation-receipt.json"
)
LOCAL_GRAPH_ROOT = (
    ROOT
    / "v2"
    / "local-model-replication-v1"
    / "transition-graph-v1"
    / "frozen"
    / "policy-transition-graph"
)
BASELINE_REQUIREMENTS = ROOT / "v2" / "slsa-portability-v1" / "requirements-baseline.txt"
RUNTIME_SOURCES = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_policy_switch_study.py",
    "scripts/analyze_policy_transition_graph_hosted_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/build_policy_transition_graph_study.py",
    "scripts/derive_policy_switch_hosted_replacement_eligibility.py",
    "scripts/derive_policy_transition_graph_hosted_eligibility.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/freeze_policy_switch_study.py",
    "scripts/freeze_policy_transition_graph_hosted_study.py",
    "scripts/freeze_slsa_portability_study.py",
    "scripts/policy_switch.py",
    "scripts/run_policy_switch_study.py",
    "scripts/run_policy_transition_graph_hosted_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/slsa_policy.py",
    "scripts/validate_policy_transition_graph_hosted_study.py",
    "scripts/validate_policy_transition_graph_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/decision_validation.py",
    "src/claimpromotebench/hashing.py",
    "v2/policy-switch-v1/policy-contract.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/schemas/stronger-model-run-record.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
)
RESOURCE_EXHAUSTION_RULE = (
    "Ordinary service, syntax, schema, semantic, adapter, and rate-limit failures remain "
    "incorrect in the complete end-to-end denominator. If a terminal provider error "
    "explicitly states that the shared subscription quota or usage allowance is exhausted, "
    "at least 20 scheduled cells remain, and every later cell is a transport failure, the "
    "complete hosted transition-graph study is ineligible for model-efficacy reporting. In "
    "that case, retain only a redacted full-study exclusion receipt; never select a "
    "successful subset."
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-graph-hosted-freeze: {message}")


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
        lane["lane_id"] = f"opencode-go-{suffix}-policy-transition-graph-hosted-v1"
    return lanes


def build_selection_receipt(
    *, dataset_root: Path, baseline_root: Path, coverage_path: Path, catalog: Json
) -> Json:
    hosted_terminals = EXPECTED_ROOT / "journal" / "terminal-records.jsonl"
    hosted_results = EXPECTED_ROOT / "results" / "aggregate.json"
    local_terminals = LOCAL_GRAPH_ROOT / "journal" / "terminal-records.jsonl"
    local_results = LOCAL_GRAPH_ROOT / "results" / "aggregate.json"
    if hosted_terminals.exists() or hosted_results.exists():
        fail("hosted transition-graph outcomes already exist")
    if local_terminals.exists() or local_results.exists():
        fail("local transition-graph outcomes already exist; route selection is no longer clean")
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "PREINFERENCE_HOSTED_POLICY_TRANSITION_GRAPH_SELECTION",
        "recorded_at_utc": utc_now(),
        "study_id": STUDY_ID,
        "graph_selection_basis": (
            "Static reachability of the already published author-defined policy executor: all "
            "ten reachable directed nonself action transitions, six contexts per transition."
        ),
        "route_selection_basis": (
            "Reuse the two hosted configurations that produced usable decision coverage in the "
            "earlier balanced public challenge. No transition-graph output was available."
        ),
        "known_prior_result_boundary": (
            "Earlier balanced-challenge coverage and a fully excluded quota-confounded hosted "
            "policy-switch run were known. They selected service configurations, not graph "
            "edges, contexts, labels, prompts, endpoints, or reporting rules."
        ),
        "outcomes_used_to_choose_graph_edges_or_contexts": False,
        "hosted_transition_graph_terminal_records_before_freeze": 0,
        "local_transition_graph_terminal_records_before_freeze": 0,
        "new_model_calls_for_selection": 0,
        "evaluation_gold_used_to_train_comparators": False,
        "dataset_fingerprint": manifest["dataset_fingerprint"],
        "packet_sha256": packet["packet_sha256"],
        "dataset_manifest_sha256": sha256_file(dataset_root / "manifest.json"),
        "transition_coverage_sha256": sha256_file(coverage_path),
        "baseline_report_sha256": sha256_file(baseline_root / "report.json"),
        "catalog_selected_model_ids": catalog["selected_model_ids"],
        "resource_exhaustion_rule": RESOURCE_EXHAUSTION_RULE,
    }
    receipt["self_digest"] = self_digest(receipt)
    return receipt


def freeze(
    *,
    dataset_root: Path,
    baseline_root: Path,
    coverage_path: Path,
    catalog_path: Path,
    plan_path: Path,
    schedule_path: Path,
    selection_path: Path,
) -> Json:
    if any(path.exists() for path in (plan_path, schedule_path, selection_path)):
        fail("refusing to overwrite a plan, schedule, or selection receipt")
    if any(path.parent != EXPECTED_ROOT for path in (plan_path, schedule_path, selection_path)):
        fail("freeze files must use the designated hosted-v1 root")
    if catalog_path.parent != EXPECTED_ROOT:
        fail("catalog snapshot must use the designated hosted-v1 root")

    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    baseline = load_object(baseline_root / "report.json")
    catalog = load_object(catalog_path)
    coverage = validate_graph(dataset_root)
    expected_coverage = load_object(coverage_path)
    if canonical_json(coverage) != canonical_json(expected_coverage):
        fail("transition coverage does not recompute byte-exactly")
    if catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]:
        fail("catalog does not contain the selected hosted configurations")
    if catalog.get("credentials_retained") is not False:
        fail("catalog credential boundary changed")
    if (
        baseline.get("evaluation_gold_loaded") is not False
        or baseline.get("model_outputs_loaded") is not False
    ):
        fail("baseline data-access boundary changed")

    selection_path.parent.mkdir(parents=True, exist_ok=True)
    selection = build_selection_receipt(
        dataset_root=dataset_root,
        baseline_root=baseline_root,
        coverage_path=coverage_path,
        catalog=catalog,
    )
    selection_path.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lanes = hosted_lanes()
    source_receipt = load_object(SOURCE_VALIDATION_RECEIPT)
    if source_receipt.get("upstream_sources_verified") is not True:
        fail("source receipt did not verify upstream bytes")

    plan: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "truth_status": "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST",
        "frozen_at_utc": utc_now(),
        "purpose": (
            "Evaluate two hosted model-service configurations on every semantically reachable "
            "directed action transition induced by changing only the active policy profile."
        ),
        "promotion_rule": (
            "Only the complete set of all 240 terminal outcomes may enter reporting. No partial, "
            "resumed, or selectively retained run is eligible. The prospectively specified "
            "shared-resource rule may instead exclude the complete hosted study."
        ),
        "interpretation_boundary": (
            "The graph is derived from one author-defined executable policy over synthetic "
            "SLSA-shaped records. Results test conformance on this graph, not unseen-policy "
            "generalization, natural prevalence, deployment fitness, or model-family effects."
        ),
        "design": {
            "controlled_path": "/active_policy_profile",
            "development_pairs": 30,
            "development_items": 60,
            "evaluation_pairs": 60,
            "evaluation_items": 120,
            "evaluation_factors": 10,
            "evaluation_action_support": manifest["evaluation"]["action_counts"],
            "evaluation_profile_action_support": manifest["evaluation"]["profile_action_counts"],
            "reachable_directed_nonself_transitions": 10,
            "contexts_per_transition": 6,
            "planned_lanes": 2,
            "planned_model_item_cells": 240,
            "attempts_per_cell": 1,
            "selection_uses_new_study_outputs": False,
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
            "root": repo_relative(dataset_root),
            "source_study_id": manifest["study_id"],
            "manifest_file_sha256": sha256_file(dataset_root / "manifest.json"),
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "pair_contract": manifest["pair_contract"],
            "private_git_freeze_before_inference": True,
            "public_before_inference": False,
        },
        "prompt": {
            "path": repo_relative(dataset_root / "evaluation-prompt-packet.json"),
            "source_study_id": packet["study_id"],
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(dataset_root / "evaluation-prompt-packet.json"),
            "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
            "complete_decision_schema_visible_to_every_lane": True,
            "numeric_probability_type_visible_to_every_lane": True,
            "same_prompt_bytes_for_every_lane": True,
        },
        "catalog": {
            "path": repo_relative(catalog_path),
            "file_sha256": sha256_file(catalog_path),
            "selected_model_ids": catalog["selected_model_ids"],
            "selected_before_new_study_outputs": True,
        },
        "baselines": {
            "root": repo_relative(baseline_root),
            "requirements_path": repo_relative(BASELINE_REQUIREMENTS),
            "requirements_sha256": sha256_file(BASELINE_REQUIREMENTS),
            "report_sha256": sha256_file(baseline_root / "report.json"),
            "algorithm": baseline["algorithm"],
            "configuration": baseline["configuration"],
            "evaluation_gold_loaded": baseline["evaluation_gold_loaded"],
            "model_outputs_loaded": baseline["model_outputs_loaded"],
            "comparators": baseline["comparators"],
        },
        "transition_graph": {
            "coverage_path": repo_relative(coverage_path),
            "coverage_sha256": sha256_file(coverage_path),
            "directed_nonself_transitions_possible": coverage[
                "directed_nonself_action_transitions_possible"
            ],
            "directed_transitions_semantically_reachable": coverage[
                "directed_action_transitions_semantically_reachable"
            ],
            "directed_transitions_covered": coverage["directed_action_transitions_covered"],
            "structurally_unreachable_transitions": coverage[
                "structurally_unreachable_transitions"
            ],
            "authored_profile_difference_rules_covered": coverage[
                "authored_profile_difference_rules_covered"
            ],
            "authored_profile_difference_rules_total": coverage[
                "authored_profile_difference_rules_total"
            ],
        },
        "formal_lanes": lanes,
        "execution": {
            "base_lane_order": [str(lane["lane_id"]) for lane in lanes],
            "order_rule": "ITEM_MAJOR_WITH_CYCLIC_LANE_ROTATION",
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "interruption_rule": "INCOMPLETE_STUDY_INELIGIBLE_FOR_MANUSCRIPT_NO_RESUME",
            "planned_application_posts": 240,
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
                "A transition pair is correct only when both profile members are valid and "
                "action-correct."
            ),
            "within_lane_identification": (
                "Within each lane, pair members differ only in active_policy_profile. Pair "
                "correctness tests sensitivity to the published policy change on the frozen graph."
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
    schedule = build_schedule(plan, packet)
    plan["execution"]["schedule_path"] = repo_relative(schedule_path)
    plan["execution"]["schedule_sha256"] = schedule["schedule_sha256"]
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schedule_path.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    parser.add_argument("--schedule-out", type=Path, required=True)
    parser.add_argument("--selection-out", type=Path, required=True)
    args = parser.parse_args()
    plan = freeze(
        dataset_root=args.dataset_root.resolve(),
        baseline_root=args.baseline_root.resolve(),
        coverage_path=args.coverage.resolve(),
        catalog_path=args.catalog.resolve(),
        plan_path=args.plan_out.resolve(),
        schedule_path=args.schedule_out.resolve(),
        selection_path=args.selection_out.resolve(),
    )
    print(
        canonical_json(
            {
                "status": plan["status"],
                "study_id": plan["study_id"],
                "planned_cells": plan["design"]["planned_model_item_cells"],
                "transition_graph_model_calls_before_freeze": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
