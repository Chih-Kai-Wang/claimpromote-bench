"""Tests for public-safe prompt-hash recovery from a void zero-POST realization."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "recover_void_confirmatory_prompt_hashes.py"
    spec = importlib.util.spec_from_file_location("recover_void_prompt_hashes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    hashes = [sha256_bytes(f"void-r5-prompt-{index}".encode()) for index in range(300)]
    packet = {
        "schema_version": "1.0.0",
        "study_id": "study-r5",
        "dataset_manifest_sha256": sha256_bytes(b"dataset-r5"),
        "prompt_arm": "ledger_verifier",
        "records": [{"prompt_sha256": value} for value in hashes],
    }
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode())
    packet_path = tmp_path / "packet.json"
    _write(packet_path, packet)

    commitment = {
        "study_id": "study-r5",
        "source_commit": "a" * 40,
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "c1_receipt": {"packet_sha256": packet["packet_sha256"]},
        "prompt_novelty_audit": {
            "fresh_prompt_set_sha256": sha256_bytes(canonical_json(sorted(hashes)).encode())
        },
    }
    commitment["commitment_sha256"] = sha256_bytes(canonical_json(commitment).encode())
    commitment_path = tmp_path / "commitment.json"
    _write(commitment_path, commitment)

    run = {
        "github_run_id": 123,
        "commitment_sha256": commitment["commitment_sha256"],
        "model_post_intents": 0,
        "model_calls": 0,
        "cost_usd": 0.0,
    }
    run_path = tmp_path / "run.json"
    _write(run_path, run)
    return packet_path, commitment_path, run_path


def test_recovery_outputs_only_a_900_hash_union(tmp_path: Path) -> None:
    module = _load_script()
    packet, commitment, run = _fixtures(tmp_path)
    denylist, receipt = module.recover(
        base_path=ROOT / "configs" / "prior-hidden-prompt-hash-denylist-r5.json",
        packet_path=packet,
        commitment_path=commitment,
        c1_run_receipt_path=run,
        recovery_run_id=456,
    )
    assert denylist["prompt_count"] == 900
    assert denylist["unique_prompt_count"] == 900
    assert denylist["contains_prompt_text"] is False
    assert denylist["contains_hidden_rows"] is False
    assert denylist["contains_gold_labels"] is False
    assert receipt["recovered_prompt_count"] == 300
    assert receipt["application_post_count"] == 0
    assert receipt["model_inference_evidence"] == "NONE"


def test_recovery_rejects_a_packet_not_bound_at_c1(tmp_path: Path) -> None:
    module = _load_script()
    packet, commitment, run = _fixtures(tmp_path)
    value = json.loads(packet.read_text(encoding="utf-8"))
    value["records"][0]["prompt_sha256"] = sha256_bytes(b"tampered")
    _write(packet, value)
    with pytest.raises(ValueError, match="self-digest mismatch"):
        module.recover(
            base_path=ROOT / "configs" / "prior-hidden-prompt-hash-denylist-r5.json",
            packet_path=packet,
            commitment_path=commitment,
            c1_run_receipt_path=run,
            recovery_run_id=456,
        )
