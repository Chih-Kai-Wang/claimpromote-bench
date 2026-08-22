from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimpromotebench.hashing import sha256_bytes
from release.tools import build_public_model_breadth_public_evidence as builder

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
