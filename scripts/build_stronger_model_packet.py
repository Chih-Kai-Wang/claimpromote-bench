#!/usr/bin/env python3
"""Build the frozen, provider-neutral prompt packet for the stronger-model follow-up."""

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
from claimpromotebench.prompts import render_prompt  # noqa: E402

Json = dict[str, Any]
DEFAULT_PLAN = ROOT / "v2" / "stronger-model-study-plan.json"


def fail(message: str) -> None:
    raise SystemExit(f"stronger-model-packet: {message}")


def select_pilot_pairs(pairs: list[Json]) -> list[Json]:
    """Select the lexicographically first pair in each family, without model outputs."""

    by_family: dict[str, list[Json]] = {}
    for pair in pairs:
        by_family.setdefault(str(pair["family"]), []).append(pair)
    return [
        sorted(by_family[family], key=lambda row: str(row["pair_id"]))[0]
        for family in sorted(by_family)
    ]


def _expected(plan: Json, section: str, key: str) -> str:
    value = plan.get(section, {}).get(key)
    if not isinstance(value, str):
        fail(f"plan.{section}.{key} is missing")
    return value


def build_packet(dataset_dir: Path, plan_path: Path) -> Json:
    plan = load_json(plan_path)
    if not isinstance(plan, dict):
        fail("study plan must be an object")
    validate_dataset(dataset_dir, ROOT)
    observed_dataset_manifest = sha256_file(dataset_dir / "manifest.json")
    expected_dataset_manifest = plan.get("dataset", {}).get("dataset_manifest_sha256")
    c1_dataset_binding = plan.get("design", {}).get("dataset_manifest_bound_at_c1", False)
    if isinstance(expected_dataset_manifest, str):
        if observed_dataset_manifest != expected_dataset_manifest:
            fail("rebuilt dataset manifest differs from the study plan")
    elif expected_dataset_manifest is not None or c1_dataset_binding is not True:
        fail("study plan lacks either a dataset digest or the registered C1 binding")
    if sha256_file(ROOT / "configs" / "v1-benchmark-plan.json") != _expected(
        plan, "dataset", "benchmark_plan_sha256"
    ):
        fail("benchmark construction plan differs from the study plan")
    if sha256_file(ROOT / "src" / "claimpromotebench" / "prompts.py") != _expected(
        plan, "prompt", "renderer_sha256"
    ):
        fail("prompt renderer differs from the study plan")
    if sha256_file(ROOT / "schemas" / "agent-decision.schema.json") != _expected(
        plan, "prompt", "decision_schema_sha256"
    ):
        fail("decision schema differs from the study plan")

    manifest = load_json(dataset_dir / "manifest.json")
    policy_path = ROOT / "policies" / str(manifest["policy_file"])
    if sha256_file(policy_path) != _expected(plan, "prompt", "policy_sha256"):
        fail("policy differs from the study plan")
    policy = load_policy(policy_path)
    evaluation_time = str(manifest["evaluation_time"])
    prompt_arm = str(plan["prompt"]["arm"])
    suffix = str(plan["prompt"]["provider_neutral_control_suffix"])
    confirmatory_packet = plan.get("design", {}).get("confirmatory_inference_packet", False)
    if not isinstance(confirmatory_packet, bool):
        fail("plan.design.confirmatory_inference_packet must be Boolean")

    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        fail("pairs.json must contain a list")
    full_requires_pilot = plan.get("design", {}).get("full_requires_pilot", True)
    if not isinstance(full_requires_pilot, bool):
        fail("plan.design.full_requires_pilot must be Boolean")
    selected = select_pilot_pairs(pairs) if full_requires_pilot else []
    selected_pair_ids = [str(pair["pair_id"]) for pair in selected]
    expected_pair_ids = [str(value) for value in plan["pilot"]["pairs"]]
    if selected_pair_ids != expected_pair_ids:
        fail(
            "deterministic pilot selection differs from the study plan: "
            f"{selected_pair_ids} != {expected_pair_ids}"
        )
    pair_by_member: dict[str, Json] = {}
    for pair in pairs:
        for member_id in pair["member_ids"]:
            pair_by_member[str(member_id)] = pair

    records: list[Json] = []
    for item in sorted(load_jsonl(dataset_dir / "inputs.jsonl"), key=lambda row: str(row["id"])):
        item_id = str(item["id"])
        pair = pair_by_member.get(item_id)
        if pair is None:
            fail(f"item is missing from pairs.json: {item_id}")
        rendered = render_prompt(
            item,
            prompt_arm,
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        )
        prompt = f"{rendered.rstrip()}\n{suffix}" if suffix else f"{rendered.rstrip()}\n"
        record: Json = {
            "item_id": item_id,
            "pair_id": str(pair["pair_id"]),
            "family": str(pair["family"]),
            "factor_id": str(pair["factor_id"]),
            "prompt": prompt,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "utf8_bytes": len(prompt.encode("utf-8")),
        }
        if confirmatory_packet:
            template_id = pair.get("template_id")
            if not isinstance(template_id, str) or not template_id:
                fail(f"confirmatory pair lacks evaluator-only template_id: {pair['pair_id']}")
            if template_id in prompt:
                fail(f"evaluator-only template_id leaked into prompt: {item_id}")
            record["template_id"] = template_id
            record["input_item"] = item
            record["input_sha256"] = sha256_bytes(canonical_json(item).encode("utf-8"))
        records.append(record)

    pilot_item_ids = [str(member_id) for pair in selected for member_id in pair["member_ids"]]
    packet: Json = {
        "schema_version": "1.0.0",
        "study_id": str(plan["study_id"]),
        "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
        "policy_sha256": sha256_file(policy_path),
        "renderer_sha256": sha256_file(ROOT / "src" / "claimpromotebench" / "prompts.py"),
        "decision_schema_sha256": sha256_file(ROOT / "schemas" / "agent-decision.schema.json"),
        "prompt_arm": prompt_arm,
        "records": records,
        "pilot_pair_ids": selected_pair_ids,
        "pilot_item_ids": pilot_item_ids,
        "selection_uses_model_outputs": False,
    }
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode("utf-8"))
    expected_packet = plan.get("prompt", {}).get("expected_packet_sha256")
    if expected_packet is not None and packet["packet_sha256"] != expected_packet:
        fail(
            "packet digest differs from frozen plan: "
            f"{packet['packet_sha256']} != {expected_packet}"
        )
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    packet = build_packet(args.dataset.resolve(), args.plan.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "records": len(packet["records"]),
                "pilot_items": len(packet["pilot_item_ids"]),
                "packet_sha256": packet["packet_sha256"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
