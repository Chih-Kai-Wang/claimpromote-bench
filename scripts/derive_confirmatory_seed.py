#!/usr/bin/env python3
"""Derive one hidden seed from a precommitted salt and future verified drand beacon."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN = b"CPB-CONFIRMATORY-V1\0"


def _salt(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) == 32:
        return raw
    stripped = raw.strip()
    if re.fullmatch(rb"[0-9a-fA-F]{64}", stripped):
        return bytes.fromhex(stripped.decode("ascii"))
    raise ValueError("private salt must be exactly 32 raw bytes or 64 hexadecimal digits")


def derive(salt_path: Path, config_path: Path, beacon_path: Path) -> tuple[bytes, Json]:
    salt = _salt(salt_path)
    config = load_json(config_path)
    beacon = load_json(beacon_path)
    salt_sha = sha256_bytes(salt)
    if config.get("private_salt_sha256") != salt_sha:
        raise ValueError("private salt differs from the public C0 commitment")
    preregistration = str(config.get("preregistration_sha256", "")).removeprefix("sha256:")
    if not _HEX64.fullmatch(preregistration):
        raise ValueError("C0 preregistration digest is malformed")
    drand = config.get("drand")
    if not isinstance(drand, dict):
        raise ValueError("drand C0 commitment is malformed")
    if beacon.get("status") != "CRYPTOGRAPHICALLY_VERIFIED_MULTI_RELAY_AGREEMENT":
        raise ValueError("drand beacon lacks cryptographic multi-relay verification")
    for config_key, beacon_key in (
        ("chain_hash", "chain_hash"),
        ("public_key", "public_key"),
        ("scheme_id", "scheme_id"),
        ("round", "round"),
    ):
        if beacon.get(beacon_key) != drand.get(config_key):
            raise ValueError(f"verified beacon differs from C0 commitment: {config_key}")
    randomness = str(beacon.get("randomness", ""))
    signature = str(beacon.get("signature", ""))
    if not _HEX64.fullmatch(randomness) or not re.fullmatch(r"[0-9a-f]+", signature):
        raise ValueError("verified beacon payload is malformed")
    round_number = int(drand["round"])
    message = (
        _DOMAIN
        + bytes.fromhex(preregistration)
        + round_number.to_bytes(8, "big")
        + bytes.fromhex(randomness)
    )
    seed = hmac.new(salt, message, hashlib.sha256).digest()
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "SINGLE_PRECOMMITTED_SEED_DERIVED",
        "derivation": (
            "HMAC-SHA256(key=private_salt, msg=CPB-CONFIRMATORY-V1\\0 || "
            "preregistration_sha256_bytes || drand_round_u64_be || drand_randomness_bytes)"
        ),
        "private_salt_sha256": salt_sha,
        "preregistration_sha256": f"sha256:{preregistration}",
        "seed_commitment_file_sha256": sha256_file(config_path),
        "verified_beacon_file_sha256": sha256_file(beacon_path),
        "drand": {
            "chain_hash": drand["chain_hash"],
            "round": round_number,
            "randomness": randomness,
            "signature": signature,
            "agreeing_relays": beacon["agreeing_relays"],
            "verification": beacon["verification"],
        },
        "derived_seed_sha256": sha256_bytes(seed),
        "contains_private_salt_bytes": False,
        "contains_derived_seed_bytes": False,
        "alternate_salt_seed_or_round_permitted": False,
        "rejection_sampling_permitted": False,
    }
    receipt["seed_derivation_receipt_sha256"] = sha256_bytes(
        canonical_json(receipt).encode("utf-8")
    )
    return seed, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--verified-beacon", type=Path, required=True)
    parser.add_argument("--seed-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    seed, receipt = derive(
        args.salt_file.resolve(),
        args.commitment.resolve(),
        args.verified_beacon.resolve(),
    )
    args.seed_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.seed_out.write_text(seed.hex(), encoding="ascii")
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "derived_seed_sha256": receipt["derived_seed_sha256"],
                "drand_round": receipt["drand"]["round"],
                "receipt_sha256": receipt["seed_derivation_receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
