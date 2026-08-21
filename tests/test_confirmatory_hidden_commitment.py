"""Tests for the source-bound fresh hidden commitment."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_confirmatory_commitment_is_fresh_source_bound_and_public_safe(tmp_path: Path) -> None:
    builder = _load_script("build_v1_dataset")
    base_commitment = _load_script("make_hidden_test_commitment")
    novelty_audit = _load_script("audit_hidden_prompt_novelty")
    commitment = _load_script("make_confirmatory_hidden_commitment")
    prior_seed = tmp_path / "prior-seed.bin"
    prior_seed.write_bytes(bytes(reversed(range(32))))
    prior_dataset = tmp_path / "prior-hidden"
    builder.build("test", prior_dataset, prior_seed)
    prior_prompt_manifest = tmp_path / "prior-prompt-manifest.json"
    prior_prompt_manifest.write_text("{}\n", encoding="utf-8")
    prior_record = base_commitment.build_commitment(
        prior_dataset, prior_seed, prior_prompt_manifest
    )
    prior_commitment_path = tmp_path / "prior-commitment.json"
    prior_commitment_path.write_text(json.dumps(prior_record), encoding="utf-8")

    seed = tmp_path / "seed.bin"
    seed.write_bytes(bytes(range(32)))
    dataset = tmp_path / "hidden"
    builder.build("test", dataset, seed, confirmatory_rekey=True)
    prompt_manifest = tmp_path / "prompt-manifest.json"
    prompt_manifest.write_text('{"fresh":true}\n', encoding="utf-8")
    novelty = novelty_audit.audit(prior_dataset, dataset, "ledger_verifier", "")
    novelty_path = tmp_path / "novelty.json"
    novelty_path.write_text(json.dumps(novelty, sort_keys=True) + "\n", encoding="utf-8")
    seed_receipt = {
        "derived_seed_sha256": sha256_bytes(seed.read_bytes()),
        "rejection_sampling_permitted": False,
    }
    seed_receipt["seed_derivation_receipt_sha256"] = sha256_bytes(
        canonical_json(seed_receipt).encode("utf-8")
    )
    seed_receipt_path = tmp_path / "seed-receipt.json"
    seed_receipt_path.write_text(json.dumps(seed_receipt), encoding="utf-8")
    c1_receipt = {
        "dataset_manifest_sha256": sha256_file(dataset / "manifest.json"),
        "planned_cells": 600,
        "contains_request_bodies": False,
        "contains_prompts": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "contains_seed_bytes": False,
    }
    c1_receipt["c1_receipt_sha256"] = sha256_bytes(canonical_json(c1_receipt).encode("utf-8"))
    c1_receipt_path = tmp_path / "c1-receipt.json"
    c1_receipt_path.write_text(json.dumps(c1_receipt), encoding="utf-8")

    record = commitment.build_confirmatory_commitment(
        dataset,
        seed,
        prompt_manifest,
        "a" * 40,
        prior_commitment_path,
        novelty_path,
        seed_receipt_path,
        c1_receipt_path,
    )
    assert record["commitment_version"] == "2.0.0"
    assert record["source_commit"] == "a" * 40
    assert record["pairs"] == 150
    assert record["instances"] == 300
    assert record["contains_hidden_rows"] is False
    assert record["contains_gold_labels"] is False
    assert record["contains_seed_bytes"] is False
    assert all(record["freshness_checks"]["component_differences"].values())
    assert record["commitment_sha256"].startswith("sha256:")
    serialized = json.dumps(record, sort_keys=True)
    assert "claim_text" not in serialized
    assert "requested_transition" not in serialized
