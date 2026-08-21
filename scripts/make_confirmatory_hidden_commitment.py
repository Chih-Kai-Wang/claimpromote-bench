#!/usr/bin/env python3
"""Emit a source-bound public commitment for a fresh confirmatory hidden realization."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from make_hidden_test_commitment import build_commitment  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SOURCE_FILES = (
    ".github/workflows/confirmatory-hidden-freeze.yml",
    ".github/workflows/confirmatory-hidden-study.yml",
    "configs/v1-benchmark-plan.json",
    "policies/math-evidence-transition-1.0.0.json",
    "schemas/agent-decision.schema.json",
    "schemas/benchmark-input-v1.schema.json",
    "schemas/gold-label.schema.json",
    "scripts/build_v1_dataset.py",
    "scripts/audit_hidden_prompt_novelty.py",
    "scripts/analyze_confirmatory_hidden_study.py",
    "scripts/build_confirmatory_c1.py",
    "scripts/confirmatory_power_analysis.py",
    "scripts/freeze_prompt_manifest.py",
    "scripts/finalize_confirmatory_c2.py",
    "scripts/derive_confirmatory_seed.py",
    "scripts/make_hidden_test_commitment.py",
    "scripts/predict_confirmatory_baselines.py",
    "scripts/run_confirmatory_service_study.py",
    "scripts/train_confirmatory_shallow_baseline.py",
    "scripts/validate_confirmatory_c0.py",
    "scripts/validate_v1_plan.py",
    "src/claimpromotebench/confirmatory_baseline.py",
    "src/claimpromotebench/formal.py",
    "src/claimpromotebench/prompts.py",
    "tools/drand/fetch_verified_beacon.mjs",
    "tools/drand/package-lock.json",
    "v2/confirmatory/power-analysis-r3.json",
    "v2/confirmatory/power-assumptions-r3.json",
    "v2/confirmatory/public-dev-text-nb-v1.json",
    "v2/fresh-confirmatory-study-plan.json",
)
_FRESH_COMPONENTS = (
    "manifest.json",
    "author-items.jsonl",
    "inputs.jsonl",
    "gold.jsonl",
    "pairs.json",
)


def build_confirmatory_commitment(
    dataset_dir: Path,
    seed_file: Path,
    prompt_manifest: Path,
    source_commit: str,
    prior_commitment_path: Path,
    novelty_report_path: Path,
    seed_receipt_path: Path,
    c1_receipt_path: Path,
) -> Json:
    """Build a public-safe record and prove it differs from the prior hidden realization."""

    source_commit = source_commit.lower()
    if not _COMMIT.fullmatch(source_commit):
        raise ValueError("source commit must be a full 40-character lowercase Git SHA")
    prior = load_json(prior_commitment_path)
    if not isinstance(prior, dict):
        raise ValueError("prior commitment must be an object")
    base = build_commitment(dataset_dir, seed_file, prompt_manifest)
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    if dataset_manifest.get("confirmatory_rekey_enabled") is not True:
        raise ValueError("fresh confirmatory dataset lacks private seed-keyed identifiers")
    novelty = load_json(novelty_report_path)
    if not isinstance(novelty, dict) or novelty.get("status") != "ZERO_EXACT_PROMPT_OVERLAP":
        raise ValueError("fresh confirmatory prompt novelty audit did not pass")
    if novelty.get("exact_prompt_overlap_count") != 0:
        raise ValueError("fresh confirmatory prompts overlap the prior hidden prompts")
    if novelty.get("prior_dataset_manifest_sha256") != prior.get("dataset_manifest_sha256"):
        raise ValueError("prompt novelty audit is not bound to the registered prior hidden set")
    if novelty.get("fresh_dataset_manifest_sha256") != base.get("dataset_manifest_sha256"):
        raise ValueError("prompt novelty audit is not bound to the fresh hidden set")
    novelty_payload = dict(novelty)
    novelty_digest = novelty_payload.pop("novelty_report_sha256", None)
    if novelty_digest != sha256_bytes(canonical_json(novelty_payload).encode("utf-8")):
        raise ValueError("prompt novelty report digest mismatch")
    seed_receipt = load_json(seed_receipt_path)
    seed_payload = dict(seed_receipt)
    seed_digest = seed_payload.pop("seed_derivation_receipt_sha256", None)
    if seed_digest != sha256_bytes(canonical_json(seed_payload).encode("utf-8")):
        raise ValueError("seed derivation receipt digest mismatch")
    if seed_receipt.get("derived_seed_sha256") != base.get("hidden_seed_sha256"):
        raise ValueError("hidden dataset is not bound to the single beacon-derived seed")
    if seed_receipt.get("rejection_sampling_permitted") is not False:
        raise ValueError("seed derivation receipt permits selection")
    c1_receipt = load_json(c1_receipt_path)
    c1_payload = dict(c1_receipt)
    c1_digest = c1_payload.pop("c1_receipt_sha256", None)
    if c1_digest != sha256_bytes(canonical_json(c1_payload).encode("utf-8")):
        raise ValueError("C1 receipt digest mismatch")
    if c1_receipt.get("dataset_manifest_sha256") != base.get("dataset_manifest_sha256"):
        raise ValueError("C1 receipt is not bound to the fresh hidden dataset")
    study_id = str(c1_receipt.get("study_id", ""))
    if not study_id or c1_receipt.get("plan_file_sha256") != sha256_file(
        ROOT / "v2" / "fresh-confirmatory-study-plan.json"
    ):
        raise ValueError("C1 receipt is not bound to the current study plan")
    if c1_receipt.get("planned_cells") != 600:
        raise ValueError("C1 receipt does not bind all 600 model-item cells")
    if any(
        c1_receipt.get(key) is not False
        for key in (
            "contains_request_bodies",
            "contains_prompts",
            "contains_hidden_rows",
            "contains_gold_labels",
            "contains_seed_bytes",
        )
    ):
        raise ValueError("C1 receipt contains private payload")
    old_components = prior.get("dataset_components")
    new_components = base.get("dataset_components")
    if not isinstance(old_components, dict) or not isinstance(new_components, dict):
        raise ValueError("commitment component maps are missing")
    changed = {
        name: old_components.get(name) != new_components.get(name) for name in _FRESH_COMPONENTS
    }
    if not all(changed.values()):
        unchanged = sorted(name for name, differs in changed.items() if not differs)
        raise ValueError(f"fresh hidden realization reused prior components: {unchanged}")
    if prior.get("hidden_seed_sha256") == base.get("hidden_seed_sha256"):
        raise ValueError("fresh hidden realization reused the prior seed")
    if prior.get("prompt_manifest_sha256") == base.get("prompt_manifest_sha256"):
        raise ValueError("fresh hidden realization reused the prior prompt manifest")

    base_commitment_sha256 = str(base.pop("commitment_sha256"))
    record: Json = {
        **base,
        "commitment_version": "2.0.0",
        "study_id": study_id,
        "source_commit": source_commit,
        "source_files_sha256": {
            relative: sha256_file(ROOT / relative) for relative in _SOURCE_FILES
        },
        "base_v1_commitment_sha256": base_commitment_sha256,
        "prior_hidden_commitment_sha256": prior.get("commitment_sha256"),
        "prior_hidden_dataset_manifest_sha256": prior.get("dataset_manifest_sha256"),
        "freshness_checks": {
            "all_required_dataset_components_differ_from_prior_hidden": True,
            "component_differences": changed,
            "hidden_seed_differs_from_prior_hidden": True,
            "prompt_manifest_differs_from_prior_hidden": True,
            "private_seed_keyed_identifiers": True,
            "exact_registered_prompt_overlap_with_prior_hidden": 0,
        },
        "prompt_novelty_audit": novelty,
        "prompt_novelty_report_file_sha256": sha256_file(novelty_report_path),
        "seed_derivation_receipt": seed_receipt,
        "seed_derivation_receipt_file_sha256": sha256_file(seed_receipt_path),
        "c1_receipt": c1_receipt,
        "c1_receipt_file_sha256": sha256_file(c1_receipt_path),
        "interpretation_boundary": (
            "This is a fresh seeded realization of the frozen v1 generator and factor templates, "
            "not a new naturalistic corpus or a new benchmark ontology."
        ),
    }
    record["commitment_sha256"] = sha256_bytes(canonical_json(record).encode("utf-8"))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--prompt-manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--prior-commitment",
        type=Path,
        default=ROOT / "configs" / "v1-hidden-test-commitment.json",
    )
    parser.add_argument("--novelty-report", type=Path, required=True)
    parser.add_argument("--seed-receipt", type=Path, required=True)
    parser.add_argument("--c1-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    record = build_confirmatory_commitment(
        args.dataset.resolve(),
        args.seed_file.resolve(),
        args.prompt_manifest.resolve(),
        args.source_commit,
        args.prior_commitment.resolve(),
        args.novelty_report.resolve(),
        args.seed_receipt.resolve(),
        args.c1_receipt.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "CONFIRMATORY_COMMITMENT_READY",
                "study_id": record["study_id"],
                "pairs": record["pairs"],
                "instances": record["instances"],
                "commitment_sha256": record["commitment_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
