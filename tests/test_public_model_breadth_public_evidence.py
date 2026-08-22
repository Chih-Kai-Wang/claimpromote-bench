from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file
from release.tools import build_public_model_breadth_public_evidence as builder
from release.tools import verify_public_model_breadth_public_evidence as verifier

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = (
    ROOT
    / "v2"
    / "balanced-public-challenge"
    / "results"
    / "runs"
    / "opencode-go-qwen3.7-max-full.jsonl"
)


def source_record() -> dict[str, object]:
    first_line = next(line for line in SOURCE_RUN.read_text(encoding="utf-8").splitlines() if line)
    value = json.loads(first_line)
    assert isinstance(value, dict)
    return value


def test_public_derivative_removes_private_text_without_changing_science() -> None:
    row = source_record()
    derived, mapping = builder.derive_public_record(
        row,
        api_key="test-credential-that-is-not-present",
        label="test-row",
    )
    assert derived["raw_response_text"] is None
    assert derived["transport_error"] is None
    assert derived["parse_error_detail"] is None
    assert derived["raw_response_sha256"] == row["raw_response_sha256"]
    assert derived["raw_decision"] == row["raw_decision"]
    assert derived["postgate_decision"] == row["postgate_decision"]
    assert mapping["scientific_fields_unchanged"] is True
    assert builder.scoring_projection(derived) == builder.scoring_projection(row)


def test_private_record_rejects_exact_study_credential() -> None:
    row = source_record()
    credential = "test-private-study-credential-123456789"
    row["raw_response_text"] = credential
    row["raw_response_sha256"] = sha256_bytes(credential.encode("utf-8"))
    with pytest.raises(ValueError, match="privacy finding classes"):
        builder.derive_public_record(row, api_key=credential, label="test-row")


def test_private_record_rejects_provider_response_identifier() -> None:
    row = source_record()
    row["provider_response_id"] = "chatcmpl-privateproviderid12345"
    with pytest.raises(ValueError, match="provider response identifier"):
        builder.derive_public_record(
            row,
            api_key="test-credential-that-is-not-present",
            label="test-row",
        )


def test_private_metadata_rejects_exact_study_credential() -> None:
    credential = "test-private-study-credential-123456789"
    with pytest.raises(ValueError, match="privacy finding classes"):
        builder.validate_private_payload(
            {"execution_note": credential},
            api_key=credential,
            label="execution receipt",
        )


def test_private_metadata_rejects_hidden_reasoning() -> None:
    with pytest.raises(ValueError, match="hidden-reasoning fields"):
        builder.validate_private_payload(
            {"analysis": "private chain of thought"},
            api_key="test-credential-that-is-not-present",
            label="aggregate",
        )


def test_aggregate_transform_changes_only_lane_record_bindings() -> None:
    aggregate = {
        "lanes": [
            {"lane_id": "lane-a", "metrics": {"correct_items": 7}, "run_sha256": "old-a"},
            {"lane_id": "lane-b", "metrics": {"correct_items": 3}, "run_sha256": "old-b"},
        ]
    }
    derived = builder._transform_aggregate(
        aggregate,
        {"lane-a": "sha256:new-a", "lane-b": "sha256:new-b"},
    )
    assert derived["lanes"][0]["run_sha256"] == "sha256:new-a"
    assert derived["lanes"][1]["run_sha256"] == "sha256:new-b"
    assert [lane["metrics"] for lane in derived["lanes"]] == [
        {"correct_items": 7},
        {"correct_items": 3},
    ]
    assert aggregate["lanes"][0]["run_sha256"] == "old-a"


def test_full_seven_lane_public_derivative_replays_without_private_text(tmp_path: Path) -> None:
    plan_path = ROOT / "v2" / "public-model-breadth-v1" / "study-plan.json"
    packet_path = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
    dataset = ROOT / "v2" / "balanced-public-challenge" / "dataset"
    plan = load_json(plan_path)
    assert isinstance(plan, dict)
    lane_order = plan["execution"]["base_lane_order"]
    lane_definitions = {lane["lane_id"]: lane for lane in plan["formal_lanes"]}
    base_rows = [
        json.loads(line) for line in SOURCE_RUN.read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(base_rows) == 180

    source_results = tmp_path / "private-results"
    source_results.mkdir()
    lane_paths: dict[str, Path] = {}
    lane_metrics: list[dict[str, object]] = []
    aggregate_lanes: list[dict[str, object]] = []
    frozen_commit = "e3823dbc2df2ac596df43ee4d6c3b5fb2ff16516"
    gold = load_jsonl(dataset / "gold.jsonl")
    pairs = load_json(dataset / "pairs.json")
    assert isinstance(pairs, list)
    for lane_id in lane_order:
        definition = lane_definitions[lane_id]
        rows = []
        for base in base_rows:
            row = deepcopy(base)
            row.update(
                {
                    "frozen_plan_commit": frozen_commit,
                    "lane_id": lane_id,
                    "model_family": definition["model_family"],
                    "model_requested": definition["model"],
                    "model_returned": definition["model"],
                    "provider": definition["provider"],
                    "routed_provider": definition["provider"],
                    "study_id": plan["study_id"],
                }
            )
            rows.append(row)
        path = source_results / f"{lane_id}.jsonl"
        path.write_text(
            "".join(f"{canonical_json(row)}\n" for row in rows),
            encoding="utf-8",
        )
        metrics = verifier.derive_reporting_metrics(gold, pairs, rows)
        lane_paths[lane_id] = path
        lane_metrics.append(metrics)
        aggregate_lanes.append(
            {
                "lane_id": lane_id,
                "metrics": metrics,
                "run_sha256": sha256_file(path),
            }
        )

    execution = {
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "durable_request_intents": 1260,
        "durable_terminal_records": 1260,
        "frozen_plan_commit": frozen_commit,
        "hidden_reasoning_blocks_retained": False,
        "lane_output_sha256": {path.name: sha256_file(path) for path in lane_paths.values()},
        "partial_resume_used": False,
        "planned_cells": 1260,
        "provider_response_identifiers_retained": False,
        "schema_version": "1.0.0",
        "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
        "study_id": plan["study_id"],
    }
    builder.write_json(source_results / "execution-receipt.json", execution)
    aggregate = {
        "design": "PUBLIC_PRECOMMITTED_MODEL_BREADTH_SUPPLEMENT",
        "deterministic_policy_executor": {
            "end_to_end_item_accuracy": 1.0,
            "end_to_end_pair_accuracy": 1.0,
            "items": 1260,
            "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE",
            "pairs": 630,
        },
        "external_commitment": {"frozen_plan_commit": frozen_commit},
        "interpretation": (
            "Prospectively frozen model-family breadth evidence on a known public synthetic "
            "challenge; not hidden generalization."
        ),
        "lanes": aggregate_lanes,
        "pooled_model_item_cells": verifier.combine_lane_metrics(lane_metrics),
        "schema_version": "1.0.0",
        "scope_limits": {
            "breadth_dimension_added": "MODEL_FAMILY_ONLY",
            "hidden_generalization_claimed": False,
            "naturalistic_cases": 0,
            "ontology_count": 1,
            "policy_count": 1,
            "public_known_challenge": True,
        },
        "service_comparison": {
            "causal_model_ablation_claimed": False,
            "scope": "DESCRIPTIVE_ONLY",
        },
        "status": "COMPLETE",
        "study_id": plan["study_id"],
        "truth_status": "COMPUTATIONAL",
    }
    aggregate_path = tmp_path / "aggregate.json"
    builder.write_json(aggregate_path, aggregate)

    public_results = tmp_path / "public-results"
    receipt = builder.build_public_evidence(
        source_results,
        plan_path,
        aggregate_path,
        public_results,
        api_key="test-credential-that-is-not-present",
    )
    replay = verifier.verify_public_evidence(
        public_results,
        plan_path,
        packet_path,
        dataset,
        api_key="test-credential-that-is-not-present",
    )

    assert receipt["terminal_records_validated"] == 1260
    assert replay == {
        "status": "PUBLIC_MODEL_BREADTH_EVIDENCE_PASS",
        "lanes": 7,
        "items_per_lane": 180,
        "pairs_per_lane": 90,
        "terminal_records": 1260,
        "parseable_records": 1036,
        "privacy_receipt_sha256": receipt["privacy_receipt_sha256"],
    }
    for lane_id, relative in receipt["public_lane_files"].items():
        public_rows = load_jsonl(public_results / relative)
        assert len(public_rows) == 180
        assert all(row["raw_response_text"] is None for row in public_rows)
        assert all(row["transport_error"] is None for row in public_rows)
        assert all(row["parse_error_detail"] is None for row in public_rows)
        assert sha256_file(public_results / relative) != sha256_file(lane_paths[lane_id])
