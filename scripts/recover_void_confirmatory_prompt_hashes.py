#!/usr/bin/env python3
"""Recover only prompt hashes from a void, zero-POST confirmatory realization."""

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

from build_prior_prompt_hash_denylist import validate_denylist  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _self_digest(value: Json, field: str) -> str:
    payload = dict(value)
    observed = payload.pop(field, None)
    expected = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if observed != expected:
        raise ValueError(f"self-digest mismatch: {field}")
    return expected


def recover(
    *,
    base_path: Path,
    packet_path: Path,
    commitment_path: Path,
    c1_run_receipt_path: Path,
    recovery_run_id: int,
) -> tuple[Json, Json]:
    base = _load(base_path)
    validate_denylist(base)
    packet = _load(packet_path)
    commitment = _load(commitment_path)
    c1_run = _load(c1_run_receipt_path)

    packet_sha = _self_digest(packet, "packet_sha256")
    commitment_sha = _self_digest(commitment, "commitment_sha256")
    expected_packet_sha = commitment.get("c1_receipt", {}).get("packet_sha256")
    if packet_sha != expected_packet_sha:
        raise ValueError("reconstructed packet differs from the frozen r5 C1 identity")
    if packet.get("dataset_manifest_sha256") != commitment.get("dataset_manifest_sha256"):
        raise ValueError("reconstructed dataset differs from the frozen r5 C1 identity")
    if commitment_sha != c1_run.get("commitment_sha256"):
        raise ValueError("archived r5 C1 run receipt names a different commitment")
    if (
        c1_run.get("model_post_intents") != 0
        or c1_run.get("model_calls") != 0
        or c1_run.get("cost_usd") != 0.0
    ):
        raise ValueError("r5 recovery is permitted only for the sealed zero-POST realization")

    records = packet.get("records")
    if not isinstance(records, list) or len(records) != 300:
        raise ValueError("reconstructed r5 packet must contain exactly 300 records")
    added = sorted(str(record.get("prompt_sha256", "")) for record in records)
    if (
        len(set(added)) != 300
        or any(not _DIGEST.fullmatch(value) for value in added)
        or set(base["prompt_sha256"]) & set(added)
    ):
        raise ValueError("reconstructed r5 prompt hashes are malformed or overlap prior prompts")
    added_set_sha = sha256_bytes(canonical_json(added).encode("utf-8"))
    if added_set_sha != commitment.get("prompt_novelty_audit", {}).get("fresh_prompt_set_sha256"):
        raise ValueError("reconstructed r5 prompt-hash set differs from its C1 commitment")

    hashes = sorted([str(value) for value in base["prompt_sha256"]] + added)
    manifests = sorted(
        {
            *[
                str(value)
                for value in base.get(
                    "dataset_manifest_sha256_members",
                    [base.get("dataset_manifest_sha256")],
                )
            ],
            str(packet["dataset_manifest_sha256"]),
        }
    )
    if any(not _DIGEST.fullmatch(value) for value in manifests):
        raise ValueError("a source dataset-manifest digest is malformed")

    denylist: Json = {
        "schema_version": "1.2.0",
        "status": "FROZEN_PRIOR_PROMPT_HASH_DENYLIST",
        "source": {
            "kind": "UNION_WITH_VOID_ZERO_POST_RECOVERY",
            "base": {
                "file_sha256": sha256_file(base_path),
                "denylist_sha256": base["denylist_sha256"],
                "prompt_hash_set_sha256": base["prompt_hash_set_sha256"],
            },
            "recovered_member": {
                "kind": "VOID_PRE_POST_RECOVERED_PROMPT_HASH_SET",
                "study_id": commitment["study_id"],
                "source_commit": commitment["source_commit"],
                "c1_github_run_id": c1_run["github_run_id"],
                "recovery_github_run_id": recovery_run_id,
                "commitment_sha256": commitment_sha,
                "packet_sha256": packet_sha,
                "fresh_prompt_hash_set_sha256": added_set_sha,
                "model_post_intents": 0,
                "model_calls": 0,
            },
        },
        "dataset_manifest_sha256": sha256_bytes(canonical_json(manifests).encode("utf-8")),
        "dataset_manifest_sha256_members": manifests,
        "prompt_arm": packet["prompt_arm"],
        "provider_neutral_control_suffix": "",
        "prompt_count": len(hashes),
        "unique_prompt_count": len(set(hashes)),
        "prompt_sha256": hashes,
        "prompt_hash_set_sha256": sha256_bytes(canonical_json(hashes).encode("utf-8")),
        "contains_item_ids": False,
        "contains_prompt_text": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "interpretation_boundary": (
            "The union proves only byte-identical prompt non-reuse. The recovered r5 member "
            "was reconstructed solely to freeze hashes after r5 was voided before any model "
            "POST; no prompt text, item ID, hidden row, or gold label is released."
        ),
    }
    denylist["denylist_sha256"] = sha256_bytes(canonical_json(denylist).encode("utf-8"))
    validate_denylist(denylist)

    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "VOID_R5_PROMPT_HASH_RECOVERY_VERIFIED",
        "study_id": commitment["study_id"],
        "recovery_github_run_id": recovery_run_id,
        "c1_github_run_id": c1_run["github_run_id"],
        "source_commit": commitment["source_commit"],
        "commitment_sha256": commitment_sha,
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "packet_sha256": packet_sha,
        "recovered_prompt_count": len(added),
        "recovered_prompt_hash_set_sha256": added_set_sha,
        "combined_prompt_count": len(hashes),
        "combined_prompt_hash_set_sha256": denylist["prompt_hash_set_sha256"],
        "combined_denylist_sha256": denylist["denylist_sha256"],
        "combined_denylist_file_sha256": None,
        "application_post_count": 0,
        "client_retry_count": 0,
        "model_inference_evidence": "NONE",
        "contains_item_ids": False,
        "contains_prompt_text": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "contains_private_salt_bytes": False,
        "contains_derived_seed_bytes": False,
    }
    return denylist, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-denylist", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--c1-run-receipt", type=Path, required=True)
    parser.add_argument("--recovery-run-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    denylist, receipt = recover(
        base_path=args.base_denylist.resolve(),
        packet_path=args.packet.resolve(),
        commitment_path=args.commitment.resolve(),
        c1_run_receipt_path=args.c1_run_receipt.resolve(),
        recovery_run_id=args.recovery_run_id,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(denylist, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    receipt["combined_denylist_file_sha256"] = sha256_file(args.out)
    receipt["recovery_receipt_sha256"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "recovered_prompt_count": receipt["recovered_prompt_count"],
                "combined_prompt_count": receipt["combined_prompt_count"],
                "combined_denylist_sha256": receipt["combined_denylist_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
