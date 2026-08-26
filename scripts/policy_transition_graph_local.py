#!/usr/bin/env python3
"""Register the frozen policy-transition graph with the local-model runtime."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from local_model_replication import DATASETS

from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]
DATASET_KEY = "policy-transition-graph"
STUDY_SPEC: dict[str, Any] = {
    "study_id": (
        "claimpromotebench-policy-transition-graph-local-model-replication-2026-08-v2"
    ),
    "design": "LOCAL_MODEL_EVALUATION_OF_FROZEN_REACHABLE_POLICY_TRANSITION_GRAPH",
    "dataset_root": ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "dataset",
    "baseline_root": ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "baseline",
    "expected_dataset_fingerprint": (
        "sha256:cf3ece1b05948214cfb60292cb655eb860c92276fd6f0c5c2a36c7618586fa13"
    ),
    "purpose": (
        "Evaluate whether two pinned local open-weight configurations follow every reachable "
        "directed action transition induced by changing only the active policy profile."
    ),
    "interpretation_boundary": (
        "The graph is derived from one author-defined executable policy over synthetic SLSA-"
        "shaped records. Results test conformance on this graph, not unseen-policy "
        "generalization, natural prevalence, deployment fitness, or model-family effects."
    ),
}
RUNTIME_PATHS = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_local_model_replication.py",
    "scripts/analyze_policy_transition_graph_local_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/build_policy_transition_graph_study.py",
    "scripts/finalize_local_model_results.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/freeze_local_model_replications.py",
    "scripts/freeze_policy_transition_graph_local_study.py",
    "scripts/frozen_run_io.py",
    "scripts/local_model_replication.py",
    "scripts/policy_switch.py",
    "scripts/policy_transition_graph_local.py",
    "scripts/run_local_model_replication.py",
    "scripts/run_policy_transition_graph_local_study.py",
    "scripts/slsa_policy.py",
    "scripts/synthetic_policy_output.py",
    "scripts/train_policy_switch_baselines.py",
    "scripts/validate_local_model_replications.py",
    "scripts/validate_policy_transition_graph_study.py",
    "scripts/validate_policy_transition_graph_local_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/hashing.py",
    "v2/schemas/local-model-run-record.schema.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
    "v2/slsa-portability-v1/source-registry.json",
    "v2/policy-switch-v1/policy-contract.json",
)


def self_digest(value: dict[str, Any], field: str = "self_digest") -> str:
    payload = {key: child for key, child in value.items() if key != field}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def register_only_transition_graph() -> None:
    """Restrict generic local adapters to the independently frozen graph study."""

    DATASETS.clear()
    DATASETS[DATASET_KEY] = deepcopy(STUDY_SPEC)
