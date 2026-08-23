#!/usr/bin/env python3
"""Validate the SLSA-derived portability freeze without model credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_slsa_portability_study import FACTORS, changed_paths, public_contract  # noqa: E402
from slsa_policy import evaluate_slsa, load_slsa_policy  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

DEFAULT_ROOT = ROOT / "v2" / "slsa-portability-v1" / "dataset"
POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"
SOURCE_REGISTRY = ROOT / "v2" / "slsa-portability-v1" / "source-registry.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"slsa-portability-validate: {message}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path}: {exc}")


def load_jsonl(path: Path) -> list[Json]:
    rows: list[Json] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{path}:{line_number}: {exc}")
        if not isinstance(value, dict):
            fail(f"{path}:{line_number}: row is not an object")
        rows.append(value)
    return rows


def verify_sources(registry: Json) -> None:
    for source in registry["sources"]:
        expected = source.get("sha256")
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            fail(f"invalid source hash for {source.get('source_id')}")
        repository = str(source["repository"])
        commit = str(source["commit"])
        path = str(source["path"])
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"
        request = urllib.request.Request(
            url, headers={"User-Agent": "ClaimPromoteBench-SLSA-Source-Audit/1"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            actual = "sha256:" + hashlib.sha256(response.read()).hexdigest()
        if actual != expected:
            fail(f"pinned source bytes differ for {source['source_id']}")


def validate_dataset(dataset_root: Path, *, verify_upstream: bool) -> Json:
    policy = load_slsa_policy(POLICY_PATH)
    registry = load_json(SOURCE_REGISTRY)
    manifest = load_json(dataset_root / "manifest.json")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    if not isinstance(registry, dict) or registry.get("status") != "PINNED_PRIMARY_SOURCES":
        fail("source registry is not pinned")
    if verify_upstream:
        verify_sources(registry)
    if (
        not isinstance(manifest, dict)
        or manifest.get("status") != "SYNTHETIC_POLICY_PORTABILITY_DATASET"
    ):
        fail("manifest status is invalid")
    if manifest.get("policy_sha256") != sha256_file(POLICY_PATH):
        fail("manifest policy hash differs")
    if manifest.get("source_registry_sha256") != sha256_file(SOURCE_REGISTRY):
        fail("manifest source-registry hash differs")
    if manifest.get("decision_schema_sha256") != sha256_file(DECISION_SCHEMA):
        fail("manifest decision-schema hash differs")

    loaded: dict[str, list[Json]] = {}
    for split in ("development", "evaluation"):
        loaded[f"{split}_items"] = load_jsonl(dataset_root / f"{split}-items.jsonl")
        loaded[f"{split}_gold"] = load_jsonl(dataset_root / f"{split}-gold.jsonl")
        pairs = load_json(dataset_root / f"{split}-pairs.json")
        if not isinstance(pairs, list) or not all(isinstance(value, dict) for value in pairs):
            fail(f"{split} pairs must be a list of objects")
        loaded[f"{split}_pairs"] = pairs

    for name, expected in manifest["data_file_sha256"].items():
        if sha256_file(dataset_root / name) != expected:
            fail(f"data-file hash differs: {name}")
    fingerprint = sha256_bytes(
        canonical_json(
            {
                "policy_sha256": sha256_file(POLICY_PATH),
                "source_registry_sha256": sha256_file(SOURCE_REGISTRY),
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "data_file_sha256": manifest["data_file_sha256"],
            }
        ).encode("utf-8")
    )
    if fingerprint != manifest.get("dataset_fingerprint"):
        fail("dataset fingerprint differs")
    if packet.get("dataset_fingerprint") != fingerprint:
        fail("prompt packet is not bound to the dataset fingerprint")
    if packet.get("packet_sha256") != sha256_bytes(
        canonical_json(
            {key: value for key, value in packet.items() if key != "packet_sha256"}
        ).encode("utf-8")
    ):
        fail("packet content hash differs")
    if manifest.get("packet_sha256") != packet.get("packet_sha256"):
        fail("manifest packet hash differs")
    if manifest.get("packet_file_sha256") != sha256_file(
        dataset_root / "evaluation-prompt-packet.json"
    ):
        fail("manifest packet file hash differs")

    factor_ids = {factor.factor_id for factor in FACTORS}
    summaries: Json = {}
    for split, expected_pairs, expected_items, expected_actions in (
        ("development", 36, 72, Counter({"ALLOW": 36, "HOLD": 12, "DEMOTE": 12, "ESCALATE": 12})),
        ("evaluation", 60, 120, Counter({"ALLOW": 60, "HOLD": 20, "DEMOTE": 20, "ESCALATE": 20})),
    ):
        items = loaded[f"{split}_items"]
        gold = loaded[f"{split}_gold"]
        pairs = loaded[f"{split}_pairs"]
        if (
            len(items) != expected_items
            or len(gold) != expected_items
            or len(pairs) != expected_pairs
        ):
            fail(f"{split} count differs from the frozen design")
        item_by_id = {str(row["id"]): row for row in items}
        gold_by_id = {str(row["id"]): row for row in gold}
        if len(item_by_id) != len(items) or set(item_by_id) != set(gold_by_id):
            fail(f"{split} contains duplicate or mismatched item IDs")
        actions: Counter[str] = Counter()
        observed_factors: Counter[str] = Counter()
        for item_id, item in item_by_id.items():
            actual = evaluate_slsa(item["model_visible"], policy)
            expected = gold_by_id[item_id]["decision"]
            if actual != expected:
                fail(f"oracle/gold mismatch for {item_id}")
            actions[str(actual["action"])] += 1
            observed_factors[str(gold_by_id[item_id]["factor_id"])] += 1
        if actions != expected_actions:
            fail(f"{split} action distribution differs: {actions}")
        if set(observed_factors) != factor_ids:
            fail(f"{split} factor coverage differs")
        for pair in pairs:
            member_ids = [str(value) for value in pair["member_ids"]]
            if len(member_ids) != 2 or len(set(member_ids)) != 2:
                fail(f"invalid pair membership: {pair.get('pair_id')}")
            members = [item_by_id[item_id]["model_visible"] for item_id in member_ids]
            paths = changed_paths(members[0], members[1])
            if paths != [pair["controlled_path"]]:
                fail(f"pair isolation differs for {pair['pair_id']}: {paths}")
            pair_actions = [
                str(gold_by_id[item_id]["decision"]["action"]) for item_id in member_ids
            ]
            if pair_actions != pair["expected_actions"] or Counter(pair_actions)["ALLOW"] != 1:
                fail(f"pair action contract differs for {pair['pair_id']}")
        summaries[split] = {
            "items": len(items),
            "pairs": len(pairs),
            "factors": len(observed_factors),
            "action_counts": dict(sorted(actions.items())),
        }

    eval_items = {str(row["id"]): row for row in loaded["evaluation_items"]}
    packet_records = packet.get("records")
    if not isinstance(packet_records, list) or len(packet_records) != 120:
        fail("evaluation packet must contain 120 records")
    for record in packet_records:
        item_id = str(record["item_id"])
        if item_id not in eval_items:
            fail(f"packet contains an unknown item: {item_id}")
        prompt = record.get("prompt")
        if not isinstance(prompt, str) or record.get("prompt_sha256") != sha256_bytes(
            prompt.encode("utf-8")
        ):
            fail(f"packet prompt hash differs for {item_id}")
        if item_id in prompt or str(record["pair_id"]) in prompt or "factor_id" in prompt:
            fail(f"packet leaks evaluation metadata for {item_id}")
        if canonical_json(public_contract(policy)) not in prompt:
            fail(f"packet omits the complete public policy for {item_id}")

    return {
        "status": "SLSA_PORTABILITY_FREEZE_VALID",
        "credentials_loaded": False,
        "upstream_sources_verified": verify_upstream,
        "dataset_fingerprint": fingerprint,
        "policy_count_added": 1,
        **summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--verify-upstream", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = validate_dataset(args.dataset_root.resolve(), verify_upstream=args.verify_upstream)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
