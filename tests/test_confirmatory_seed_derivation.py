"""Tests for future-beacon hidden seed derivation."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.hashing import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_is_bound_to_salt_preregistration_round_and_verified_randomness(
    tmp_path: Path,
) -> None:
    derivation = _load_script("derive_confirmatory_seed")
    salt = bytes(range(32))
    salt_path = tmp_path / "salt.bin"
    salt_path.write_bytes(salt)
    preregistration = "11" * 32
    randomness = "22" * 32
    round_number = 123456
    config = {
        "private_salt_sha256": sha256_bytes(salt),
        "preregistration_sha256": f"sha256:{preregistration}",
        "drand": {
            "chain_hash": "33" * 32,
            "public_key": "44" * 96,
            "scheme_id": "bls-unchained-g1-rfc9380",
            "round": round_number,
        },
    }
    beacon = {
        "status": "CRYPTOGRAPHICALLY_VERIFIED_MULTI_RELAY_AGREEMENT",
        "chain_hash": config["drand"]["chain_hash"],
        "public_key": config["drand"]["public_key"],
        "scheme_id": config["drand"]["scheme_id"],
        "round": round_number,
        "randomness": randomness,
        "signature": "55" * 48,
        "agreeing_relays": 3,
        "verification": {"library": "drand-client", "version": "1.4.2"},
    }
    config_path = tmp_path / "commitment.json"
    beacon_path = tmp_path / "beacon.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    beacon_path.write_text(json.dumps(beacon), encoding="utf-8")

    seed, receipt = derivation.derive(salt_path, config_path, beacon_path)
    message = (
        b"CPB-CONFIRMATORY-V1\0"
        + bytes.fromhex(preregistration)
        + round_number.to_bytes(8, "big")
        + bytes.fromhex(randomness)
    )
    assert seed == hmac.new(salt, message, hashlib.sha256).digest()
    assert receipt["derived_seed_sha256"] == sha256_bytes(seed)
    assert receipt["contains_private_salt_bytes"] is False
    assert receipt["rejection_sampling_permitted"] is False

    wrong_salt = tmp_path / "wrong-salt.bin"
    wrong_salt.write_bytes(b"x" * 32)
    with pytest.raises(ValueError, match="public C0 commitment"):
        derivation.derive(wrong_salt, config_path, beacon_path)
