#!/usr/bin/env python3
"""Recompute reviewer-facing claims from anonymized item-level empirical records."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

from aggregate_capable_hidden_study import (
    PRIMARY_LANES,
    compact_analysis,
    compact_pilot,
    correctness_vector,
)
from analyze_stronger_model_study import analyze as analyze_stronger_run

from claimpromotebench.dataset import validate_with_schema
from claimpromotebench.hashing import canonical_json
from claimpromotebench.prompts import render_prompt
from claimpromotebench.statistics import holm_adjust, mcnemar_exact
from claimpromotebench.v2 import diagnose_decision, postgate_decision

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"anonymous-empirical-evidence: {message}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[Json]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        fail(f"non-object JSONL record: {path.relative_to(ROOT)}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def equivalent_json(left: Any, right: Any) -> bool:
    """Compare recomputed JSON while tolerating only machine-scale float summation drift."""

    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            equivalent_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equivalent_json(left_value, right_value)
            for left_value, right_value in zip(left, right, strict=True)
        )
    return bool(left == right)


def validate_raw_response_hashes(rows: list[Json], label: str) -> None:
    for row in rows:
        raw = row.get("raw_response_text")
        observed = row.get("raw_response_sha256")
        if raw is None:
            if observed is not None:
                fail(f"{label}: null raw response has a digest")
        elif observed != sha256_text(str(raw)):
            fail(f"{label}: raw response digest mismatch for {row.get('item_id')}")


def validate_prompt_binding(rows: list[Json], packet_path: Path, label: str) -> None:
    packet = load_json(packet_path)
    if not isinstance(packet, dict) or not isinstance(packet.get("records"), list):
        fail(f"{label}: malformed prompt packet")
    prompts = {str(row["item_id"]): str(row["prompt_sha256"]) for row in packet["records"]}
    for row in rows:
        item_id = str(row.get("item_id"))
        if item_id not in prompts or row.get("prompt_sha256") != prompts[item_id]:
            fail(f"{label}: prompt binding mismatch for {item_id}")


def validate_v1_recovery() -> Json:
    root = EVIDENCE / "v1-hidden-recovery"
    normalization = load_json(root / "semantic-format-normalization.json")
    if not isinstance(normalization, dict):
        fail("v1 normalization record is malformed")
    entries = normalization.get("run_files")
    if (
        normalization.get("status") != "SEMANTIC_FORMAT_ERROR_NORMALIZATION_COMPLETE"
        or normalization.get("runs") != 24
        or normalization.get("decisions") != 7200
        or not isinstance(entries, list)
        or len(entries) != 24
    ):
        fail("v1 normalization identity changed")

    normalized_rows: list[Json] = []
    reclassified = 0
    seen_identities: set[tuple[str, str, int]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            fail("v1 normalization entry is malformed")
        source_path = root / str(entry["source"]).removeprefix("work/")
        normalized_path = root / str(entry["normalized"]).removeprefix("work/")
        if sha256_file(source_path) != entry.get("source_sha256"):
            fail(f"v1 source digest mismatch: {source_path.relative_to(root)}")
        if sha256_file(normalized_path) != entry.get("normalized_sha256"):
            fail(f"v1 normalized digest mismatch: {normalized_path.relative_to(root)}")
        source = load_jsonl(source_path)
        normalized = load_jsonl(normalized_path)
        if len(source) != 300 or len(normalized) != 300:
            fail("v1 run coverage changed")
        source_by_id = {str(row["item_id"]): row for row in source}
        normalized_by_id = {str(row["item_id"]): row for row in normalized}
        if set(source_by_id) != set(normalized_by_id) or len(source_by_id) != 300:
            fail("v1 source/normalized item coverage differs")

        changed = 0
        for item_id in sorted(source_by_id):
            before = source_by_id[item_id]
            after = normalized_by_id[item_id]
            if before == after:
                continue
            expected = dict(before)
            expected["parse_status"] = "FORMAT_ERROR"
            expected["raw_decision"] = None
            expected["final_decision"] = None
            if after != expected or before.get("parse_status") != "OK":
                fail(f"v1 normalization changed an unregistered field: {item_id}")
            changed += 1
        if changed != entry.get("semantic_format_errors_reclassified"):
            fail("v1 per-run normalization count differs")
        reclassified += changed
        normalized_rows.extend(normalized)

        first = normalized[0]
        identity = (str(first["model_id"]), str(first["arm"]), int(first["seed"]))
        if identity in seen_identities:
            fail(f"duplicate v1 run identity: {identity}")
        seen_identities.add(identity)

    status_counts = Counter(str(row["parse_status"]) for row in normalized_rows)
    actions = Counter(
        str(row["raw_decision"]["action"]) for row in normalized_rows if row["parse_status"] == "OK"
    )
    if reclassified != 27:
        fail("v1 semantic reclassification total changed")
    if status_counts != Counter({"FORMAT_ERROR": 5327, "OK": 1873}):
        fail(f"v1 status totals changed: {dict(status_counts)}")
    if actions != Counter({"ALLOW": 1873}):
        fail(f"v1 raw action distribution changed: {dict(actions)}")
    return {
        "runs": len(seen_identities),
        "records": len(normalized_rows),
        "semantic_format_errors_reclassified": reclassified,
        "status_counts": dict(status_counts),
        "raw_action_distribution": dict(actions),
    }


def validate_v1_end_to_end(gold_by_id: dict[str, Json], pairs: list[Json]) -> Json:
    root = EVIDENCE / "v1-hidden-recovery" / "normalized-evidence"
    run_paths = sorted(root.glob("*/run.jsonl"))
    if len(run_paths) != 24:
        fail("v1 end-to-end recomputation requires 24 normalized runs")

    expected_correct_actions = {
        ("Qwen/Qwen3-0.6B", "ledger", 104729): 106,
        ("Qwen/Qwen3-0.6B", "ledger", 130363): 136,
        ("Qwen/Qwen3-0.6B", "ledger", 169087): 88,
        ("Qwen/Qwen3-0.6B", "ledger_verifier", 104729): 107,
        ("Qwen/Qwen3-0.6B", "ledger_verifier", 130363): 121,
        ("Qwen/Qwen3-0.6B", "ledger_verifier", 169087): 58,
        ("Qwen/Qwen3-0.6B", "ledger_verifier_gate", 104729): 83,
        ("Qwen/Qwen3-0.6B", "ledger_verifier_gate", 130363): 63,
        ("Qwen/Qwen3-0.6B", "ledger_verifier_gate", 169087): 26,
        ("Qwen/Qwen3-1.7B", "ledger_verifier_gate", 104729): 69,
        ("Qwen/Qwen3-1.7B", "ledger_verifier_gate", 130363): 34,
        ("Qwen/Qwen3-1.7B", "ledger_verifier_gate", 169087): 69,
    }

    seen: set[tuple[str, str, int]] = set()
    summaries: list[Json] = []
    total_correct_actions = 0
    total_correct_pairs = 0
    for path in run_paths:
        rows = load_jsonl(path)
        identities: set[tuple[str, str, int]] = set()
        for row in rows:
            seed = row.get("seed")
            if not isinstance(seed, int) or isinstance(seed, bool):
                fail(f"v1 normalized run has an invalid seed: {path.parent.name}")
            identities.add((str(row.get("model_id")), str(row.get("arm")), seed))
        if len(rows) != 300 or len(identities) != 1:
            fail(f"v1 normalized run identity or coverage changed: {path.parent.name}")
        identity = identities.pop()
        if identity in seen:
            fail(f"duplicate v1 normalized run identity: {identity}")
        seen.add(identity)
        by_id = {str(row.get("item_id")): row for row in rows}
        if len(by_id) != 300 or set(by_id) != set(gold_by_id):
            fail(f"v1 normalized run does not match released hidden items: {identity}")

        item_correct = {
            item_id: row.get("parse_status") == "OK"
            and isinstance(row.get("raw_decision"), dict)
            and row["raw_decision"].get("action") == gold_by_id[item_id]["decision"]["action"]
            for item_id, row in by_id.items()
        }
        correct_actions = sum(item_correct.values())
        correct_pairs = sum(
            all(item_correct[str(item_id)] for item_id in pair["member_ids"]) for pair in pairs
        )
        if correct_actions != expected_correct_actions.get(identity, 0):
            fail(f"v1 end-to-end action result changed: {identity} {correct_actions}")
        if correct_pairs != 0:
            fail(f"v1 end-to-end pair result changed: {identity} {correct_pairs}")

        total_correct_actions += correct_actions
        total_correct_pairs += correct_pairs
        summaries.append(
            {
                "model_id": identity[0],
                "arm": identity[1],
                "seed": identity[2],
                "correct_actions": correct_actions,
                "trials": len(rows),
                "correct_pairs": correct_pairs,
                "pairs": len(pairs),
            }
        )

    if total_correct_actions != 960 or total_correct_pairs != 0:
        fail("v1 aggregate end-to-end result changed")
    return {
        "runs": len(summaries),
        "correct_actions": total_correct_actions,
        "action_trials": len(summaries) * 300,
        "action_accuracy": total_correct_actions / (len(summaries) * 300),
        "correct_pairs": total_correct_pairs,
        "pair_trials": len(summaries) * len(pairs),
        "pair_accuracy": 0.0,
        "run_summaries": summaries,
    }


def complete_pair_counts(
    rows: list[Json], pairs: list[Json], gold_by_id: dict[str, Json]
) -> tuple[int, int]:
    by_id = {str(row["item_id"]): row for row in rows}
    complete = 0
    correct = 0
    for pair in pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        if all(by_id[item_id]["parse_status"] == "OK" for item_id in member_ids):
            complete += 1
            if all(
                by_id[item_id]["raw_decision"]["action"]
                == gold_by_id[item_id]["decision"]["action"]
                for item_id in member_ids
            ):
                correct += 1
    return complete, correct


def validate_v2_public_pilot() -> Json:
    root = EVIDENCE / "v2-public-pilot"
    run_paths = sorted(root.glob("*/v2-runs/*.jsonl"))
    if len(run_paths) != 4:
        fail("v2 public pilot evidence must contain four item-level runs")

    expected: dict[tuple[str, str], Json] = {
        ("Qwen/Qwen3-0.6B", "free"): {
            "status_counts": Counter({"OK": 30, "SCHEMA_ERROR": 10}),
            "correct": 15,
            "complete_pairs": 14,
            "correct_pairs": 0,
        },
        ("Qwen/Qwen3-0.6B", "json_schema"): {
            "status_counts": Counter({"OK": 40}),
            "correct": 20,
            "complete_pairs": 20,
            "correct_pairs": 0,
        },
        ("Qwen/Qwen3-1.7B", "free"): {
            "status_counts": Counter({"SCHEMA_ERROR": 40}),
            "correct": 0,
            "complete_pairs": 0,
            "correct_pairs": 0,
        },
        ("Qwen/Qwen3-1.7B", "json_schema"): {
            "status_counts": Counter({"OK": 38, "SCHEMA_ERROR": 2}),
            "correct": 19,
            "complete_pairs": 18,
            "correct_pairs": 0,
        },
    }

    inputs = load_jsonl(ROOT / "data" / "alpha" / "inputs.jsonl")
    gold = load_jsonl(ROOT / "data" / "alpha" / "gold.jsonl")
    pairs = load_json(ROOT / "data" / "alpha" / "pairs.json")
    manifest = load_json(ROOT / "data" / "alpha" / "manifest.json")
    if not isinstance(pairs, list) or not isinstance(manifest, dict):
        fail("v2 public pilot dataset metadata is malformed")
    policy = load_json(ROOT / "policies" / str(manifest["policy_file"]))
    decoding = load_json(ROOT / "configs" / "decoding-v1.json")
    if not isinstance(policy, dict):
        fail("v2 public pilot policy is malformed")
    if not isinstance(decoding, dict) or not isinstance(decoding.get("control_instruction"), str):
        fail("v2 public pilot decoding contract is malformed")
    input_by_id = {str(row["id"]): row for row in inputs}
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(input_by_id) != 40 or set(input_by_id) != set(gold_by_id):
        fail("v2 public pilot public dataset coverage changed")
    prompt_hashes: dict[str, str] = {}
    for item_id, item in input_by_id.items():
        rendered = render_prompt(
            item,
            "ledger_verifier",
            ROOT / "data" / "alpha",
            policy=policy,
            evaluation_time=str(manifest["evaluation_time"]),
        )
        exact_prompt = f"{rendered.rstrip()}\n\n{decoding['control_instruction']}\n"
        prompt_hashes[item_id] = sha256_text(exact_prompt)

    summaries: dict[str, Json] = {}
    all_rows: list[Json] = []
    seen: set[tuple[str, str]] = set()
    for path in run_paths:
        rows = load_jsonl(path)
        if len(rows) != 40 or len({str(row.get("item_id")) for row in rows}) != 40:
            fail(f"v2 public pilot run coverage changed: {path.name}")
        identities = {(str(row.get("model_id")), str(row.get("decoding_mode"))) for row in rows}
        if len(identities) != 1:
            fail(f"v2 public pilot mixed run identity: {path.name}")
        identity = identities.pop()
        if identity not in expected or identity in seen:
            fail(f"v2 public pilot unexpected or duplicate run: {identity}")
        seen.add(identity)
        if (
            {str(row.get("item_id")) for row in rows} != set(gold_by_id)
            or {row.get("seed") for row in rows} != {104729}
            or {row.get("prompt_arm") for row in rows} != {"ledger_verifier"}
        ):
            fail(f"v2 public pilot item, seed, or prompt arm changed: {identity}")
        for row in rows:
            item_id = str(row["item_id"])
            if row.get("prompt_sha256") != prompt_hashes[item_id]:
                fail(f"v2 public pilot prompt binding mismatch for {item_id}")
            if identity[1] == "free" and row.get("response_format_sha256") is not None:
                fail(f"v2 public pilot free run has a response-format digest: {item_id}")
            if identity[1] == "json_schema" and not row.get("response_format_sha256"):
                fail(f"v2 public pilot constrained run lacks a response-format digest: {item_id}")
        validate_raw_response_hashes(rows, f"v2 public pilot {identity}")

        status_counts = Counter(str(row["parse_status"]) for row in rows)
        parseable = [row for row in rows if row["parse_status"] == "OK"]
        correct = sum(
            row["raw_decision"]["action"] == gold_by_id[str(row["item_id"])]["decision"]["action"]
            for row in parseable
        )
        complete_pairs, correct_pairs = complete_pair_counts(rows, pairs, gold_by_id)
        exp = expected[identity]
        if (
            status_counts != exp["status_counts"]
            or correct != exp["correct"]
            or complete_pairs != exp["complete_pairs"]
            or correct_pairs != exp["correct_pairs"]
        ):
            fail(f"v2 public pilot result differs from item-level records: {identity}")
        summaries[f"{identity[0]}::{identity[1]}"] = {
            "records": len(rows),
            "parseable_decisions": len(parseable),
            "correct_decisions": correct,
            "end_to_end_action_accuracy": correct / len(rows),
            "complete_pairs": complete_pairs,
            "correct_pairs": correct_pairs,
            "end_to_end_pair_accuracy": correct_pairs / len(pairs),
            "status_counts": dict(status_counts),
        }
        all_rows.extend(rows)

    if seen != set(expected):
        fail("v2 public pilot run matrix is incomplete")
    aggregate = load_json(root / "aggregate.json")
    if (
        not isinstance(aggregate, dict)
        or aggregate.get("status") != "COMPLETE"
        or aggregate.get("aggregate_status_counts") != {"OK": 108, "SCHEMA_ERROR": 52}
        or Counter(str(row["parse_status"]) for row in all_rows)
        != Counter({"OK": 108, "SCHEMA_ERROR": 52})
    ):
        fail("v2 public pilot aggregate differs from item-level records")
    return {"runs": summaries, "records": len(all_rows), "parseable_decisions": 108}


def validate_gpt54_followup() -> Json:
    root = EVIDENCE / "gpt54-public-dev"
    run_paths = sorted((root / "runs").glob("*.jsonl"))
    if len(run_paths) != 3:
        fail("GPT-5.4 evidence must contain three distinct runs")
    full_paths = [path for path in run_paths if "-full-" in path.name]
    successful_pilots = [path for path in run_paths if "max-tokens-pilot" in path.name]
    failed_pilots = [
        path for path in run_paths if "-pilot-" in path.name and "max-tokens-pilot" not in path.name
    ]
    if not (len(full_paths) == len(successful_pilots) == len(failed_pilots) == 1):
        fail("GPT-5.4 run roles are ambiguous")

    failed = load_jsonl(failed_pilots[0])
    pilot = load_jsonl(successful_pilots[0])
    full = load_jsonl(full_paths[0])
    if (
        len(failed) != 12
        or sum(row["transport_status"] == "ERROR" for row in failed) != 12
        or sum(row["parse_status"] == "OK" for row in failed) != 0
    ):
        fail("GPT-5.4 preserved transport-only STOP changed")
    if (
        len(pilot) != 12
        or sum(row["transport_status"] == "ERROR" for row in pilot) != 0
        or sum(row["parse_status"] == "OK" for row in pilot) != 12
    ):
        fail("GPT-5.4 successful pilot changed")
    if len(full) != 100 or len({str(row["item_id"]) for row in full}) != 100:
        fail("GPT-5.4 full item coverage changed")

    validate_prompt_binding([*failed, *pilot, *full], root / "prompt-packet.json", "GPT-5.4")
    validate_raw_response_hashes([*failed, *pilot, *full], "GPT-5.4")
    gold = load_jsonl(root / "dataset" / "gold.jsonl")
    pairs = load_json(root / "dataset" / "pairs.json")
    if not isinstance(pairs, list):
        fail("GPT-5.4 pair file is malformed")
    gold_by_id = {str(row["id"]): row for row in gold}
    if {str(row["item_id"]) for row in full} != set(gold_by_id):
        fail("GPT-5.4 full/gold coverage differs")
    parseable = [row for row in full if row["parse_status"] == "OK"]
    correct = sum(
        row["raw_decision"]["action"] == gold_by_id[str(row["item_id"])]["decision"]["action"]
        for row in parseable
    )
    action_distribution = Counter(str(row["raw_decision"]["action"]) for row in parseable)
    complete_pairs, correct_pairs = complete_pair_counts(full, pairs, gold_by_id)
    if (
        len(parseable) != 99
        or correct != 99
        or complete_pairs != 49
        or correct_pairs != 49
        or action_distribution != Counter({"ALLOW": 50, "HOLD": 45, "DEMOTE": 2, "ESCALATE": 2})
    ):
        fail("GPT-5.4 full result differs from its item-level records")
    return {
        "pilot_records": len(pilot),
        "full_records": len(full),
        "parseable_decisions": len(parseable),
        "correct_decisions": correct,
        "complete_pairs": complete_pairs,
        "correct_pairs": correct_pairs,
        "raw_action_distribution": dict(action_distribution),
    }


def extract_single_json_object(content: str) -> str | None:
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(content):
        if start is None:
            if char == "{":
                start = index
                depth = 1
                in_string = False
                escaped = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidates.append(content[start : index + 1])
                start = None
    return candidates[0] if len(candidates) == 1 and start is None else None


def diagnose_capable_content(
    content: str, item: Json, schema_path: Path, allow_extraction: bool
) -> tuple[str, Json | None, str | None]:
    status, decision, detail = diagnose_decision(content, item, schema_path=schema_path)
    if status != "JSON_SYNTAX_ERROR" or not allow_extraction:
        return status, decision, detail
    extracted = extract_single_json_object(content)
    if extracted is None:
        return status, decision, detail
    status, decision, detail = diagnose_decision(extracted, item, schema_path=schema_path)
    marker = "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
    return status, decision, marker if detail is None else f"{marker}: {detail}"


def reject_hidden_reasoning(value: Any, label: str) -> None:
    if isinstance(value, dict):
        forbidden = {"reasoning_content", "thought", "thoughts", "thinking_content"}
        overlap = forbidden & set(value)
        if overlap:
            fail(f"{label}: hidden reasoning fields survived: {sorted(overlap)}")
        for child in value.values():
            reject_hidden_reasoning(child, label)
    elif isinstance(value, list):
        for child in value:
            reject_hidden_reasoning(child, label)


def validate_capable_hidden() -> Json:
    root = EVIDENCE / "capable-hidden"
    dataset = root / "dataset"
    plan = load_json(root / "study-plan.json")
    packet = load_json(root / "prompt-packet.json")
    aggregate = load_json(root / "aggregate.json")
    if not all(isinstance(value, dict) for value in (plan, packet, aggregate)):
        fail("capable hidden plan, packet, and aggregate must be objects")

    inputs = load_jsonl(dataset / "inputs.jsonl")
    gold = load_jsonl(dataset / "gold.jsonl")
    pairs = load_json(dataset / "pairs.json")
    manifest = load_json(dataset / "manifest.json")
    if not isinstance(pairs, list) or not isinstance(manifest, dict):
        fail("capable hidden dataset metadata is malformed")
    input_by_id = {str(row["id"]): row for row in inputs}
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(input_by_id) != 300 or set(input_by_id) != set(gold_by_id) or len(pairs) != 150:
        fail("capable hidden dataset coverage changed")
    v1_end_to_end = validate_v1_end_to_end(gold_by_id, pairs)

    dataset_contract = plan.get("dataset")
    if not isinstance(dataset_contract, dict):
        fail("capable hidden plan lacks a dataset contract")
    expected_dataset_hashes = {
        "dataset_manifest_sha256": sha256_file(dataset / "manifest.json"),
        "inputs_sha256": sha256_file(dataset / "inputs.jsonl"),
        "gold_sha256": sha256_file(dataset / "gold.jsonl"),
        "pairs_sha256": sha256_file(dataset / "pairs.json"),
    }
    for key, observed in expected_dataset_hashes.items():
        if dataset_contract.get(key) != observed:
            fail(f"capable hidden dataset digest changed: {key}")

    packet_payload = deepcopy(packet)
    observed_packet_sha = packet_payload.pop("packet_sha256", None)
    recomputed_packet_sha = sha256_text(canonical_json(packet_payload))
    if observed_packet_sha != recomputed_packet_sha:
        fail("capable hidden packet digest does not match its contents")
    packet_records = packet.get("records")
    if not isinstance(packet_records, list):
        fail("capable hidden packet records are malformed")
    packet_by_id: dict[str, Json] = {}
    for row in packet_records:
        if not isinstance(row, dict) or not isinstance(row.get("prompt"), str):
            fail("capable hidden packet contains a malformed prompt record")
        item_id = str(row.get("item_id"))
        prompt = str(row["prompt"])
        if item_id in packet_by_id or row.get("prompt_sha256") != sha256_text(prompt):
            fail(f"capable hidden packet prompt identity changed: {item_id}")
        if row.get("utf8_bytes") != len(prompt.encode("utf-8")):
            fail(f"capable hidden packet prompt byte count changed: {item_id}")
        packet_by_id[item_id] = row
    if set(packet_by_id) != set(input_by_id):
        fail("capable hidden packet/dataset coverage differs")
    pilot_ids = {str(value) for value in packet.get("pilot_item_ids", [])}
    if len(pilot_ids) != 12 or not pilot_ids <= set(input_by_id):
        fail("capable hidden pilot selection changed")

    lanes = {
        str(row["lane_id"]): row
        for row in plan.get("formal_lanes", [])
        if isinstance(row, dict) and isinstance(row.get("lane_id"), str)
    }
    if len(lanes) != 7:
        fail("capable hidden formal lane matrix changed")
    accepted_commits = {
        str(value)
        for value in plan.get("collection_amendment", {}).get("accepted_frozen_plan_commits", [])
    }
    if len(accepted_commits) != 2:
        fail("capable hidden anonymous frozen-plan aliases changed")

    policy = load_json(ROOT / "policies" / str(manifest["policy_file"]))
    if not isinstance(policy, dict):
        fail("capable hidden policy is malformed")
    run_schema = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
    decision_schema = ROOT / "schemas" / "agent-decision.schema.json"
    run_paths = sorted((root / "canonical" / "runs").glob("*.jsonl"))
    if len(run_paths) != 9:
        fail("capable hidden canonical evidence must contain seven pilots and two full runs")

    recomputed: dict[tuple[str, str], Json] = {}
    rows_by_identity: dict[tuple[str, str], list[Json]] = {}
    for path in run_paths:
        rows = load_jsonl(path)
        identities = {(str(row.get("lane_id")), str(row.get("phase"))) for row in rows}
        if len(identities) != 1:
            fail(f"capable hidden run mixes identities: {path.name}")
        identity = identities.pop()
        lane_id, phase = identity
        if lane_id not in lanes or phase not in {"pilot", "full"} or identity in recomputed:
            fail(f"capable hidden unexpected or duplicate run: {identity}")
        expected_ids = pilot_ids if phase == "pilot" else set(input_by_id)
        observed_ids = {str(row.get("item_id")) for row in rows}
        if len(rows) != len(expected_ids) or observed_ids != expected_ids:
            fail(f"capable hidden run coverage changed: {identity}")
        lane = lanes[lane_id]
        for row in rows:
            item_id = str(row["item_id"])
            validate_with_schema(row, run_schema, item_id)
            reject_hidden_reasoning(row, f"capable hidden {identity}")
            if (
                row.get("study_id") != plan.get("study_id")
                or row.get("frozen_plan_commit") not in accepted_commits
                or row.get("packet_sha256") != observed_packet_sha
                or row.get("dataset_manifest_sha256")
                != expected_dataset_hashes["dataset_manifest_sha256"]
                or row.get("model_requested") != lane.get("model")
                or row.get("prompt_sha256") != packet_by_id[item_id]["prompt_sha256"]
            ):
                fail(f"capable hidden record binding changed: {identity} {item_id}")
            raw = row.get("raw_response_text")
            if raw is None:
                if row.get("raw_response_sha256") is not None:
                    fail(f"capable hidden null response has a digest: {item_id}")
            elif row.get("raw_response_sha256") != sha256_text(str(raw)):
                fail(f"capable hidden raw response digest mismatch: {item_id}")

            if row.get("transport_status") == "ERROR":
                expected_status, expected_decision, expected_detail = (
                    "TRANSPORT_ERROR",
                    None,
                    row.get("transport_error"),
                )
            elif raw is None:
                expected_status, expected_decision, expected_detail = (
                    "SCHEMA_ERROR",
                    None,
                    "provider returned no final response text",
                )
            else:
                expected_status, expected_decision, expected_detail = diagnose_capable_content(
                    str(raw),
                    input_by_id[item_id],
                    decision_schema,
                    bool(lane.get("allow_single_json_object_extraction", False)),
                )
            if (
                row.get("parse_status") != expected_status
                or row.get("raw_decision") != expected_decision
                or row.get("parse_error_detail") != expected_detail
            ):
                fail(f"capable hidden parser replay differs: {identity} {item_id}")
            expected_postgate = (
                postgate_decision(
                    expected_decision,
                    input_by_id[item_id],
                    policy,
                    str(manifest["evaluation_time"]),
                )
                if expected_decision is not None
                else None
            )
            if row.get("postgate_decision") != expected_postgate:
                fail(f"capable hidden post-gate replay differs: {identity} {item_id}")

        analysis_path = root / "canonical" / "analysis" / f"{path.stem}.json"
        archived_analysis = load_json(analysis_path)
        if not isinstance(archived_analysis, dict):
            fail(f"capable hidden analysis is malformed: {analysis_path.name}")
        rebuilt_analysis = analyze_stronger_run(dataset, packet, plan, path)
        comparable_keys = (
            "records",
            "continuation_gate",
            "usage",
            "cost",
            "raw_action_distribution",
            "postgate_action_distribution",
            "metrics",
            "complete_metrics",
            "uncertainty",
        )
        for key in comparable_keys:
            if not equivalent_json(archived_analysis.get(key), rebuilt_analysis.get(key)):
                fail(
                    "capable hidden archived analysis differs from recomputation: "
                    f"{identity}: {key}"
                )
        if archived_analysis.get("run_sha256") != sha256_file(path):
            fail(f"capable hidden analysis run digest differs: {identity}")
        recomputed[identity] = rebuilt_analysis
        rows_by_identity[identity] = rows

    pilot_lanes = {lane_id for lane_id, phase in recomputed if phase == "pilot"}
    go_lanes = {
        lane_id
        for (lane_id, phase), value in recomputed.items()
        if phase == "pilot" and value["continuation_gate"]["decision"] == "GO"
    }
    full_lanes = {lane_id for lane_id, phase in recomputed if phase == "full"}
    if pilot_lanes != set(lanes) or full_lanes != go_lanes or len(go_lanes) != 2:
        fail("capable hidden GO/STOP-derived full-run matrix changed")

    qualification = aggregate.get("qualification")
    complete = aggregate.get("models_with_complete_hidden_pass")
    if not isinstance(qualification, dict) or not isinstance(complete, list):
        fail("capable hidden aggregate result matrix is malformed")
    expected_pilots = [compact_pilot(recomputed[(lane, "pilot")]) for lane in sorted(lanes)]
    expected_full = [compact_analysis(recomputed[(lane, "full")]) for lane in sorted(full_lanes)]
    if (
        qualification.get("attempted_lanes") != sorted(lanes)
        or qualification.get("go_lanes") != sorted(go_lanes)
        or qualification.get("stop_lanes") != sorted(set(lanes) - go_lanes)
        or qualification.get("pilots") != expected_pilots
        or not equivalent_json(complete, expected_full)
    ):
        fail("capable hidden aggregate differs from canonical analyses")

    always_allow = [
        gold_by_id[item_id]["decision"]["action"] == "ALLOW" for item_id in sorted(gold_by_id)
    ]
    if aggregate.get("baselines", {}).get("always_allow") != {
        "correct": sum(always_allow),
        "trials": len(always_allow),
        "accuracy": sum(always_allow) / len(always_allow),
    }:
        fail("capable hidden always-ALLOW baseline changed")
    completed_primary = [
        primary_lane_id for primary_lane_id in PRIMARY_LANES if primary_lane_id in full_lanes
    ]
    tests: list[Json] = []
    for primary_lane_id in completed_primary:
        test = mcnemar_exact(
            always_allow,
            correctness_vector(rows_by_identity[(primary_lane_id, "full")], gold_by_id),
        )
        tests.append({"lane_id": primary_lane_id, **test})
    adjusted = holm_adjust([float(row["p"]) for row in tests])
    for row, p_holm in zip(tests, adjusted, strict=True):
        row["p_holm_within_completed_family"] = p_holm
    observed_tests = aggregate.get("prespecified_tests", {}).get("models_vs_always_allow", {})
    if (
        observed_tests.get("completed_lanes") != completed_primary
        or not equivalent_json(observed_tests.get("tests"), tests)
        or observed_tests.get("status") != "PARTIAL_FAMILY"
    ):
        fail("capable hidden baseline tests changed")

    return {
        "v1_end_to_end_against_released_hidden_gold": v1_end_to_end,
        "pilots": len(pilot_lanes),
        "go_lanes": sorted(go_lanes),
        "stop_lanes": sorted(set(lanes) - go_lanes),
        "full_runs": {
            lane: recomputed[(lane, "full")]["complete_metrics"]["end_to_end"]
            for lane in sorted(full_lanes)
        },
        "baseline_tests": tests,
    }


def main() -> int:
    result = {
        "status": "PASS",
        "v1_hidden_recovery": validate_v1_recovery(),
        "v2_public_pilot": validate_v2_public_pilot(),
        "gpt54_public_development": validate_gpt54_followup(),
        "capable_hidden": validate_capable_hidden(),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
