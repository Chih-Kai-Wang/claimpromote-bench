"""Tests for the source-bound fresh hidden commitment."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_json
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
    r4_seed = tmp_path / "r4-seed.bin"
    r4_seed.write_bytes(bytes([17]) * 32)
    r4_dataset = tmp_path / "r4-hidden"
    builder.build("test", r4_dataset, r4_seed, confirmatory_rekey=True)
    r4_prompt_manifest = tmp_path / "r4-prompt-manifest.json"
    r4_prompt_manifest.write_text('{"r4":true}\n', encoding="utf-8")
    r4_record = base_commitment.build_commitment(r4_dataset, r4_seed, r4_prompt_manifest)
    r4_record["study_id"] = "claimpromotebench-v1-fresh-confirmatory-2026-08-r4"
    r4_commitment_path = tmp_path / "r4-commitment.json"
    r4_commitment_path.write_text(json.dumps(r4_record), encoding="utf-8")
    r5_seed = tmp_path / "r5-seed.bin"
    r5_seed.write_bytes(bytes([23]) * 32)
    r5_dataset = tmp_path / "r5-hidden"
    builder.build("test", r5_dataset, r5_seed, confirmatory_rekey=True)
    r5_prompt_manifest = tmp_path / "r5-prompt-manifest.json"
    r5_prompt_manifest.write_text('{"r5":true}\n', encoding="utf-8")
    r5_record = base_commitment.build_commitment(r5_dataset, r5_seed, r5_prompt_manifest)
    r5_record["study_id"] = "claimpromotebench-v1-fresh-confirmatory-2026-08-r5"
    r5_commitment_path = tmp_path / "r5-commitment.json"
    r5_commitment_path.write_text(json.dumps(r5_record), encoding="utf-8")

    seed = tmp_path / "seed.bin"
    seed.write_bytes(bytes(range(32)))
    dataset = tmp_path / "hidden"
    builder.build("test", dataset, seed, confirmatory_rekey=True)
    prompt_manifest = tmp_path / "prompt-manifest.json"
    prompt_manifest.write_text('{"fresh":true}\n', encoding="utf-8")
    novelty = novelty_audit.audit(
        None,
        dataset,
        "ledger_verifier",
        "",
        prior_prompt_manifest=ROOT / "configs" / "prior-hidden-prompt-hash-denylist-r6.json",
    )
    assert novelty["prior_prompt_source"]["kind"] == "FROZEN_RELEASED_PROMPT_HASH_DENYLIST"
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
        "study_id": "claimpromotebench-v1-fresh-confirmatory-2026-08-r6",
        "plan_file_sha256": sha256_file(ROOT / "v2" / "fresh-confirmatory-study-plan.json"),
        "dataset_manifest_sha256": sha256_file(dataset / "manifest.json"),
        "planned_cells": 600,
        "contains_request_bodies": False,
        "contains_prompts": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "contains_seed_bytes": False,
        "subscription_authorization": {
            "status": "SUBSCRIPTION_AUTHORIZATION_GATE_PASS",
            "schedule_recomputed_from_exact_request_bodies": True,
            "schedule_cells_verified": 600,
            "incremental_cash_cap_usd": 0.0,
            "pre_post_token_cost_gate": "NOT_APPLICABLE",
        },
    }
    c1_receipt["c1_receipt_sha256"] = sha256_bytes(canonical_json(c1_receipt).encode("utf-8"))
    c1_receipt_path = tmp_path / "c1-receipt.json"
    c1_receipt_path.write_text(json.dumps(c1_receipt), encoding="utf-8")

    original_extras = commitment._SOURCE_EXTRAS
    original_manifest_validator = commitment.validate_manifest
    frozen_manifest = load_json(ROOT / commitment.MANIFEST_PATH)
    frozen_commitment = load_json(
        ROOT / "v2" / "confirmatory" / "c1-r6" / "confirmatory-hidden-commitment.json"
    )

    def validate_frozen_manifest(manifest: dict[str, object]) -> dict[str, object]:
        # This unit test exercises the historical C1 builder after post-study tooling changes.
        # Bind it to the immutable C1 source map instead of rewriting that frozen manifest.
        assert manifest == frozen_manifest
        assert frozen_commitment["runtime_source_manifest_sha256"] == manifest["manifest_sha256"]
        source_files = frozen_commitment["source_files_sha256"]
        assert {path: source_files[path] for path in manifest["files_sha256"]} == manifest[
            "files_sha256"
        ]
        return {"status": "FROZEN_RUNTIME_SOURCE_MANIFEST_PASS"}

    try:
        commitment.validate_manifest = validate_frozen_manifest
        commitment._SOURCE_EXTRAS = tuple(
            path
            for path in original_extras
            if path != "configs/fresh-confirmatory-seed-commitment.json"
        )
        record = commitment.build_confirmatory_commitment(
            dataset,
            seed,
            prompt_manifest,
            "a" * 40,
            [prior_commitment_path, r4_commitment_path, r5_commitment_path],
            novelty_path,
            seed_receipt_path,
            c1_receipt_path,
        )
    finally:
        commitment.validate_manifest = original_manifest_validator
        commitment._SOURCE_EXTRAS = original_extras
    assert record["commitment_version"] == "2.0.0"
    assert record["study_id"] == "claimpromotebench-v1-fresh-confirmatory-2026-08-r6"
    assert record["source_commit"] == "a" * 40
    assert record["runtime_source_manifest_sha256"].startswith("sha256:")
    assert "src/claimpromotebench/__init__.py" in record["source_files_sha256"]
    assert "src/claimpromotebench/statistics.py" in record["source_files_sha256"]
    assert record["pairs"] == 150
    assert record["instances"] == 300
    assert record["contains_hidden_rows"] is False
    assert record["contains_gold_labels"] is False
    assert record["contains_seed_bytes"] is False
    assert len(record["prior_hidden_commitments"]) == 3
    assert all(
        all(differences.values())
        for differences in record["freshness_checks"][
            "component_differences_by_prior_hidden"
        ].values()
    )
    assert record["commitment_sha256"].startswith("sha256:")
    serialized = json.dumps(record, sort_keys=True)
    assert "claim_text" not in serialized
    assert "requested_transition" not in serialized
