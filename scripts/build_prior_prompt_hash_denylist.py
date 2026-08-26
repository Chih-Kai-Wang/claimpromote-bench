#!/usr/bin/env python3
"""Build or validate a public-safe denylist of prior model-facing prompt hashes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def validate_denylist(value: Json) -> None:
    if value.get("status") != "FROZEN_PRIOR_PROMPT_HASH_DENYLIST":
        raise ValueError("prior prompt denylist status is invalid")
    hashes = value.get("prompt_sha256")
    if (
        not isinstance(hashes, list)
        or len(hashes) < 300
        or len(hashes) % 300 != 0
        or len(set(hashes)) != len(hashes)
        or any(not isinstance(digest, str) or not _DIGEST.fullmatch(digest) for digest in hashes)
    ):
        raise ValueError(
            "prior prompt denylist must contain complete 300-prompt realizations "
            "with unique SHA-256 values"
        )
    if value.get("prompt_count") != len(hashes) or value.get("unique_prompt_count") != len(hashes):
        raise ValueError("prior prompt denylist declared counts do not match its hashes")
    if hashes != sorted(hashes):
        raise ValueError("prior prompt denylist hashes are not canonically sorted")
    if (
        value.get("contains_prompt_text") is not False
        or value.get("contains_gold_labels") is not False
    ):
        raise ValueError("prior prompt denylist crosses a private-content boundary")
    payload = dict(value)
    observed = payload.pop("denylist_sha256", None)
    expected = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if observed != expected:
        raise ValueError("prior prompt denylist self-digest mismatch")
    expected_set = sha256_bytes(canonical_json(hashes).encode("utf-8"))
    if value.get("prompt_hash_set_sha256") != expected_set:
        raise ValueError("prior prompt denylist set digest mismatch")


def build(packet_path: Path, expected_source_sha256: str) -> Json:
    if sha256_file(packet_path) != expected_source_sha256:
        raise ValueError("released prior prompt packet differs from the registered source digest")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    records = packet.get("records")
    if not isinstance(records, list) or len(records) != 300:
        raise ValueError("released prior prompt packet does not contain 300 records")
    hashes = sorted(str(row.get("prompt_sha256", "")) for row in records)
    value: Json = {
        "schema_version": "1.0.0",
        "status": "FROZEN_PRIOR_PROMPT_HASH_DENYLIST",
        "source": {
            "reviewer_evidence_run": 32421292779,
            "prompt_packet_sha256": expected_source_sha256,
            "packet_sha256": str(packet.get("packet_sha256")),
        },
        "dataset_manifest_sha256": str(packet.get("dataset_manifest_sha256")),
        "prompt_arm": str(packet.get("prompt_arm")),
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
            "The denylist proves only byte-identical prompt non-reuse. It does not establish "
            "semantic-template, ontology, or naturalistic-domain novelty."
        ),
    }
    value["denylist_sha256"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    validate_denylist(value)
    return value


def extend(
    base_path: Path,
    packet_path: Path,
    expected_source_sha256: str,
    source_run_id: int,
) -> Json:
    """Union a frozen denylist with one additional released 300-prompt packet."""

    base = json.loads(base_path.read_text(encoding="utf-8"))
    validate_denylist(base)
    if sha256_file(packet_path) != expected_source_sha256:
        raise ValueError("additional prompt packet differs from the registered source digest")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if (
        packet.get("prompt_arm") != base.get("prompt_arm")
        or base.get("provider_neutral_control_suffix") != ""
    ):
        raise ValueError("additional prompt packet uses a different prompt configuration")
    records = packet.get("records")
    if not isinstance(records, list) or len(records) != 300:
        raise ValueError("additional prompt packet does not contain 300 records")
    added = sorted(str(row.get("prompt_sha256", "")) for row in records)
    if (
        len(set(added)) != 300
        or any(not _DIGEST.fullmatch(digest) for digest in added)
        or set(base["prompt_sha256"]) & set(added)
    ):
        raise ValueError("additional prompt packet is malformed or overlaps the base denylist")
    hashes = sorted([str(value) for value in base["prompt_sha256"]] + added)
    manifests = sorted(
        set(
            [
                str(value)
                for value in base.get(
                    "dataset_manifest_sha256_members",
                    [base.get("dataset_manifest_sha256")],
                )
            ]
            + [str(packet.get("dataset_manifest_sha256"))]
        )
    )
    if any(not _DIGEST.fullmatch(value) for value in manifests):
        raise ValueError("a source dataset-manifest digest is malformed")
    value: Json = {
        "schema_version": "1.1.0",
        "status": "FROZEN_PRIOR_PROMPT_HASH_DENYLIST",
        "source": {
            "kind": "UNION_OF_RELEASED_PROMPT_HASH_SETS",
            "members": [
                {
                    "kind": "frozen_denylist",
                    "file_sha256": sha256_file(base_path),
                    "denylist_sha256": str(base["denylist_sha256"]),
                    "prompt_hash_set_sha256": str(base["prompt_hash_set_sha256"]),
                },
                {
                    "kind": "released_prompt_packet",
                    "reviewer_evidence_run": source_run_id,
                    "file_sha256": expected_source_sha256,
                    "packet_sha256": str(packet.get("packet_sha256")),
                    "study_id": str(packet.get("study_id")),
                },
            ],
        },
        "dataset_manifest_sha256": sha256_bytes(canonical_json(manifests).encode("utf-8")),
        "dataset_manifest_sha256_members": manifests,
        "prompt_arm": str(packet.get("prompt_arm")),
        "provider_neutral_control_suffix": "",
        "prompt_count": len(hashes),
        "unique_prompt_count": len(hashes),
        "prompt_sha256": hashes,
        "prompt_hash_set_sha256": sha256_bytes(canonical_json(hashes).encode("utf-8")),
        "contains_item_ids": False,
        "contains_prompt_text": False,
        "contains_hidden_rows": False,
        "contains_gold_labels": False,
        "interpretation_boundary": (
            "The union denylist proves only byte-identical prompt non-reuse across every "
            "released hidden realization. It does not establish semantic-template, ontology, "
            "or naturalistic-domain novelty."
        ),
    }
    value["denylist_sha256"] = sha256_bytes(canonical_json(value).encode("utf-8"))
    validate_denylist(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source-packet", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--base-denylist", type=Path)
    parser.add_argument("--source-run-id", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.verify is not None:
        value = json.loads(args.verify.read_text(encoding="utf-8"))
        validate_denylist(value)
        print(
            json.dumps(
                {
                    "status": "PRIOR_PROMPT_DENYLIST_PASS",
                    "prompts": value["prompt_count"],
                    "denylist_sha256": value["denylist_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    if args.out is None or not args.expected_source_sha256:
        raise SystemExit("--source-packet requires --expected-source-sha256 and --out")
    if args.base_denylist is not None:
        if args.source_run_id is None:
            raise SystemExit("--base-denylist requires --source-run-id")
        value = extend(
            args.base_denylist.resolve(),
            args.source_packet.resolve(),
            str(args.expected_source_sha256),
            args.source_run_id,
        )
    else:
        value = build(args.source_packet.resolve(), str(args.expected_source_sha256))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": value["status"],
                "prompts": value["prompt_count"],
                "denylist_sha256": value["denylist_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
