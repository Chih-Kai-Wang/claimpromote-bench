from __future__ import annotations

import json
from pathlib import Path

from claimpromotebench.hashing import canonical_json, sha256_bytes
from release.tools import build_fresh_confirmatory_public_evidence as builder
from release.tools import verify_fresh_confirmatory_public_evidence as verifier


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
    registry = {"github_run_id": 123, "status": "FROZEN_SOURCE"}
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
    assert public_envelope["content"][0]["thinking"] == builder.SENTINEL
    assert public_envelope["content"][1]["text"] == '{"action":"ALLOW"}'
    assert public_envelope["reasoning_content"] == builder.SENTINEL
    assert "private reasoning" not in (out / "collected" / "lane-run.jsonl").read_text()
    assert receipt["status"] == "POST_C2_PUBLIC_RELEASE_REDACTION"
    assert receipt["redacted_unique_model_item_cells"] == 1
    assert receipt["scientific_fields_unchanged"] is True
    assert receipt["source_artifact_registry_sha256"] == sha256_bytes(registry_path.read_bytes())
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
