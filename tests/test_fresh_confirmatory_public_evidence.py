from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimpromotebench.hashing import canonical_json, sha256_bytes
from release.tools import build_fresh_confirmatory_public_evidence as builder
from release.tools import build_persistent_reviewer_evidence_manifest as persistent_manifest
from release.tools import verify_fresh_confirmatory_public_evidence as verifier

ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{canonical_json(row)}\n" for row in rows), encoding="utf-8")


def test_post_c2_release_redacts_reasoning_without_changing_science(tmp_path: Path) -> None:
    source = tmp_path / "source"
    out = tmp_path / "public"
    envelope = {
        "content": [
            {"signature": "", "thinking": "private reasoning", "type": "thinking"},
            {"text": '{"action":"ALLOW"}', "type": "text"},
        ],
        "id": "response-1",
        "reasoning_content": "another private trace",
    }
    row = {
        "application_post_count": 1,
        "item_id": "item-1",
        "lane_id": "lane-1",
        "parse_status": "OK",
        "raw_decision": {"action": "ALLOW"},
        "raw_final_text": '{"action":"ALLOW"}',
        "sanitized_provider_envelope": envelope,
        "sanitized_provider_envelope_sha256": sha256_bytes(
            canonical_json(envelope).encode("utf-8")
        ),
        "sequence": 0,
    }
    _write_jsonl(source / "collected" / "lane-run.jsonl", [row])
    c2_row = dict(row, c2_cell_outcome="RESPONSE_RECORDED")
    _write_jsonl(source / "collected" / "lane-c2-complete.jsonl", [c2_row])
    (source / "safe.json").write_text('{"status":"SAFE"}\n', encoding="utf-8")
    c2_receipt = {"sealed_cells": 1, "status": "C2"}
    c2_receipt["c2_receipt_sha256"] = sha256_bytes(canonical_json(c2_receipt).encode("utf-8"))
    c2_path = source / "collected" / "c2-receipt.json"
    c2_path.write_text(json.dumps(c2_receipt), encoding="utf-8")
    registry = {
        "artifacts": [
            {
                "artifact_id": 456,
                "name": "claimpromotebench-fresh-confirmatory-reviewer-evidence",
                "zip_sha256": "sha256:artifact",
            }
        ],
        "github_run_id": 123,
        "status": "FROZEN_SOURCE",
    }
    registry["source_artifact_registry_sha256"] = sha256_bytes(
        canonical_json(registry).encode("utf-8")
    )
    registry_path = tmp_path / "source-artifacts.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    receipt = builder.build_public_release(
        source,
        out,
        github_run_id=123,
        artifact_registry_path=registry_path,
    )
    public_row = json.loads((out / "collected" / "lane-run.jsonl").read_text(encoding="utf-8"))
    assert public_row["raw_decision"] == row["raw_decision"]
    assert public_row["raw_final_text"] == row["raw_final_text"]
    assert (
        public_row["pre_redaction_sanitized_provider_envelope_sha256"]
        == row["sanitized_provider_envelope_sha256"]
    )
    public_envelope = public_row["sanitized_provider_envelope"]
    assert public_envelope["content"] == [{"text": '{"action":"ALLOW"}', "type": "text"}]
    assert "reasoning_content" not in public_envelope
    assert "thinking" not in json.dumps(public_envelope)
    assert "private reasoning" not in (out / "collected" / "lane-run.jsonl").read_text()
    assert receipt["status"] == "POST_C2_PUBLIC_RELEASE_REDACTION"
    assert receipt["redacted_unique_model_item_cells"] == 1
    assert receipt["scientific_fields_unchanged"] is True
    assert receipt["removed_content_blocks_including_raw_and_c2_copies"] == 2
    assert receipt["source_artifact_registry_file_sha256"] == sha256_bytes(
        registry_path.read_bytes()
    )
    assert receipt["source_artifact_registry_sha256"] == registry["source_artifact_registry_sha256"]
    assert receipt["source_c2_receipt"]["self_digest"] == c2_receipt["c2_receipt_sha256"]
    assert (out / "provenance" / "source-artifacts.json").read_bytes() == (
        registry_path.read_bytes()
    )
    assert (out / "safe.json").read_bytes() == (source / "safe.json").read_bytes()


def test_analysis_projection_ignores_only_provenance_hashes() -> None:
    source = {
        "aggregate_sha256": "sha256:source",
        "scores": {"lane": {"raw": {"item_accuracy": 0.8}, "run_sha256": "sha256:a"}},
    }
    public = {
        "aggregate_sha256": "sha256:public",
        "scores": {"lane": {"raw": {"item_accuracy": 0.8}, "run_sha256": "sha256:b"}},
    }
    assert verifier._scientific_analysis(source) == verifier._scientific_analysis(public)


@pytest.mark.parametrize(
    "envelope",
    [
        {
            "content": [{"text": "safe", "type": "text", "unknown": "value"}],
            "id": "response-1",
        },
        {
            "content": [{"data": "opaque", "type": "tool"}],
            "id": "response-1",
        },
        {
            "content": [{"text": "safe", "type": "text"}],
            "id": "response-1",
            "unknown": "value",
        },
    ],
)
def test_public_provider_envelope_fails_closed_on_unknown_fields(
    envelope: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        builder.derive_public_provider_envelope(envelope, builder.RedactionStats())


def test_committed_fresh_confirmatory_evidence_has_complete_persistent_manifest() -> None:
    evidence = ROOT / "release" / "reviewer-evidence-source" / "fresh-confirmatory"
    manifest = persistent_manifest.verify_manifest(
        evidence,
        evidence / "PERMANENT-MANIFEST.json",
    )
    assert manifest["file_count"] == len(manifest["files"])
    assert manifest["file_count"] > 0
    assert manifest["scope"]["hidden_reasoning_present"] is False
    assert manifest["scope"]["scientific_analysis_payload_byte_identical"] is True


def test_persistent_manifest_ignores_only_lean_build_cache(tmp_path: Path) -> None:
    evidence = tmp_path / "reviewer-evidence"
    evidence.mkdir()
    (evidence / "evidence.json").write_text('{"status":"FROZEN"}\n', encoding="utf-8")
    manifest_path = evidence / "PERMANENT-MANIFEST.json"
    persistent_manifest.build_manifest(
        evidence,
        manifest_path,
        workflow_run_id=123,
        artifact_id=456,
        artifact_zip_sha256="sha256:artifact",
        head_commit="a" * 40,
    )

    lean_cache = evidence / "dataset" / ".lake" / "build" / "lib" / "cache.olean"
    lean_cache.parent.mkdir(parents=True)
    lean_cache.write_bytes(b"rebuildable Lean output")
    persistent_manifest.verify_manifest(evidence, manifest_path)

    (evidence / "unmanifested.json").write_text('{"status":"EXTRA"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="file coverage or digest mismatch"):
        persistent_manifest.verify_manifest(evidence, manifest_path)


@pytest.mark.parametrize(
    ("relative", "digest_key"),
    [
        ("v2/confirmatory/r6-execution/study-result.json", "study_result_sha256"),
        (
            "v2/confirmatory/r6-execution/frozen-manifest-metadata-correction.json",
            "self_digest",
        ),
    ],
)
def test_r6_result_receipts_have_valid_self_digests(relative: str, digest_key: str) -> None:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    observed = value.pop(digest_key)
    assert observed == sha256_bytes(canonical_json(value).encode("utf-8"))
