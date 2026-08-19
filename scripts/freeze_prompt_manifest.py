#!/usr/bin/env python3
"""Freeze exact model-facing prompt hashes for every item and intervention arm.

The manifest contains hashes and identities, not prompt text. For a hidden split it should stay
private until the public commitment step; only its SHA-256 needs to be committed beforehand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl, validate_dataset  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.prompts import ARMS, render_prompt  # noqa: E402

Json = dict[str, Any]


def exact_model_prompt(rendered: str, control_instruction: str) -> str:
    """Mirror the byte construction used by scripts/run_llama_study.py."""

    return f"{rendered.rstrip()}\n\n{control_instruction}\n"


def build_manifest(dataset_dir: Path, decoding_path: Path) -> Json:
    validate_dataset(dataset_dir, ROOT)
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    decoding = load_json(decoding_path)
    policy_path = ROOT / "policies" / str(dataset_manifest["policy_file"])
    policy = load_policy(policy_path)
    evaluation_time = str(dataset_manifest["evaluation_time"])
    control = str(decoding["control_instruction"])
    items = load_jsonl(dataset_dir / "inputs.jsonl")

    prompt_records: list[Json] = []
    for item in sorted(items, key=lambda value: str(value["id"])):
        for arm in ARMS:
            rendered = render_prompt(
                item,
                arm,
                dataset_dir,
                policy=policy,
                evaluation_time=evaluation_time,
            )
            prompt = exact_model_prompt(rendered, control)
            prompt_records.append(
                {
                    "item_id": str(item["id"]),
                    "arm": arm,
                    "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                    "utf8_bytes": len(prompt.encode("utf-8")),
                }
            )

    identity: Json = {
        "manifest_version": "1.0.0",
        "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
        "policy_sha256": sha256_file(policy_path),
        "decoding_sha256": sha256_file(decoding_path),
        "renderer_sha256": sha256_file(ROOT / "src" / "claimpromotebench" / "prompts.py"),
        "runner_sha256": sha256_file(ROOT / "scripts" / "run_llama_study.py"),
        "control_instruction_sha256": sha256_bytes(control.encode("utf-8")),
        "item_count": len(items),
        "arms": list(ARMS),
        "prompt_count": len(prompt_records),
        "prompts": prompt_records,
    }
    identity["prompt_manifest_sha256"] = sha256_bytes(canonical_json(identity).encode("utf-8"))
    return identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--decoding", type=Path, default=ROOT / "configs" / "decoding-v1.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = build_manifest(args.dataset.resolve(), args.decoding.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "FROZEN",
                "items": result["item_count"],
                "prompts": result["prompt_count"],
                "prompt_manifest_sha256": result["prompt_manifest_sha256"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
