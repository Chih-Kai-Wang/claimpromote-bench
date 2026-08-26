#!/usr/bin/env python3
"""Train and freeze the shallow baseline on the already-public dev split only."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.confirmatory_baseline import ACTIONS, prompt_features  # noqa: E402
from claimpromotebench.dataset import load_json, load_jsonl, validate_dataset  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.prompts import render_prompt  # noqa: E402

Json = dict[str, Any]


def build_model(
    public_dev: Path,
    expected_manifest_sha256: str,
    arm: str,
    suffix: str,
) -> Json:
    validate_dataset(public_dev, ROOT)
    observed_manifest = sha256_file(public_dev / "manifest.json")
    if observed_manifest != expected_manifest_sha256:
        raise ValueError("public-dev manifest differs from the frozen training set")
    manifest = load_json(public_dev / "manifest.json")
    policy = load_policy(ROOT / "policies" / str(manifest["policy_file"]))
    prompts: dict[str, str] = {}
    for item in load_jsonl(public_dev / "inputs.jsonl"):
        rendered = render_prompt(
            item,
            arm,
            public_dev,
            policy=policy,
            evaluation_time=str(manifest["evaluation_time"]),
        )
        prompts[str(item["id"])] = (
            f"{rendered.rstrip()}\n{suffix}" if suffix else f"{rendered.rstrip()}\n"
        )
    gold = {
        str(row["id"]): str(row["decision"]["action"])
        for row in load_jsonl(public_dev / "gold.jsonl")
    }
    if set(prompts) != set(gold):
        raise ValueError("public-dev prompt/gold coverage mismatch")
    document_counts = Counter(gold.values())
    if set(document_counts) != set(ACTIONS):
        raise ValueError("public-dev training set does not cover all registered actions")
    token_counts = {action: Counter() for action in ACTIONS}
    vocabulary: set[str] = set()
    for item_id in sorted(prompts):
        features = prompt_features(prompts[item_id])
        token_counts[gold[item_id]].update(features)
        vocabulary.update(features)
    report: Json = {
        "schema_version": "1.0.0",
        "model_id": "public-dev-text-multinomial-nb-v1",
        "actions": list(ACTIONS),
        "action_tie_break_order": list(ACTIONS),
        "alpha": 1.0,
        "documents": len(prompts),
        "document_counts": {action: document_counts[action] for action in ACTIONS},
        "token_counts": {action: dict(sorted(token_counts[action].items())) for action in ACTIONS},
        "token_totals": {action: sum(token_counts[action].values()) for action in ACTIONS},
        "vocabulary": sorted(vocabulary),
        "training": {
            "public_dev_manifest_sha256": observed_manifest,
            "prompt_arm": arm,
            "provider_neutral_control_suffix": suffix,
            "instances": len(prompts),
            "reads_only_public_dev": True,
            "hidden_rows_seen": 0,
            "hidden_gold_seen": 0,
        },
        "implementation_sha256": {
            "training_script": sha256_file(Path(__file__)),
            "feature_and_inference_module": sha256_file(
                ROOT / "src" / "claimpromotebench" / "confirmatory_baseline.py"
            ),
        },
    }
    report["model_sha256"] = sha256_bytes(canonical_json(report).encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-dev", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--arm", default="ledger_verifier")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_model(
        args.public_dev.resolve(),
        args.expected_manifest_sha256,
        args.arm,
        args.suffix,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PUBLIC_ONLY_SHALLOW_MODEL_FROZEN",
                "documents": report["documents"],
                "features": len(report["vocabulary"]),
                "model_sha256": report["model_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
