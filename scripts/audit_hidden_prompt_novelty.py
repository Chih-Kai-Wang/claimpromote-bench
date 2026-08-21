#!/usr/bin/env python3
"""Prove that a fresh hidden realization shares no exact registered prompts with the prior one."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_prior_prompt_hash_denylist import validate_denylist  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl, validate_dataset  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.prompts import render_prompt  # noqa: E402

Json = dict[str, Any]


def _prompt_hashes(dataset_dir: Path, arm: str, suffix: str) -> list[str]:
    validate_dataset(dataset_dir, ROOT)
    manifest = load_json(dataset_dir / "manifest.json")
    policy = load_policy(ROOT / "policies" / str(manifest["policy_file"]))
    hashes: list[str] = []
    for item in sorted(load_jsonl(dataset_dir / "inputs.jsonl"), key=lambda row: str(row["id"])):
        rendered = render_prompt(
            item,
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=str(manifest["evaluation_time"]),
        )
        prompt = f"{rendered.rstrip()}\n{suffix}" if suffix else f"{rendered.rstrip()}\n"
        hashes.append(sha256_bytes(prompt.encode("utf-8")))
    return hashes


def audit(
    prior_dataset: Path | None,
    fresh_dataset: Path,
    arm: str,
    suffix: str,
    prior_prompt_manifest: Path | None = None,
) -> Json:
    if (prior_dataset is None) == (prior_prompt_manifest is None):
        raise ValueError("provide exactly one prior prompt source")
    prior_source: Json
    if prior_prompt_manifest is not None:
        frozen = load_json(prior_prompt_manifest)
        validate_denylist(frozen)
        if (
            frozen.get("prompt_arm") != arm
            or frozen.get("provider_neutral_control_suffix") != suffix
        ):
            raise ValueError("prior prompt denylist uses a different prompt configuration")
        prior = [str(value) for value in frozen["prompt_sha256"]]
        prior_dataset_manifest_sha256 = str(frozen["dataset_manifest_sha256"])
        prior_source = {
            "kind": "FROZEN_RELEASED_PROMPT_HASH_DENYLIST",
            "file_sha256": sha256_file(prior_prompt_manifest),
            "denylist_sha256": frozen["denylist_sha256"],
            "source_prompt_packet_sha256": frozen["source"]["prompt_packet_sha256"],
        }
    else:
        assert prior_dataset is not None
        prior = _prompt_hashes(prior_dataset, arm, suffix)
        prior_dataset_manifest_sha256 = sha256_file(prior_dataset / "manifest.json")
        prior_source = {
            "kind": "DETERMINISTIC_DATASET_RERENDER",
            "dataset_manifest_sha256": prior_dataset_manifest_sha256,
        }
    fresh = _prompt_hashes(fresh_dataset, arm, suffix)
    if len(prior) != 300 or len(fresh) != 300:
        raise ValueError("both hidden realizations must contain exactly 300 prompts")
    if len(set(prior)) != len(prior) or len(set(fresh)) != len(fresh):
        raise ValueError("a hidden realization contains duplicate exact prompts")
    overlap = set(prior) & set(fresh)
    if overlap:
        raise ValueError(f"fresh realization reuses {len(overlap)} exact prior prompts")
    report: Json = {
        "schema_version": "1.0.0",
        "status": "ZERO_EXACT_PROMPT_OVERLAP",
        "prompt_arm": arm,
        "provider_neutral_control_suffix": suffix,
        "prior_dataset_manifest_sha256": prior_dataset_manifest_sha256,
        "fresh_dataset_manifest_sha256": sha256_file(fresh_dataset / "manifest.json"),
        "prior_prompt_source": prior_source,
        "prior_prompt_count": len(prior),
        "fresh_prompt_count": len(fresh),
        "prior_unique_prompt_count": len(set(prior)),
        "fresh_unique_prompt_count": len(set(fresh)),
        "exact_prompt_overlap_count": 0,
        "prior_prompt_set_sha256": sha256_bytes(canonical_json(sorted(prior)).encode("utf-8")),
        "fresh_prompt_set_sha256": sha256_bytes(canonical_json(sorted(fresh)).encode("utf-8")),
        "contains_prompt_text": False,
        "contains_gold_labels": False,
        "interpretation_boundary": (
            "Zero byte-identical prompts prevents direct prompt reuse. The controlled factor "
            "ontology and most synthetic templates remain shared across realizations, so this is "
            "not evidence of naturalistic-domain generalization."
        ),
    }
    report["novelty_report_sha256"] = sha256_bytes(canonical_json(report).encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    prior = parser.add_mutually_exclusive_group(required=True)
    prior.add_argument("--prior-dataset", type=Path)
    prior.add_argument("--prior-prompt-manifest", type=Path)
    parser.add_argument("--fresh-dataset", type=Path, required=True)
    parser.add_argument("--arm", default="ledger_verifier")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(
        args.prior_dataset.resolve() if args.prior_dataset is not None else None,
        args.fresh_dataset.resolve(),
        args.arm,
        args.suffix,
        (args.prior_prompt_manifest.resolve() if args.prior_prompt_manifest is not None else None),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "prior_prompts": report["prior_prompt_count"],
                "fresh_prompts": report["fresh_prompt_count"],
                "overlap": report["exact_prompt_overlap_count"],
                "novelty_report_sha256": report["novelty_report_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
