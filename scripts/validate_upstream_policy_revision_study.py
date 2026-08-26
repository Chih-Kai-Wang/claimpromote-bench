#!/usr/bin/env python3
"""Validate the frozen upstream-policy-revision dataset without model or network calls."""

from __future__ import annotations

import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from upstream_policy_revision import validate_decision_semantics  # noqa: E402

from claimpromotebench.dataset import load_jsonl, validate_with_schema  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "upstream-policy-revisions-v1"
SCHEMA_PATH = ROOT / "v2" / "schemas" / "upstream-policy-decision.schema.json"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")


def fail(message: str) -> None:
    raise ValueError(f"upstream-policy-revision-validation: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def diff_paths(left: Any, right: Any, pointer: str = "") -> set[str]:
    if type(left) is not type(right):
        return {pointer or "/"}
    if isinstance(left, dict):
        paths: set[str] = set()
        for key in sorted(set(left) | set(right)):
            child = f"{pointer}/{key}"
            if key not in left or key not in right:
                paths.add(child)
            else:
                paths.update(diff_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        paths = set()
        if len(left) != len(right):
            paths.add(f"{pointer}/length")
        for index, (left_value, right_value) in enumerate(zip(left, right, strict=False)):
            paths.update(diff_paths(left_value, right_value, f"{pointer}/{index}"))
        return paths
    return set() if left == right else {pointer or "/"}


def validate(root: Path = STUDY_ROOT) -> Json:
    manifest = load_object(root / "artifact-manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or len(files) != 8:
        fail("artifact manifest must bind eight generated files")
    for relative, expected in files.items():
        path = root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"generated artifact digest differs: {relative}")
    source_files = manifest.get("source_files")
    if not isinstance(source_files, dict) or len(source_files) != 4:
        fail("artifact manifest must bind four upstream source files")
    for relative, expected in source_files.items():
        path = ROOT / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"upstream source digest differs: {relative}")
    payload = {key: value for key, value in manifest.items() if key != "self_digest"}
    if manifest.get("self_digest") != sha256_bytes(canonical_json(payload).encode("utf-8")):
        fail("artifact manifest self digest differs")
    if manifest.get("response_schema_sha256") != sha256_file(SCHEMA_PATH):
        fail("response schema digest differs")

    items = load_jsonl(root / "dataset" / "evaluation-items.jsonl")
    gold = load_jsonl(root / "dataset" / "evaluation-gold.jsonl")
    pairs = json.loads((root / "dataset" / "evaluation-pairs.json").read_text(encoding="utf-8"))
    packet = load_object(root / "dataset" / "evaluation-prompt-packet.json")
    if len(items) != 24 or len(gold) != 24 or not isinstance(pairs, list) or len(pairs) != 12:
        fail("expected twenty-four items and twelve pairs")
    items_by_id = {str(row["id"]): row for row in items}
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(items_by_id) != 24 or set(items_by_id) != set(gold_by_id):
        fail("item and gold IDs must be unique and identical")
    transitions: Counter[str] = Counter()
    seen_members: set[str] = set()
    for row in gold:
        decision = row.get("decision")
        if not isinstance(decision, dict):
            fail(f"gold decision is malformed: {row.get('id')}")
        validate_with_schema(decision, SCHEMA_PATH, str(row["id"]))
        validate_decision_semantics(decision)
    for pair in pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        if len(member_ids) != 2 or len(set(member_ids)) != 2:
            fail(f"pair members are malformed: {pair.get('pair_id')}")
        if set(member_ids) & seen_members or not set(member_ids) <= set(items_by_id):
            fail(f"pair membership is repeated or unknown: {pair.get('pair_id')}")
        seen_members.update(member_ids)
        old_id = str(pair["old_id"])
        new_id = str(pair["new_id"])
        if {old_id, new_id} != set(member_ids):
            fail(f"old/new members differ from pair members: {pair.get('pair_id')}")
        left = deepcopy(items_by_id[old_id])
        right = deepcopy(items_by_id[new_id])
        for value in (left, right):
            value.pop("id")
        differences = diff_paths(left, right)
        allowed = set(str(value) for value in pair["controlled_json_pointers"])
        if differences != allowed:
            fail(
                f"{pair.get('pair_id')} changes {sorted(differences)} instead of {sorted(allowed)}"
            )
        old_action = str(gold_by_id[old_id]["decision"]["action"])
        new_action = str(gold_by_id[new_id]["decision"]["action"])
        transition = f"{old_action}->{new_action}"
        if transition != pair["action_transition"] or old_action == new_action:
            fail(f"action transition differs: {pair.get('pair_id')}")
        transitions[transition] += 1
    if seen_members != set(items_by_id):
        fail("every item must occur in exactly one pair")
    if transitions != Counter({"ALLOW->HOLD": 6, "HOLD->ALLOW": 6}):
        fail(f"action transitions are unbalanced: {dict(transitions)}")

    records = packet.get("records")
    if (
        not isinstance(records, list)
        or len(records) != 24
        or packet.get("contains_gold") is not False
    ):
        fail("prompt packet is malformed")
    packet_payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if packet.get("packet_sha256") != sha256_bytes(canonical_json(packet_payload).encode("utf-8")):
        fail("prompt packet digest differs")
    prompt_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            fail("prompt packet contains a malformed record")
        item_id = str(record["item_id"])
        prompt = str(record["prompt"])
        if item_id in prompt_ids or item_id not in items_by_id:
            fail(f"prompt packet item is repeated or unknown: {item_id}")
        prompt_ids.add(item_id)
        if record.get("prompt_sha256") != sha256_bytes(prompt.encode("utf-8")):
            fail(f"prompt digest differs: {item_id}")
        lowered = prompt.lower()
        if '"revision"' in lowered or '"decision"' in lowered or "gold" in lowered:
            fail(f"prompt contains scorer metadata: {item_id}")

    coverage = load_object(root / "coverage.json")
    minimum = load_object(root / "minimum-suite.json")
    plan = load_object(root / "dataset-plan.json")
    receipt = load_object(root / "source-validation-receipt.json")
    if (
        coverage.get("contexts_per_transition") != {"ALLOW->HOLD": 6, "HOLD->ALLOW": 6}
        or minimum.get("witness_pairs") != 2
        or minimum.get("coverage", {}).get("action_edges") != {"covered": 2, "total": 2}
        or minimum.get("coverage", {}).get("changed_rules") != {"covered": 2, "total": 2}
    ):
        fail("coverage or minimum-suite certificate differs")
    if (
        plan.get("status") != "DATASET_READY_FOR_PREINFERENCE_COMMIT"
        or plan.get("model_calls_before_freeze") != 0
        or plan.get("human_annotator_count") != 0
        or receipt.get("model_calls") != 0
        or receipt.get("credentials_retained") is not False
        or receipt.get("source_bytes_match_registry") is not True
    ):
        fail("preinference or provenance boundary differs")

    scanned_paths = [
        root / "dataset" / "evaluation-items.jsonl",
        root / "dataset" / "evaluation-prompt-packet.json",
        root / "coverage.json",
        root / "dataset-plan.json",
        root / "minimum-suite.json",
        root / "source-validation-receipt.json",
        SCHEMA_PATH,
    ]
    for path in scanned_paths:
        text = path.read_text(encoding="utf-8")
        for marker in ACCOUNT_MARKERS:
            if marker.lower() in text.lower():
                fail(f"account marker in model/release-facing artifact: {path}: {marker}")
    return {
        "items": len(items),
        "pairs": len(pairs),
        "migrations": int(plan["external_revision_count"]),
        "transitions": dict(sorted(transitions.items())),
        "minimum_pairs": int(minimum["witness_pairs"]),
    }


def main() -> int:
    report = validate()
    print(
        "upstream-policy-revision-validation: "
        f"pairs={report['pairs']} items={report['items']} "
        f"migrations={report['migrations']} minimum={report['minimum_pairs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
