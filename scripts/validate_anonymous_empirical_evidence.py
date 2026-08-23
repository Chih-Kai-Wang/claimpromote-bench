#!/usr/bin/env python3
"""Recompute reviewer-facing claims from anonymized item-level empirical records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

from aggregate_capable_hidden_study import (
    PRIMARY_LANES,
    action_breakdown,
    compact_analysis,
    compact_pilot,
    correctness_vector,
    pilot_excluded_summary,
)
from analyze_balanced_public_challenge import (
    combine_lane_metrics,
)
from analyze_balanced_public_challenge import (
    derive_reporting_metrics as derive_balanced_metrics,
)
from analyze_confirmatory_hidden_study import analyze as analyze_fresh_confirmatory
from analyze_stronger_model_study import analyze as analyze_stronger_run

from claimpromotebench.dataset import validate_with_schema
from claimpromotebench.hashing import canonical_json
from claimpromotebench.prompts import render_prompt
from claimpromotebench.statistics import holm_adjust, mcnemar_exact
from claimpromotebench.v2 import diagnose_decision, postgate_decision

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")


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


def validate_self_digest(value: Json, field: str, label: str) -> None:
    payload = {key: child for key, child in value.items() if key != field}
    if value.get(field) != sha256_text(canonical_json(payload)):
        fail(f"{label}: self-digest changed")


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
        forbidden = {
            "reasoning_content",
            "thinking",
            "thinking_content",
            "thought",
            "thoughts",
        }
        overlap = forbidden & set(value)
        if overlap:
            fail(f"{label}: hidden reasoning fields survived: {sorted(overlap)}")
        if str(value.get("type", "")).lower() in {"reasoning", "thinking"}:
            fail(f"{label}: hidden reasoning content block survived")
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
    review_audit = plan.get("post_collection_review_audit")
    if not isinstance(review_audit, dict):
        fail("capable hidden post-collection review audit is missing")
    executed_commits = {str(value) for value in review_audit.get("executed_plan_commits", [])}
    expected_attempt_counts = review_audit.get("attempt_counts_by_lane")
    if (
        review_audit.get("analysis_status") != "EXPLORATORY_ADAPTIVE_INTERFACE_QUALIFICATION"
        or review_audit.get("executed_pilot_attempts") != 14
        or review_audit.get("executed_full_passes") != 2
        or len(executed_commits) != 3
        or not isinstance(expected_attempt_counts, dict)
    ):
        fail("capable hidden adaptive-attempt audit changed")

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

    snapshot_root = root / "attempt-protocol-snapshots"
    snapshot_manifest = load_json(snapshot_root / "manifest.json")
    if not isinstance(snapshot_manifest, dict) or not isinstance(
        snapshot_manifest.get("stages"), list
    ):
        fail("capable hidden attempt-protocol snapshot manifest is malformed")
    stages: list[tuple[Path, str, Json]] = []
    for entry in snapshot_manifest["stages"]:
        if not isinstance(entry, dict):
            fail("capable hidden attempt-protocol stage is malformed")
        plan_path = snapshot_root / str(entry.get("plan_path"))
        runner_path = snapshot_root / str(entry.get("runner_path"))
        attempt_root = (snapshot_root / str(entry.get("attempt_history_path"))).resolve()
        frozen_commit = str(entry.get("frozen_plan_commit"))
        historical_plan = load_json(plan_path)
        if (
            not isinstance(historical_plan, dict)
            or not runner_path.is_file()
            or not attempt_root.is_dir()
            or frozen_commit not in executed_commits
        ):
            fail(f"capable hidden attempt-protocol stage is incomplete: {entry.get('stage')}")
        stages.append((attempt_root, frozen_commit, historical_plan))
    if len(stages) != 3 or {commit for _, commit, _ in stages} != executed_commits:
        fail("capable hidden attempt-protocol stage coverage changed")

    attempt_run_paths = sorted((root / "attempt-history").glob("**/runs/*.jsonl"))
    if len(attempt_run_paths) != 16:
        fail("capable hidden history must contain 14 pilots and two full-pass copies")
    attempt_phase_counts: Counter[str] = Counter()
    attempt_lane_counts: Counter[str] = Counter()
    attempt_digests: set[str] = set()
    for path in attempt_run_paths:
        stage_candidates = [
            (commit, historical_plan)
            for attempt_root, commit, historical_plan in stages
            if path.resolve().is_relative_to(attempt_root)
        ]
        if len(stage_candidates) != 1:
            fail(f"capable hidden attempt lacks one protocol snapshot: {path.relative_to(root)}")
        frozen_commit, historical_plan = stage_candidates[0]
        historical_lanes = {
            str(row["lane_id"]): row
            for row in historical_plan.get("formal_lanes", [])
            if isinstance(row, dict) and isinstance(row.get("lane_id"), str)
        }
        rows = load_jsonl(path)
        identities = {(str(row.get("lane_id")), str(row.get("phase"))) for row in rows}
        if len(identities) != 1:
            fail(f"capable hidden attempt mixes identities: {path.relative_to(root)}")
        lane_id, phase = identities.pop()
        if lane_id not in historical_lanes or phase not in {"pilot", "full"}:
            fail(f"capable hidden attempt has an unexpected identity: {(lane_id, phase)}")
        expected_ids = pilot_ids if phase == "pilot" else set(input_by_id)
        observed_ids = {str(row.get("item_id")) for row in rows}
        if len(rows) != len(expected_ids) or observed_ids != expected_ids:
            fail(f"capable hidden attempt coverage changed: {(lane_id, phase)}")
        historical_lane = historical_lanes[lane_id]
        for row in rows:
            item_id = str(row["item_id"])
            validate_with_schema(row, run_schema, item_id)
            reject_hidden_reasoning(row, f"capable hidden attempt {(lane_id, phase)}")
            if (
                row.get("study_id") != plan.get("study_id")
                or row.get("frozen_plan_commit") != frozen_commit
                or row.get("packet_sha256") != observed_packet_sha
                or row.get("dataset_manifest_sha256")
                != expected_dataset_hashes["dataset_manifest_sha256"]
                or row.get("model_requested") != historical_lane.get("model")
                or row.get("prompt_sha256") != packet_by_id[item_id]["prompt_sha256"]
            ):
                fail(f"capable hidden attempt binding changed: {(lane_id, phase)} {item_id}")
            raw = row.get("raw_response_text")
            if raw is None:
                if row.get("raw_response_sha256") is not None:
                    fail(f"capable hidden attempt null response has a digest: {item_id}")
            elif row.get("raw_response_sha256") != sha256_text(str(raw)):
                fail(f"capable hidden attempt raw response digest mismatch: {item_id}")
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
                    bool(historical_lane.get("allow_single_json_object_extraction", False)),
                )
            if (
                row.get("parse_status") != expected_status
                or row.get("raw_decision") != expected_decision
                or row.get("parse_error_detail") != expected_detail
            ):
                fail(f"capable hidden attempt parser replay differs: {(lane_id, phase)} {item_id}")
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
                fail(
                    f"capable hidden attempt post-gate replay differs: {(lane_id, phase)} {item_id}"
                )

        analysis_path = path.parent.parent / "analysis" / f"{path.stem}.json"
        archived_analysis = load_json(analysis_path)
        if not isinstance(archived_analysis, dict):
            fail(f"capable hidden attempt analysis is malformed: {analysis_path.name}")
        rebuilt_analysis = analyze_stronger_run(dataset, packet, historical_plan, path)
        for key in (
            "records",
            "continuation_gate",
            "usage",
            "cost",
            "raw_action_distribution",
            "postgate_action_distribution",
            "metrics",
            "complete_metrics",
            "uncertainty",
        ):
            if not equivalent_json(archived_analysis.get(key), rebuilt_analysis.get(key)):
                fail(
                    "capable hidden attempt analysis differs from recomputation: "
                    f"{path.relative_to(root)}: {key}"
                )
        run_digest = sha256_file(path)
        if archived_analysis.get("run_sha256") != run_digest:
            fail(f"capable hidden attempt analysis digest differs: {path.relative_to(root)}")
        attempt_phase_counts[phase] += 1
        if phase == "pilot":
            attempt_lane_counts[lane_id] += 1
        attempt_digests.add(run_digest)

    if attempt_phase_counts != Counter({"pilot": 14, "full": 2}):
        fail("capable hidden attempt-history phase counts changed")
    if dict(sorted(attempt_lane_counts.items())) != {
        str(key): int(value) for key, value in sorted(expected_attempt_counts.items())
    }:
        fail("capable hidden per-lane attempt counts changed")
    if not {sha256_file(path) for path in run_paths} <= attempt_digests:
        fail("capable hidden canonical view is not bound to attempt history")

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
        qualification.get("executed_pilot_attempts") != 14
        or qualification.get("attempt_history_released") is not True
        or qualification.get("attempted_lanes") != sorted(lanes)
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
        row["p_bonferroni_registered_six"] = min(1.0, float(row["p"]) * len(PRIMARY_LANES))
    observed_tests = aggregate.get("prespecified_tests", {}).get("models_vs_always_allow", {})
    if (
        observed_tests.get("completed_lanes") != completed_primary
        or not equivalent_json(observed_tests.get("tests"), tests)
        or observed_tests.get("status") != "PARTIAL_FAMILY"
        or observed_tests.get("inference_status")
        != "EXPLORATORY_SELECTION_AFFECTED_NO_CONFIRMATORY_FAMILYWISE_CLAIM"
    ):
        fail("capable hidden baseline tests changed")

    expected_full_breakdown = {
        lane: action_breakdown(rows_by_identity[(lane, "full")], gold_by_id, sorted(gold_by_id))
        for lane in sorted(full_lanes)
    }
    if not equivalent_json(aggregate.get("full_pass_action_breakdown"), expected_full_breakdown):
        fail("capable hidden full-pass action breakdown changed")
    expected_sensitivity = {
        lane: pilot_excluded_summary(rows_by_identity[(lane, "full")], gold_by_id, pairs, pilot_ids)
        for lane in sorted(full_lanes)
    }
    if not equivalent_json(aggregate.get("pilot_excluded_sensitivity"), expected_sensitivity):
        fail("capable hidden pilot-excluded sensitivity changed")

    return {
        "v1_end_to_end_against_released_hidden_gold": v1_end_to_end,
        "pilots": len(pilot_lanes),
        "executed_pilot_attempts": attempt_phase_counts["pilot"],
        "go_lanes": sorted(go_lanes),
        "stop_lanes": sorted(set(lanes) - go_lanes),
        "full_runs": {
            lane: recomputed[(lane, "full")]["complete_metrics"]["end_to_end"]
            for lane in sorted(full_lanes)
        },
        "baseline_tests": tests,
    }


def _fresh_scientific_projection(value: Json) -> Json:
    projected = deepcopy(value)
    projected.pop("aggregate_sha256", None)
    projected.pop("source_identity", None)
    scores = projected.get("scores")
    if isinstance(scores, dict):
        for score in scores.values():
            if isinstance(score, dict):
                score.pop("run_sha256", None)
    return projected


def validate_fresh_confirmatory() -> Json:
    root = EVIDENCE / "fresh-confirmatory"
    manifest_path = root / "MANIFEST.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        fail("fresh confirmatory evidence manifest is malformed")
    manifest_payload = deepcopy(manifest)
    observed_manifest_sha = manifest_payload.pop("manifest_sha256", None)
    if observed_manifest_sha != sha256_text(canonical_json(manifest_payload)):
        fail("fresh confirmatory evidence manifest self-digest changed")
    actual_files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if manifest["files"] != actual_files or manifest.get("file_count") != len(actual_files):
        fail("fresh confirmatory evidence manifest coverage changed")

    dataset = root / "dataset"
    dataset_manifest = load_json(dataset / "manifest.json")
    if not isinstance(dataset_manifest, dict) or not isinstance(
        dataset_manifest.get("files"), dict
    ):
        fail("fresh confirmatory dataset manifest is malformed")
    for relative, expected in dataset_manifest["files"].items():
        path = dataset / relative
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"fresh confirmatory dataset file digest changed: {relative}")

    inputs = load_jsonl(dataset / "inputs.jsonl")
    gold = load_jsonl(dataset / "gold.jsonl")
    pairs = load_json(dataset / "pairs.json")
    if not isinstance(pairs, list):
        fail("fresh confirmatory pair file is malformed")
    input_ids = {str(row["id"]) for row in inputs}
    gold_ids = {str(row["id"]) for row in gold}
    pair_ids = {str(row["pair_id"]) for row in pairs}
    if len(input_ids) != 300 or input_ids != gold_ids or len(pair_ids) != 150:
        fail("fresh confirmatory dataset coverage changed")
    if any(not re.fullmatch(r"v1-test-cfo-\d{3}-[ab]", item_id) for item_id in input_ids):
        fail("fresh confirmatory item namespace differs from released cfo IDs")
    if any(not re.fullmatch(r"v1-test-cfo-\d{3}", pair_id) for pair_id in pair_ids):
        fail("fresh confirmatory pair namespace differs from released cfo IDs")

    correction = load_json(root / "frozen-manifest-metadata-correction.json")
    if not isinstance(correction, dict):
        fail("fresh confirmatory frozen-manifest correction is malformed")
    correction_payload = deepcopy(correction)
    observed_correction_sha = correction_payload.pop("self_digest", None)
    if observed_correction_sha != sha256_text(canonical_json(correction_payload)):
        fail("fresh confirmatory frozen-manifest correction self-digest changed")
    if (
        correction.get("source_manifest_sha256") != sha256_file(dataset / "manifest.json")
        or correction.get("coverage_check", {}).get("item_ids_matching_observed_pattern") != 300
        or correction.get("coverage_check", {}).get("pair_ids_matching_observed_pattern") != 150
        or correction.get("scientific_impact") != "NONE"
    ):
        fail("fresh confirmatory frozen-manifest correction does not match the dataset")

    c2 = load_json(root / "c2-receipt-review.json")
    if not isinstance(c2, dict) or (
        c2.get("analysis_executed_before_receipt") is not False
        or c2.get("gold_loaded_before_receipt") is not False
        or c2.get("contains_gold_labels") is not False
        or c2.get("planned_cells") != 600
        or c2.get("sealed_cells") != 600
        or c2.get("outcome_counts") != {"RESPONSE_RECORDED": 600}
    ):
        fail("fresh confirmatory anonymous C2 receipt changed")

    expected_lanes = {
        "opencode-go-deepseek-v4-flash-matched",
        "opencode-go-qwen3.7-max",
    }
    lane_files = manifest.get("lane_files")
    if not isinstance(lane_files, dict) or set(lane_files) != expected_lanes:
        fail("fresh confirmatory lane manifest changed")
    rows_by_lane: dict[str, list[Json]] = {}
    run_paths: list[Path] = []
    for lane_id, relative in sorted(lane_files.items()):
        path = root / str(relative)
        rows = load_jsonl(path)
        run_paths.append(path)
        if (
            len(rows) != 300
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
            or {str(row.get("item_id")) for row in rows} != input_ids
        ):
            fail(f"fresh confirmatory projected run coverage changed: {lane_id}")
        for row in rows:
            reject_hidden_reasoning(row, f"fresh confirmatory {lane_id}")
            if row.get("application_post_count") != 1 or row.get("client_retry_count") != 0:
                fail(f"fresh confirmatory request accounting changed: {lane_id}")
            if row.get("redirect_followed") is not False:
                fail(f"fresh confirmatory redirect boundary changed: {lane_id}")
            raw_text = row.get("raw_final_text")
            raw_sha = row.get("raw_final_text_sha256")
            if raw_text is None:
                if raw_sha is not None:
                    fail(f"fresh confirmatory null final text has a digest: {lane_id}")
            elif raw_sha != sha256_text(str(raw_text)):
                fail(f"fresh confirmatory final-text digest changed: {lane_id}")
        rows_by_lane[lane_id] = rows

    qwen_id = "opencode-go-qwen3.7-max"
    flash_id = "opencode-go-deepseek-v4-flash-matched"
    qwen = rows_by_lane[qwen_id]
    flash = rows_by_lane[flash_id]
    if Counter(str(row.get("parse_status")) for row in qwen) != Counter(
        {"OK": 272, "HTTP_ERROR": 15, "TRANSPORT_ERROR": 10, "SEMANTIC_ERROR": 3}
    ):
        fail("fresh confirmatory Qwen parser-status distribution changed")
    if Counter(row.get("http_status") for row in qwen) != Counter(
        {200: 275, 500: 14, 503: 1, None: 10}
    ):
        fail("fresh confirmatory Qwen HTTP-status distribution changed")
    if Counter(str(row.get("parse_status")) for row in flash) != Counter({"HTTP_ERROR": 300}):
        fail("fresh confirmatory Flash parser-status distribution changed")
    if Counter(row.get("http_status") for row in flash) != Counter({401: 300}):
        fail("fresh confirmatory Flash HTTP-status distribution changed")
    qwen_usage = [
        row["usage"]
        for row in qwen
        if isinstance(row.get("usage"), dict) and isinstance(row["usage"].get("input_tokens"), int)
    ]
    if (
        len(qwen_usage) != 275
        or sum(int(row.get("input_tokens", 0)) for row in qwen_usage) != 662053
        or sum(int(row.get("output_tokens", 0)) for row in qwen_usage) != 613618
        or sum(int(row.get("output_tokens", 0)) > 1536 for row in qwen_usage) != 261
    ):
        fail("fresh confirmatory Qwen provider-reported usage changed")

    plan = load_json(root / "study-plan.json")
    packet = load_json(root / "prompt-packet.json")
    baselines = load_json(root / "baselines.json")
    reported = load_json(root / "reported-analysis.json")
    if not all(isinstance(value, dict) for value in (plan, packet, baselines, reported)):
        fail("fresh confirmatory plan, packet, baseline, or analysis is malformed")
    recomputed = analyze_fresh_confirmatory(dataset, packet, plan, baselines, run_paths)
    if not equivalent_json(
        _fresh_scientific_projection(recomputed),
        _fresh_scientific_projection(reported),
    ):
        fail("fresh confirmatory reported science differs from projected C2 records")

    study_result = load_json(root / "study-result.json")
    reporting_addendum = load_json(root / "reporting-addendum.json")
    redaction = load_json(root / "redaction-receipt-review.json")
    if not all(isinstance(value, dict) for value in (study_result, reporting_addendum, redaction)):
        fail(
            "fresh confirmatory study result, reporting addendum, or redaction receipt is malformed"
        )
    addendum_payload = deepcopy(reporting_addendum)
    observed_addendum_sha = addendum_payload.pop("self_digest", None)
    if observed_addendum_sha != sha256_text(canonical_json(addendum_payload)):
        fail("fresh confirmatory reporting addendum self-digest changed")
    qwen_score = recomputed["scores"][qwen_id]["raw"]
    qwen_test = next(
        row
        for row in recomputed["confirmatory_item_correctness_tests"]["tests"]
        if row["model_lane"] == qwen_id
    )
    qwen_summary = study_result.get("qwen_service_configuration", {})
    flash_summary = study_result.get("deepseek_flash_service_configuration", {})
    gold_actions = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
    qwen_predictions = {
        str(row["item_id"]): (
            str(row["raw_decision"]["action"])
            if row.get("parse_status") == "OK" and isinstance(row.get("raw_decision"), dict)
            else None
        )
        for row in qwen
    }
    complete_pairs = [
        pair
        for pair in pairs
        if all(qwen_predictions[str(item_id)] in ACTIONS for item_id in pair["member_ids"])
    ]
    correct_pairs = [
        pair
        for pair in pairs
        if all(
            qwen_predictions[str(item_id)] == gold_actions[str(item_id)]
            for item_id in pair["member_ids"]
        )
    ]
    factor_support: dict[str, Counter[str]] = {action: Counter() for action in ACTIONS}
    factor_counts: dict[str, Json] = {}
    for pair in pairs:
        factor_id = str(pair["factor_id"])
        invalid_action = gold_actions[str(pair["invalid_id"])]
        factor_support[invalid_action][factor_id] += 1
        factor = factor_counts.setdefault(
            factor_id,
            {
                "factor_id": factor_id,
                "family": str(pair["family"]),
                "invalid_action": invalid_action,
                "pairs": 0,
                "covered_pairs": 0,
                "correct_pairs": 0,
            },
        )
        member_ids = [str(item_id) for item_id in pair["member_ids"]]
        factor["pairs"] += 1
        factor["covered_pairs"] += int(
            all(qwen_predictions[item_id] in ACTIONS for item_id in member_ids)
        )
        factor["correct_pairs"] += int(
            all(qwen_predictions[item_id] == gold_actions[item_id] for item_id in member_ids)
        )
    factor_metrics: list[Json] = []
    for factor_id in sorted(factor_counts):
        factor = factor_counts[factor_id]
        covered = int(factor["covered_pairs"])
        pair_count = int(factor["pairs"])
        pair_correct = int(factor["correct_pairs"])
        factor_metrics.append(
            {
                **factor,
                "pair_coverage": covered / pair_count,
                "end_to_end_pair_accuracy": pair_correct / pair_count,
                "conditional_pair_accuracy": pair_correct / covered if covered else None,
            }
        )
    qwen_addendum = reporting_addendum.get("qwen_service_configuration", {})
    policy_ceiling = reporting_addendum.get("deterministic_policy_executor", {})
    if (
        not equivalent_json(
            qwen_summary.get("end_to_end_item_accuracy"), qwen_score["item_accuracy"]
        )
        or not equivalent_json(
            qwen_summary.get("end_to_end_pair_accuracy"), qwen_score["pair_accuracy"]
        )
        or not equivalent_json(
            qwen_summary.get("decision_coverage"), qwen_score["decision_coverage"]
        )
        or qwen_score["per_action"]["DEMOTE"]["correct"] != 0
        or not equivalent_json(
            qwen_summary.get("superiority_test_vs_public_dev_text_nb", {}).get("holm_adjusted_p"),
            qwen_test["holm_adjusted_p"],
        )
        or flash_summary.get("model_capability_interpretation") != "NON_EVALUABLE_NO_MODEL_OUTPUT"
        or flash_summary.get("http_401_records") != 300
        or qwen_addendum.get("valid_decisions") != 272
        or qwen_addendum.get("correct_items") != 258
        or qwen_addendum.get("complete_pairs") != len(complete_pairs)
        or len(complete_pairs) != 123
        or qwen_addendum.get("correct_pairs") != len(correct_pairs)
        or len(correct_pairs) != 113
        or not equivalent_json(
            qwen_addendum.get("conditional_item_accuracy_given_valid_decision"), 258 / 272
        )
        or not equivalent_json(
            qwen_addendum.get("conditional_pair_accuracy_given_complete_pair"), 113 / 123
        )
        or qwen_addendum.get("confusion") != qwen_score["confusion"]
        or qwen_addendum.get("factor_metrics") != factor_metrics
        or reporting_addendum.get("invalid_action_factor_support")
        != {
            action: dict(sorted(counts.items()))
            for action, counts in factor_support.items()
            if counts
        }
        or policy_ceiling.get("role")
        != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
        or policy_ceiling.get("correct_items") != 300
        or policy_ceiling.get("correct_pairs") != 150
    ):
        fail(
            "fresh confirmatory compact study result or reporting addendum "
            "differs from recomputation"
        )
    if (
        redaction.get("hidden_reasoning_present_in_public_release") is not False
        or redaction.get("original_scored_artifacts_modified") is not False
        or redaction.get("post_c2_transform") is not True
        or redaction.get("public_provider_envelopes_allowlisted") is not True
        or redaction.get("redacted_unique_model_item_cells") != 275
        or redaction.get("removed_content_blocks_including_raw_and_c2_copies") != 550
        or redaction.get("scientific_analysis_payload_byte_identical") is not True
        or redaction.get("source_to_derived_row_hashes_verified_before_anonymization") is not True
    ):
        fail("fresh confirmatory anonymous redaction receipt changed")

    return {
        "c2_sealed_cells": c2["sealed_cells"],
        "flash_http_401_records": 300,
        "flash_model_efficacy": "NON_EVALUABLE",
        "qwen_decision_coverage": qwen_score["decision_coverage"],
        "qwen_demote_correct": qwen_score["per_action"]["DEMOTE"]["correct"],
        "qwen_item_accuracy": qwen_score["item_accuracy"],
        "qwen_conditional_item_accuracy": qwen_addendum[
            "conditional_item_accuracy_given_valid_decision"
        ],
        "qwen_pair_coverage": qwen_addendum["pair_coverage"],
        "qwen_pair_accuracy": qwen_score["pair_accuracy"],
        "qwen_factor_count": len(factor_metrics),
        "qwen_conditional_pair_accuracy": qwen_addendum[
            "conditional_pair_accuracy_given_complete_pair"
        ],
        "qwen_vs_public_dev_nb_holm_p": qwen_test["holm_adjusted_p"],
        "redaction_status": redaction["status"],
    }


def validate_balanced_public_challenge() -> Json:
    root = EVIDENCE / "balanced-public-challenge"
    manifest = load_json(root / "MANIFEST.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        fail("balanced challenge manifest is malformed")
    manifest_payload = deepcopy(manifest)
    observed_manifest_sha = manifest_payload.pop("manifest_sha256", None)
    if observed_manifest_sha != sha256_text(canonical_json(manifest_payload)):
        fail("balanced challenge manifest self-digest changed")
    declared = manifest["files"]
    actual = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if manifest.get("file_count") != len(actual) or declared != actual:
        fail("balanced challenge manifest differs from the generated tree")
    scope = manifest.get("scope", {})
    if (
        scope.get("hidden_reasoning_included") is not False
        or scope.get("provider_response_identifiers_included") is not False
        or scope.get("source_artifact_or_workflow_ids_included") is not False
    ):
        fail("balanced challenge anonymous scope changed")

    dataset = root / "dataset"
    inputs = load_jsonl(dataset / "inputs.jsonl")
    gold = load_jsonl(dataset / "gold.jsonl")
    pairs = load_json(dataset / "pairs.json")
    plan = load_json(root / "study-plan.json")
    packet = load_json(root / "prompt-packet.json")
    aggregate = load_json(root / "reported-aggregate.json")
    correction = load_json(root / "reporting-correction-review.json")
    receipt = load_json(root / "privacy-receipt-review.json")
    if not all(isinstance(value, dict) for value in (plan, packet, aggregate, correction, receipt)):
        fail("balanced challenge plan, packet, aggregate, correction, or receipt is malformed")
    if not isinstance(pairs, list):
        fail("balanced challenge pairs are malformed")
    input_ids = {str(row["id"]) for row in inputs}
    gold_by_id = {str(row["id"]): row for row in gold}
    pair_ids = {str(row["pair_id"]) for row in pairs}
    factor_ids = {str(row["factor_id"]) for row in pairs}
    if (
        len(input_ids) != 180
        or input_ids != set(gold_by_id)
        or len(pair_ids) != 90
        or len(factor_ids) != 15
    ):
        fail("balanced challenge dataset coverage changed")
    action_counts = Counter(str(row["decision"]["action"]) for row in gold)
    if action_counts != Counter({"ALLOW": 90, "HOLD": 30, "DEMOTE": 30, "ESCALATE": 30}):
        fail("balanced challenge gold action distribution changed")
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("design", {}).get("attempts_per_item") != 1
        or plan.get("design", {}).get("held_out_generalization_claim") is not False
        or plan.get("statistics", {}).get("failure_rule")
        != "Every non-OK response remains in the denominator as incorrect."
    ):
        fail("balanced challenge plan boundary changed")
    packet_rows = packet.get("records")
    if (
        not isinstance(packet_rows, list)
        or {str(row.get("item_id")) for row in packet_rows} != input_ids
    ):
        fail("balanced challenge prompt-packet coverage changed")

    lane_files = manifest.get("lane_files")
    analysis_files = manifest.get("analysis_files")
    expected_lanes = {
        "opencode-go-deepseek-v4-flash-matched",
        "opencode-go-qwen3.7-max",
    }
    if (
        not isinstance(lane_files, dict)
        or not isinstance(analysis_files, dict)
        or set(lane_files) != expected_lanes
        or set(analysis_files) != expected_lanes
    ):
        fail("balanced challenge lane manifest changed")
    aggregate_lanes = {
        str(row.get("lane_id")): row for row in aggregate.get("lanes", []) if isinstance(row, dict)
    }
    if set(aggregate_lanes) != expected_lanes:
        fail("balanced challenge aggregate lane set changed")

    lane_metrics: dict[str, Json] = {}
    for lane_id in sorted(expected_lanes):
        run_path = root / str(lane_files[lane_id])
        rows = load_jsonl(run_path)
        if (
            len(rows) != 180
            or {str(row.get("item_id")) for row in rows} != input_ids
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
        ):
            fail(f"balanced challenge run coverage changed: {lane_id}")
        validate_raw_response_hashes(rows, f"balanced challenge {lane_id}")
        validate_prompt_binding(rows, root / "prompt-packet.json", f"balanced challenge {lane_id}")
        for row in rows:
            item_id = str(row.get("item_id"))
            validate_with_schema(
                row,
                ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json",
                item_id,
            )
            reject_hidden_reasoning(row, f"balanced challenge {lane_id}")
            if row.get("provider_response_id") is not None:
                fail(f"balanced challenge retained a provider response ID: {item_id}")
        metrics = derive_balanced_metrics(gold, pairs, rows)
        if not equivalent_json(metrics, aggregate_lanes[lane_id].get("metrics")):
            fail(f"balanced challenge aggregate differs from item-level records: {lane_id}")
        if aggregate_lanes[lane_id].get("run_sha256") != sha256_file(run_path):
            fail(f"balanced challenge aggregate run digest changed: {lane_id}")
        analysis_path = root / str(analysis_files[lane_id])
        analysis = load_json(analysis_path)
        if (
            not isinstance(analysis, dict)
            or analysis.get("lane_id") != lane_id
            or analysis.get("run_sha256") != sha256_file(run_path)
        ):
            fail(f"balanced challenge lane analysis binding changed: {lane_id}")
        lane_metrics[lane_id] = metrics

    qwen = lane_metrics["opencode-go-qwen3.7-max"]
    flash = lane_metrics["opencode-go-deepseek-v4-flash-matched"]
    if (
        correction.get("status") != "REPORTING_CORRECTION"
        or correction.get("source_identity") != "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
        or correction.get("metric_convention")
        != "FIXED_FOUR_CLASS_MACRO_F1_WITH_ZERO_DIVISION_EQUAL_TO_ZERO"
        or correction.get("scope", {}).get("model_calls_performed") != 0
        or correction.get("scope", {}).get("raw_or_terminal_records_changed") is not False
        or correction.get("scope", {}).get("primary_endpoints_changed") is not False
        or correction.get("anonymous_run_sha256")
        != {
            lane_id: sha256_file(root / str(lane_files[lane_id]))
            for lane_id in sorted(expected_lanes)
        }
    ):
        fail("balanced challenge reporting-correction boundary changed")
    affected = correction.get("affected_lanes", {}).get("opencode-go-deepseek-v4-flash-matched", {})
    if affected.get("historical") != {
        "conditional_macro_f1": 0.6243032962151766,
        "macro_f1": 0.5236761371215153,
        "per_action.DEMOTE.conditional_f1": None,
        "per_action.DEMOTE.end_to_end_f1": None,
        "per_action.DEMOTE.precision": None,
    } or affected.get("corrected") != {
        "conditional_macro_f1": flash["conditional_macro_f1"],
        "macro_f1": flash["macro_f1"],
        "per_action.DEMOTE.conditional_f1": flash["per_action"]["DEMOTE"]["conditional_f1"],
        "per_action.DEMOTE.end_to_end_f1": flash["per_action"]["DEMOTE"]["end_to_end_f1"],
        "per_action.DEMOTE.precision": flash["per_action"]["DEMOTE"]["precision"],
    }:
        fail("balanced challenge reporting-correction values changed")
    expected_qwen = {
        "parseable_items": 148,
        "correct_items": 132,
        "covered_pairs": 64,
        "correct_pairs": 48,
        "end_to_end_item_accuracy": 0.7333333333333333,
        "conditional_item_accuracy": 0.8918918918918919,
        "end_to_end_pair_accuracy": 0.5333333333333333,
        "conditional_pair_accuracy": 0.75,
    }
    expected_flash = {
        "parseable_items": 146,
        "correct_items": 90,
        "covered_pairs": 61,
        "correct_pairs": 13,
        "end_to_end_item_accuracy": 0.5,
        "conditional_item_accuracy": 0.6164383561643836,
        "end_to_end_pair_accuracy": 0.14444444444444443,
        "conditional_pair_accuracy": 0.21311475409836064,
        "macro_f1": 0.39275710284113646,
        "conditional_macro_f1": 0.46822747216138244,
    }
    for label, observed, expected in (
        ("Qwen", qwen, expected_qwen),
        ("Flash", flash, expected_flash),
    ):
        for key, value in expected.items():
            if not equivalent_json(observed.get(key), value):
                fail(f"balanced challenge {label} metric changed: {key}")
    validation = receipt.get("validation", {})
    if (
        receipt.get("source_artifact_or_workflow_ids_included") is not False
        or validation.get("terminal_records_validated") != 360
        or validation.get("provider_account_identifier_findings") != 0
        or validation.get("retained_provider_response_ids") != 0
        or validation.get("hidden_reasoning_field_findings") != 0
    ):
        fail("balanced challenge privacy receipt changed")
    if (
        aggregate.get("design") != "PUBLIC_PRECOMMITTED_BALANCED_CHALLENGE"
        or aggregate.get("service_comparison", {}).get("causal_model_ablation_claimed") is not False
        or aggregate.get("deterministic_policy_executor", {}).get("label")
        != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    ):
        fail("balanced challenge interpretation boundary changed")
    return {
        "items_per_lane": 180,
        "pairs_per_lane": 90,
        "qwen_valid_decisions": qwen["parseable_items"],
        "qwen_end_to_end_item_accuracy": qwen["end_to_end_item_accuracy"],
        "qwen_end_to_end_pair_accuracy": qwen["end_to_end_pair_accuracy"],
        "flash_valid_decisions": flash["parseable_items"],
        "flash_end_to_end_item_accuracy": flash["end_to_end_item_accuracy"],
        "flash_end_to_end_pair_accuracy": flash["end_to_end_pair_accuracy"],
        "privacy_status": receipt["status"],
    }


def changed_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix or "/"]
    if isinstance(left, dict):
        if set(left) != set(right):
            return [prefix or "/"]
        paths: list[str] = []
        for key in left:
            paths.extend(changed_paths(left[key], right[key], f"{prefix}/{key}"))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [prefix or "/"]
        paths = []
        for index, (left_value, right_value) in enumerate(zip(left, right, strict=True)):
            paths.extend(changed_paths(left_value, right_value, f"{prefix}/{index}"))
        return paths
    return [] if left == right else [prefix or "/"]


def baseline_records(predictions: list[Json]) -> list[Json]:
    return [
        {
            "item_id": row["item_id"],
            "pair_id": row["pair_id"],
            "parse_status": "OK",
            "raw_decision": {"action": row["predicted_action"]},
        }
        for row in predictions
    ]


def validate_synthetic_policy_evidence(study_kind: str) -> Json:
    specifications = {
        "SLSA_DERIVED_POLICY_PORTABILITY": {
            "directory": "slsa-portability",
            "aggregate_design": "PROSPECTIVELY_FROZEN_SECOND_POLICY_PORTABILITY_STUDY",
            "plan_status": "FROZEN_BEFORE_SCORED_INFERENCE",
            "baseline_files": {"structured": "predictions.jsonl"},
            "aggregate_baseline_key": "structured_random_forest_action_baseline",
            "controlled_path": "evidence_field",
            "run_schema": "stronger-model-run-record.schema.json",
        },
        "COUNTERFACTUAL_POLICY_PROFILE_SWITCH": {
            "directory": "policy-switch",
            "aggregate_design": "PROSPECTIVELY_FROZEN_COUNTERFACTUAL_POLICY_PROFILE_STUDY",
            "plan_status": "FROZEN_BEFORE_SCORED_INFERENCE",
            "baseline_files": {
                "policy_aware": "policy_aware-predictions.jsonl",
                "profile_blind": "profile_blind-predictions.jsonl",
            },
            "aggregate_baseline_key": "structured_random_forest_comparators",
            "controlled_path": "active_profile",
            "run_schema": "stronger-model-run-record.schema.json",
        },
        "LOCAL_MODEL_SLSA_POLICY_REPLICATION": {
            "directory": "local-model-replications/slsa",
            "aggregate_design": (
                "LOCAL_MODEL_REPLICATION_REPLACEMENT_V2_OF_FROZEN_SLSA_POLICY_STUDY"
            ),
            "plan_status": "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION_REPLACEMENT_V2",
            "baseline_files": {"structured": "predictions.jsonl"},
            "aggregate_baseline_key": "structured_random_forest_action_baseline",
            "controlled_path": "evidence_field",
            "run_schema": "local-model-run-record.schema.json",
            "replacement_version": 2,
        },
        "LOCAL_MODEL_POLICY_SWITCH_REPLICATION": {
            "directory": "local-model-replications/policy-switch",
            "aggregate_design": (
                "LOCAL_MODEL_REPLICATION_REPLACEMENT_V2_OF_FROZEN_POLICY_SWITCH_STUDY"
            ),
            "plan_status": "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION_REPLACEMENT_V2",
            "baseline_files": {
                "policy_aware": "policy_aware-predictions.jsonl",
                "profile_blind": "profile_blind-predictions.jsonl",
            },
            "aggregate_baseline_key": "structured_random_forest_comparators",
            "controlled_path": "active_profile",
            "run_schema": "local-model-run-record.schema.json",
            "replacement_version": 2,
        },
        "LOCAL_MODEL_POLICY_TRANSITION_GRAPH_REPLICATION": {
            "directory": "local-model-replications/policy-transition-graph",
            "aggregate_design": (
                "LOCAL_MODEL_EVALUATION_OF_FROZEN_REACHABLE_POLICY_TRANSITION_GRAPH"
            ),
            "plan_status": "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION_REPLACEMENT_V2",
            "baseline_files": {
                "policy_aware": "policy_aware-predictions.jsonl",
                "profile_blind": "profile_blind-predictions.jsonl",
            },
            "aggregate_baseline_key": "structured_random_forest_comparators",
            "controlled_path": "active_profile",
            "run_schema": "local-model-run-record.schema.json",
            "replacement_version": 2,
            "action_support": {"ALLOW": 36, "HOLD": 24, "DEMOTE": 24, "ESCALATE": 36},
            "factor_count": 10,
            "pair_requires_allow": False,
            "transition_graph": True,
            "baseline_correct": {
                "policy_aware": {"items": 107, "pairs": 47},
                "profile_blind": {"items": 57, "pairs": 0},
            },
        },
    }
    specification = specifications[study_kind]
    root = EVIDENCE / str(specification["directory"])
    manifest = load_json(root / "MANIFEST.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        fail(f"{study_kind}: manifest is malformed")
    manifest_payload = deepcopy(manifest)
    observed_manifest_sha = manifest_payload.pop("manifest_sha256", None)
    if observed_manifest_sha != sha256_text(canonical_json(manifest_payload)):
        fail(f"{study_kind}: manifest self-digest changed")
    actual_files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != root / "MANIFEST.json"
    }
    if manifest.get("file_count") != len(actual_files) or manifest.get("files") != actual_files:
        fail(f"{study_kind}: manifest differs from the generated tree")
    if manifest.get("study_kind") != study_kind or manifest.get("status") != (
        "ANONYMOUS_SYNTHETIC_POLICY_EVIDENCE"
    ):
        fail(f"{study_kind}: manifest identity changed")
    expected_scope = {
        "credentials_included": False,
        "hidden_reasoning_included": False,
        "provider_response_identifiers_included": False,
        "source_repository_or_commit_identity_included": False,
        "raw_final_response_text_included": False,
        "item_level_structured_decisions_included": True,
        "all_scheduled_terminal_failures_included": True,
    }
    if manifest.get("scope") != expected_scope:
        fail(f"{study_kind}: anonymous scope changed")

    dataset = root / "dataset"
    items = load_jsonl(dataset / "evaluation-items.jsonl")
    gold = load_jsonl(dataset / "evaluation-gold.jsonl")
    pairs = load_json(dataset / "evaluation-pairs.json")
    packet = load_json(dataset / "evaluation-prompt-packet.json")
    dataset_manifest = load_json(dataset / "manifest.json")
    plan = load_json(root / "study-plan.json")
    schedule = load_json(root / "request-schedule.json")
    aggregate = load_json(root / "reported-aggregate.json")
    receipt = load_json(root / "execution-receipt.json")
    if not all(
        isinstance(value, dict)
        for value in (packet, dataset_manifest, plan, schedule, aggregate, receipt)
    ):
        fail(f"{study_kind}: plan, packet, schedule, aggregate, or receipt is malformed")
    if not isinstance(pairs, list):
        fail(f"{study_kind}: evaluation pairs are malformed")
    item_by_id = {str(row["id"]): row for row in items}
    gold_by_id = {str(row["id"]): row for row in gold}
    if len(items) != 120 or len(item_by_id) != 120 or set(item_by_id) != set(gold_by_id):
        fail(f"{study_kind}: evaluation item coverage changed")
    expected_action_support = Counter(
        specification.get(
            "action_support",
            {"ALLOW": 60, "HOLD": 20, "DEMOTE": 20, "ESCALATE": 20},
        )
    )
    if Counter(str(row["decision"]["action"]) for row in gold) != expected_action_support:
        fail(f"{study_kind}: gold action support changed")
    seen_member_ids: set[str] = set()
    factor_ids: set[str] = set()
    for pair in pairs:
        ids = [str(value) for value in pair.get("member_ids", [])]
        if len(ids) != 2 or len(set(ids)) != 2 or set(ids) - set(item_by_id):
            fail(f"{study_kind}: pair membership changed")
        if seen_member_ids & set(ids):
            fail(f"{study_kind}: an item appears in multiple pairs")
        seen_member_ids.update(ids)
        factor_ids.add(str(pair.get("factor_id")))
        left = item_by_id[ids[0]]["model_visible"]
        right = item_by_id[ids[1]]["model_visible"]
        paths = changed_paths(left, right)
        if specification["controlled_path"] == "active_profile":
            if paths != ["/active_policy_profile"]:
                fail(f"{study_kind}: a pair changes more than the active policy profile")
        elif len(paths) != 1 or not paths[0].startswith("/evidence/0/observed/"):
            fail(f"{study_kind}: a pair changes more than one verifier field")
        pair_actions = {str(gold_by_id[item_id]["decision"]["action"]) for item_id in ids}
        if len(pair_actions) != 2 or (
            specification.get("pair_requires_allow", True) and "ALLOW" not in pair_actions
        ):
            fail(f"{study_kind}: pair actions no longer define an action-changing contrast")
    if (
        len(pairs) != 60
        or seen_member_ids != set(item_by_id)
        or len(factor_ids) != int(specification.get("factor_count", 12))
    ):
        fail(f"{study_kind}: pair or factor coverage changed")
    if specification["controlled_path"] == "active_profile" and Counter(
        str(row["model_visible"]["active_policy_profile"]) for row in items
    ) != Counter({"POLICY_BLUE": 60, "POLICY_AMBER": 60}):
        fail(f"{study_kind}: policy-profile support changed")
    if specification.get("transition_graph") is True:
        transition_counts = Counter(str(pair.get("blue_to_amber_transition")) for pair in pairs)
        expected_transitions = {
            "ALLOW->HOLD",
            "ALLOW->DEMOTE",
            "ALLOW->ESCALATE",
            "HOLD->ALLOW",
            "HOLD->ESCALATE",
            "DEMOTE->ALLOW",
            "DEMOTE->ESCALATE",
            "ESCALATE->ALLOW",
            "ESCALATE->HOLD",
            "ESCALATE->DEMOTE",
        }
        profile_support: dict[str, Counter[str]] = {
            "POLICY_BLUE": Counter(),
            "POLICY_AMBER": Counter(),
        }
        for item_id, item in item_by_id.items():
            profile = str(item["model_visible"]["active_policy_profile"])
            profile_support[profile][str(gold_by_id[item_id]["decision"]["action"])] += 1
        coverage = load_json(root / "transition-coverage.json")
        if not isinstance(coverage, dict):
            fail(f"{study_kind}: transition-coverage receipt is malformed")
        validate_self_digest(coverage, "self_digest", f"{study_kind} transition coverage")
        expected_bindings = {
            "manifest_sha256": sha256_file(dataset / "manifest.json"),
            "evaluation_items_sha256": sha256_file(dataset / "evaluation-items.jsonl"),
            "evaluation_gold_sha256": sha256_file(dataset / "evaluation-gold.jsonl"),
            "evaluation_pairs_sha256": sha256_file(dataset / "evaluation-pairs.json"),
            "base_policy_sha256": sha256_file(root / "base-policy-contract.json"),
            "switch_policy_sha256": sha256_file(root / "policy-contract.json"),
        }
        expected_profile_support = Counter({"ALLOW": 18, "HOLD": 12, "DEMOTE": 12, "ESCALATE": 18})
        if (
            transition_counts != Counter({transition: 6 for transition in expected_transitions})
            or coverage.get("status") != "POLICY_TRANSITION_GRAPH_COVERAGE_COMPLETE"
            or coverage.get("directed_nonself_action_transitions_possible") != 12
            or coverage.get("directed_action_transitions_semantically_reachable") != 10
            or coverage.get("directed_action_transitions_covered") != 10
            or coverage.get("structurally_unreachable_transitions")
            != ["HOLD->DEMOTE", "DEMOTE->HOLD"]
            or coverage.get("authored_profile_difference_rules_covered") != 12
            or coverage.get("authored_profile_difference_rules_total") != 12
            or coverage.get("source_bindings") != expected_bindings
            or any(value != expected_profile_support for value in profile_support.values())
            or {
                profile: Counter(actions)
                for profile, actions in coverage.get("profile_action_support", {}).items()
            }
            != profile_support
        ):
            fail(f"{study_kind}: reachable transition-graph coverage changed")
        decision = load_json(root / "design-decision-receipt.json")
        if not isinstance(decision, dict):
            fail(f"{study_kind}: design-decision receipt is malformed")
        validate_self_digest(decision, "self_digest", f"{study_kind} design decision")
        if (
            decision.get("status") != "PREINFERENCE_POLICY_TRANSITION_GRAPH_DESIGN_DECISION"
            or decision.get("outcomes_used_to_choose_edges_or_contexts") is not False
            or decision.get("transition_graph_model_calls_before_freeze") != 0
            or decision.get("evaluation_gold_used_to_train_comparators") is not False
            or decision.get("dataset_manifest_sha256") != sha256_file(dataset / "manifest.json")
            or decision.get("transition_coverage_sha256")
            != sha256_file(root / "transition-coverage.json")
            or decision.get("baseline_report_sha256")
            != sha256_file(root / "baseline" / "report.json")
            or decision.get("baseline_prediction_sha256")
            != {
                name: sha256_file(root / "baseline" / name)
                for name in (
                    "policy_aware-predictions.jsonl",
                    "profile_blind-predictions.jsonl",
                )
            }
        ):
            fail(f"{study_kind}: preinference transition-graph decision changed")

    packet_rows = packet.get("records")
    if not isinstance(packet_rows, list) or {str(row.get("item_id")) for row in packet_rows} != set(
        item_by_id
    ):
        fail(f"{study_kind}: prompt-packet coverage changed")
    packet_payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if (
        packet.get("packet_sha256") != sha256_text(canonical_json(packet_payload))
        or dataset_manifest.get("packet_sha256") != packet.get("packet_sha256")
        or dataset_manifest.get("packet_file_sha256")
        != sha256_file(dataset / "evaluation-prompt-packet.json")
    ):
        fail(f"{study_kind}: anonymous prompt-packet binding changed")
    for row in packet_rows:
        prompt = str(row.get("prompt"))
        if (
            row.get("prompt_sha256") != sha256_text(prompt)
            or row.get("utf8_bytes") != len(prompt.encode("utf-8"))
            or "github.com/f0909172434" in prompt
            or "anonymous.invalid/repository" not in prompt
        ):
            fail(f"{study_kind}: anonymous prompt projection changed: {row.get('item_id')}")
    lane_files = manifest.get("lane_files")
    expected_lanes = {str(row["lane_id"]) for row in plan.get("formal_lanes", [])}
    if (
        not isinstance(lane_files, dict)
        or set(lane_files) != expected_lanes
        or len(expected_lanes) != 2
    ):
        fail(f"{study_kind}: lane manifest changed")
    cells = schedule.get("cells")
    projection = plan.get("anonymous_projection")
    if (
        plan.get("status") != specification["plan_status"]
        or plan.get("execution", {}).get("client_retry_count") != 0
        or plan.get("execution", {}).get("schedule_sha256") != schedule.get("schedule_sha256")
        or not isinstance(projection, dict)
        or projection.get("scientific_prompt_content_changed") is not False
        or projection.get("schema_identifier_redacted") is not True
        or projection.get("source_request_body_digests_included") is not False
        or projection.get("redacted_prompts") != 120
        or not isinstance(cells, list)
        or len(cells) != 240
        or len({str(cell["cell_id"]) for cell in cells}) != 240
    ):
        fail(f"{study_kind}: frozen execution boundary changed")
    replacement_version = specification.get("replacement_version")
    if replacement_version is not None and (
        plan.get("replacement_version") != replacement_version
        or plan.get("freeze", {}).get("prior_ineligible_application_invocations") != 1
        or plan.get("freeze", {}).get("prior_durable_terminal_records") != 0
        or plan.get("freeze", {}).get("prior_retained_model_outputs") != 0
        or plan.get("freeze", {}).get("eligible_replacement_inference_calls_before_freeze") != 0
    ):
        fail(f"{study_kind}: replacement-v2 exclusion boundary changed")
    validate_self_digest(schedule, "schedule_sha256", f"{study_kind} schedule")
    packet_hashes = {str(row["item_id"]): str(row["prompt_sha256"]) for row in packet_rows}
    projected_requests: dict[str, str] = {}
    for cell in cells:
        lane_id = str(cell.get("lane_id"))
        item_id = str(cell.get("item_id"))
        expected_request = sha256_text(
            canonical_json(
                {
                    "anonymous_projection_version": "1.0.0-review",
                    "item_id": item_id,
                    "lane_id": lane_id,
                    "prompt_sha256": packet_hashes.get(item_id),
                }
            )
        )
        if (
            cell.get("prompt_sha256") != packet_hashes.get(item_id)
            or cell.get("request_body_sha256") != expected_request
            or cell.get("request_digest_scope") != "ANONYMOUS_LANE_ITEM_PROMPT_PROJECTION"
        ):
            fail(f"{study_kind}: anonymous request projection changed: {lane_id}/{item_id}")
        projected_requests[f"{lane_id}\0{item_id}"] = expected_request
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("planned_cells") != 240
        or receipt.get("durable_request_intents") != 240
        or receipt.get("durable_terminal_records") != 240
        or receipt.get("application_posts_per_cell") != 1
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("credentials_retained") is not False
        or receipt.get("provider_response_identifiers_retained") is not False
        or receipt.get("hidden_reasoning_blocks_retained") is not False
        or receipt.get("source_journal_digests_included") is not False
        or receipt.get("schedule_sha256") != schedule.get("schedule_sha256")
    ):
        fail(f"{study_kind}: execution receipt changed")
    if replacement_version is not None and (
        receipt.get("replacement_version") != replacement_version
        or receipt.get("prior_ineligible_application_invocations") != 1
        or receipt.get("void_attempt_receipt_sha256")
        != sha256_file(root.parent / "initial-void-exclusion.json")
    ):
        fail(f"{study_kind}: replacement execution boundary changed")

    aggregate_lanes = {
        str(row.get("lane_id")): row for row in aggregate.get("lanes", []) if isinstance(row, dict)
    }
    aggregate_freeze = aggregate.get("freeze")
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("design") != specification["aggregate_design"]
        or set(aggregate_lanes) != expected_lanes
        or not isinstance(aggregate_freeze, dict)
        or aggregate_freeze.get("plan_sha256") != sha256_file(root / "study-plan.json")
        or aggregate_freeze.get("schedule_sha256") != schedule.get("schedule_sha256")
        or aggregate_freeze.get("dataset_manifest_sha256") != sha256_file(dataset / "manifest.json")
        or aggregate_freeze.get("packet_sha256") != packet.get("packet_sha256")
        or aggregate_freeze.get("execution_receipt_sha256")
        != sha256_file(root / "execution-receipt.json")
        or aggregate.get("deterministic_policy_executor", {}).get("label")
        != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_BASELINE"
    ):
        fail(f"{study_kind}: aggregate interpretation boundary changed")
    if replacement_version is not None and aggregate_freeze.get(
        "void_attempt_receipt_sha256"
    ) != sha256_file(root.parent / "initial-void-exclusion.json"):
        fail(f"{study_kind}: aggregate void-attempt binding changed")
    lane_metrics: Json = {}
    for lane_id in sorted(expected_lanes):
        run_path = root / str(lane_files[lane_id])
        rows = load_jsonl(run_path)
        if (
            len(rows) != 120
            or {str(row.get("item_id")) for row in rows} != set(item_by_id)
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
        ):
            fail(f"{study_kind}: run coverage changed for {lane_id}")
        validate_raw_response_hashes(rows, f"{study_kind} {lane_id}")
        validate_prompt_binding(
            rows, dataset / "evaluation-prompt-packet.json", f"{study_kind} {lane_id}"
        )
        for row in rows:
            validate_with_schema(
                row,
                ROOT / "v2" / "schemas" / str(specification["run_schema"]),
                str(row.get("item_id")),
            )
            reject_hidden_reasoning(row, f"{study_kind} {lane_id}")
            if (
                row.get("provider_response_id") is not None
                or row.get("raw_response_text") is not None
                or row.get("raw_response_sha256") is not None
                or row.get("parse_error_detail") is not None
                or row.get("transport_error") is not None
                or row.get("frozen_plan_commit") != "0000000000000000000000000000000000000010"
                or row.get("packet_sha256") != packet.get("packet_sha256")
                or row.get("dataset_manifest_sha256") != sha256_file(dataset / "manifest.json")
                or row.get("request_sha256")
                != projected_requests[f"{lane_id}\0{row.get('item_id')}"]
            ):
                fail(f"{study_kind}: private response or provenance fields survived")
        metrics = derive_balanced_metrics(gold, pairs, rows)
        if not equivalent_json(metrics, aggregate_lanes[lane_id].get("metrics")):
            fail(f"{study_kind}: aggregate differs from item-level records for {lane_id}")
        if aggregate_lanes[lane_id].get("run_sha256") != sha256_file(run_path):
            fail(f"{study_kind}: aggregate run digest changed for {lane_id}")
        if receipt.get("lane_output_sha256", {}).get(run_path.name) != sha256_file(run_path):
            fail(f"{study_kind}: execution receipt run digest changed for {lane_id}")
        lane_metrics[lane_id] = metrics

    baseline_report = load_json(root / "baseline" / "report.json")
    if (
        not isinstance(baseline_report, dict)
        or baseline_report.get("evaluation_gold_loaded") is not False
        or baseline_report.get("model_outputs_loaded") is not False
    ):
        fail(f"{study_kind}: baseline data-access boundary changed")
    baseline_key = str(specification["aggregate_baseline_key"])
    aggregate_baselines = aggregate.get(baseline_key)
    baseline_files = specification["baseline_files"]
    if not isinstance(baseline_files, dict):
        fail(f"{study_kind}: internal baseline specification is malformed")
    if baseline_key == "structured_random_forest_action_baseline":
        aggregate_baselines = {"structured": aggregate_baselines}
    if not isinstance(aggregate_baselines, dict) or set(aggregate_baselines) != set(baseline_files):
        fail(f"{study_kind}: aggregate baseline set changed")
    baseline_metrics: Json = {}
    for comparator_id, filename in baseline_files.items():
        predictions = load_jsonl(root / "baseline" / str(filename))
        metrics = derive_balanced_metrics(gold, pairs, baseline_records(predictions))
        entry = aggregate_baselines[comparator_id]
        if not isinstance(entry, dict) or not equivalent_json(metrics, entry.get("metrics")):
            fail(f"{study_kind}: baseline aggregate changed for {comparator_id}")
        baseline_metrics[comparator_id] = metrics
    if specification["controlled_path"] == "active_profile":
        aware = baseline_metrics["policy_aware"]
        blind = baseline_metrics["profile_blind"]
        expected_correct = specification.get(
            "baseline_correct",
            {
                "policy_aware": {"items": 120, "pairs": 60},
                "profile_blind": {"items": 60, "pairs": 0},
            },
        )
        if (
            aware.get("correct_items") != expected_correct["policy_aware"]["items"]
            or aware.get("correct_pairs") != expected_correct["policy_aware"]["pairs"]
            or blind.get("correct_items") != expected_correct["profile_blind"]["items"]
            or blind.get("correct_pairs") != expected_correct["profile_blind"]["pairs"]
        ):
            fail(f"{study_kind}: registered shortcut comparator result changed")

    failure = load_json(root / "failure-taxonomy.json")
    privacy = load_json(root / "privacy-receipt-review.json")
    result_receipt = load_json(root / "result-receipt-review.json")
    if not all(isinstance(value, dict) for value in (failure, privacy, result_receipt)):
        fail(f"{study_kind}: review receipt chain is malformed")
    validate_self_digest(failure, "self_digest", f"{study_kind} failure taxonomy")
    validate_self_digest(privacy, "self_digest", f"{study_kind} privacy receipt")
    validate_self_digest(result_receipt, "self_digest", f"{study_kind} result receipt")
    failure_lanes = failure.get("lanes")
    if (
        failure.get("status") != "COMPLETE_FROZEN_FAILURE_TAXONOMY"
        or failure.get("free_form_error_text_included") is not False
        or not isinstance(failure_lanes, dict)
        or set(failure_lanes) != expected_lanes
    ):
        fail(f"{study_kind}: failure taxonomy boundary changed")
    for lane_id, metrics in lane_metrics.items():
        lane_failure = failure_lanes[lane_id]
        if (
            lane_failure.get("terminal_records") != 120
            or lane_failure.get("parse_status_counts") != metrics.get("parse_status_counts")
            or sum(lane_failure.get("transport_failure_categories", {}).values())
            != metrics.get("parse_status_counts", {}).get("TRANSPORT_ERROR", 0)
        ):
            fail(f"{study_kind}: failure taxonomy counts changed for {lane_id}")
    expected_review_files = {
        "execution-receipt.json": sha256_file(root / "execution-receipt.json"),
        "failure-taxonomy.json": sha256_file(root / "failure-taxonomy.json"),
        "reported-aggregate.json": sha256_file(root / "reported-aggregate.json"),
        **{str(relative): sha256_file(root / str(relative)) for relative in lane_files.values()},
    }
    if (
        privacy.get("status") != "ANONYMOUS_SYNTHETIC_POLICY_DERIVATIVE_VALIDATED"
        or privacy.get("terminal_records_validated") != 240
        or privacy.get("credentials_included") is not False
        or privacy.get("provider_response_identifiers_included") is not False
        or privacy.get("hidden_reasoning_fields_included") is not False
        or privacy.get("raw_final_response_text_included") is not False
        or privacy.get("free_form_error_text_included") is not False
        or privacy.get("all_scheduled_terminal_failures_included") is not True
        or privacy.get("review_file_sha256") != dict(sorted(expected_review_files.items()))
    ):
        fail(f"{study_kind}: privacy receipt boundary changed")
    expected_result_hashes = {
        "plan_sha256": sha256_file(root / "study-plan.json"),
        "schedule_sha256": sha256_file(root / "request-schedule.json"),
        "dataset_manifest_sha256": sha256_file(dataset / "manifest.json"),
        "baseline_report_sha256": sha256_file(root / "baseline" / "report.json"),
        "execution_receipt_sha256": sha256_file(root / "execution-receipt.json"),
        "aggregate_sha256": sha256_file(root / "reported-aggregate.json"),
        "failure_taxonomy_sha256": sha256_file(root / "failure-taxonomy.json"),
        "privacy_receipt_sha256": sha256_file(root / "privacy-receipt-review.json"),
    }
    if (
        result_receipt.get("status") != "ANONYMOUS_SYNTHETIC_POLICY_RESULTS_SEALED"
        or result_receipt.get("planned_and_terminal_cells") != 240
        or result_receipt.get("application_posts_per_cell") != 1
        or result_receipt.get("client_retry_count") != 0
        or result_receipt.get("all_failures_retained_in_end_to_end_denominator") is not True
        or any(result_receipt.get(key) != value for key, value in expected_result_hashes.items())
        or result_receipt.get("run_sha256")
        != {
            Path(str(relative)).name: sha256_file(root / str(relative))
            for relative in lane_files.values()
        }
    ):
        fail(f"{study_kind}: result receipt chain changed")

    return {
        "study_kind": study_kind,
        "items_per_lane": 120,
        "pairs_per_lane": 60,
        "terminal_records": 240,
        "lane_metrics": lane_metrics,
        "baseline_metrics": baseline_metrics,
    }


def validate_slsa_portability() -> Json:
    return validate_synthetic_policy_evidence("SLSA_DERIVED_POLICY_PORTABILITY")


def validate_policy_switch() -> Json:
    return validate_synthetic_policy_evidence("COUNTERFACTUAL_POLICY_PROFILE_SWITCH")


def validate_local_model_replications() -> Json:
    root = EVIDENCE / "local-model-replications"
    manifest = load_json(root / "MANIFEST.json")
    catalog = load_json(root / "model-catalog.json")
    snapshot = load_json(root / "model-snapshot-receipt.json")
    qualification = load_json(root / "environment-qualification.json")
    void_receipt = load_json(root / "initial-void-exclusion.json")
    if not all(
        isinstance(value, dict)
        for value in (manifest, catalog, snapshot, qualification, void_receipt)
    ):
        fail("local-model replication metadata is malformed")
    manifest_payload = deepcopy(manifest)
    observed_manifest_sha = manifest_payload.pop("manifest_sha256", None)
    actual_files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != root / "MANIFEST.json"
    }
    if (
        observed_manifest_sha != sha256_text(canonical_json(manifest_payload))
        or manifest.get("status") != "ANONYMOUS_LOCAL_MODEL_REPLICATIONS"
        or manifest.get("file_count") != len(actual_files)
        or manifest.get("files") != actual_files
        or manifest.get("studies") != ["policy-switch", "policy-transition-graph", "slsa"]
        or manifest.get("model_weights_included") is not False
        or manifest.get("exact_model_revisions_included") is not True
        or manifest.get("snapshot_file_digests_included") is not True
        or manifest.get("raw_generation_text_included") is not False
        or manifest.get("hidden_reasoning_included") is not False
        or manifest.get("credentials_included") is not False
        or manifest.get("initial_void_attempt_excluded_in_full") is not True
    ):
        fail("local-model replication manifest changed")
    lanes = catalog.get("lanes")
    if (
        catalog.get("status") != "PREINFERENCE_LOCAL_MODEL_CATALOG"
        or not isinstance(lanes, list)
        or len(lanes) != 2
        or len({str(row.get("model_family")) for row in lanes}) != 2
        or any(not re.fullmatch(r"[0-9a-f]{40}", str(row.get("model_revision"))) for row in lanes)
        or catalog.get("selection_boundary", {}).get(
            "models_selected_before_any_benchmark_inference"
        )
        is not True
        or catalog.get("selection_boundary", {}).get("benchmark_accuracy_or_labels_consulted")
        is not False
    ):
        fail("local-model pre-inference catalog changed")
    validate_self_digest(snapshot, "self_digest", "local-model snapshot receipt")
    validate_self_digest(qualification, "self_digest", "local-model qualification receipt")
    validate_self_digest(void_receipt, "self_digest", "local-model void-attempt receipt")
    catalog_hash = sha256_file(root / "model-catalog.json")
    if (
        snapshot.get("status") != "PINNED_LOCAL_MODEL_SNAPSHOTS_VALIDATED"
        or snapshot.get("catalog_sha256") != catalog_hash
        or qualification.get("status")
        != "LOCAL_MODEL_ENVIRONMENT_QUALIFIED_BEFORE_BENCHMARK_INFERENCE"
        or qualification.get("catalog_sha256") != catalog_hash
        or qualification.get("snapshot_receipt_self_digest") != snapshot.get("self_digest")
        or qualification.get("benchmark_inference_calls") != 0
        or qualification.get("credentials_used_or_retained") is not False
    ):
        fail("local-model environment qualification changed")
    if (
        void_receipt.get("status") != "INELIGIBLE_LOCAL_ATTEMPT_PRE_TERMINAL_SCHEMA_REJECTION"
        or void_receipt.get("observed_counts", {}).get("application_invocations") != 1
        or void_receipt.get("observed_counts", {}).get("durable_terminal_records") != 0
        or void_receipt.get("observed_counts", {}).get("retained_model_outputs") != 0
        or void_receipt.get("source_bindings_included") is not False
        or void_receipt.get("raw_generation_text_included") is not False
        or void_receipt.get("model_outcome_included") is not False
    ):
        fail("local-model initial void-attempt boundary changed")
    snapshots = snapshot.get("snapshots")
    qualified_models = qualification.get("models")
    if (
        not isinstance(snapshots, list)
        or not isinstance(qualified_models, list)
        or len(snapshots) != 2
        or len(qualified_models) != 2
        or any(row.get("load_and_generation_succeeded") is not True for row in qualified_models)
        or any(row.get("stream_generation_api_succeeded") is not True for row in qualified_models)
    ):
        fail("local-model snapshot or smoke-test coverage changed")
    catalog_models = {(str(row["model_repo"]), str(row["model_revision"])) for row in lanes}
    if {
        (str(row.get("model_repo")), str(row.get("model_revision"))) for row in snapshots
    } != catalog_models or {
        (str(row.get("model_repo")), str(row.get("model_revision"))) for row in qualified_models
    } != catalog_models:
        fail("local-model metadata model sets differ")
    for row in snapshots:
        payload = {key: child for key, child in row.items() if key != "snapshot_digest"}
        if (
            row.get("snapshot_digest") != sha256_text(canonical_json(payload))
            or not isinstance(row.get("files"), list)
            or row.get("file_count") != len(row["files"])
        ):
            fail(f"local-model snapshot tree changed: {row.get('model_repo')}")

    slsa = validate_synthetic_policy_evidence("LOCAL_MODEL_SLSA_POLICY_REPLICATION")
    policy_switch = validate_synthetic_policy_evidence("LOCAL_MODEL_POLICY_SWITCH_REPLICATION")
    transition_graph = validate_synthetic_policy_evidence(
        "LOCAL_MODEL_POLICY_TRANSITION_GRAPH_REPLICATION"
    )
    expected_bindings = {
        "catalog_sha256": catalog_hash,
        "requirements_sha256": sha256_file(root / "requirements.txt"),
        "snapshot_receipt_sha256": sha256_file(root / "model-snapshot-receipt.json"),
        "snapshot_receipt_self_digest": snapshot["self_digest"],
        "qualification_receipt_sha256": sha256_file(root / "environment-qualification.json"),
        "qualification_receipt_self_digest": qualification["self_digest"],
        "void_attempt_receipt_sha256": sha256_file(root / "initial-void-exclusion.json"),
        "void_attempt_receipt_self_digest": void_receipt["self_digest"],
    }
    for dataset_key in ("slsa", "policy-switch", "policy-transition-graph"):
        plan = load_json(root / dataset_key / "study-plan.json")
        if not isinstance(plan, dict) or any(
            plan.get("freeze", {}).get(key) != value for key, value in expected_bindings.items()
        ):
            fail(f"local-model plan environment binding changed: {dataset_key}")
        planned_models = {
            (str(row.get("model")), str(row.get("model_revision")))
            for row in plan.get("formal_lanes", [])
        }
        if planned_models != catalog_models:
            fail(f"local-model plan model set changed: {dataset_key}")
    return {
        "studies": 3,
        "models": len(catalog_models),
        "terminal_records": 720,
        "slsa": slsa,
        "policy_switch": policy_switch,
        "policy_transition_graph": transition_graph,
    }


def validate_hosted_exclusion_receipts() -> Json:
    paths = {
        "initial_policy_switch": EVIDENCE / "hosted-policy-switch-exclusion.json",
        "policy_switch_replacement": EVIDENCE / "hosted-policy-switch-replacement-exclusion.json",
        "policy_transition_graph": EVIDENCE / "hosted-policy-transition-graph-exclusion.json",
    }
    receipts = {name: load_json(path) for name, path in paths.items()}
    if any(not isinstance(receipt, dict) for receipt in receipts.values()):
        fail("hosted exclusion receipt is malformed")
    for name, receipt in receipts.items():
        validate_self_digest(receipt, "self_digest", f"hosted exclusion {name}")
        if (
            receipt.get("source_identity") != "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
            or receipt.get("source_bindings_included") is not False
            or receipt.get("raw_terminal_records_included") is not False
            or receipt.get("valid_output_subset_included") is not False
            or receipt.get("new_model_calls_performed_for_receipt") != 0
        ):
            fail(f"hosted exclusion privacy or selection boundary changed: {name}")

    initial = receipts["initial_policy_switch"]
    if (
        initial.get("status") != "HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION"
        or initial.get("decision", {}).get("hosted_model_rows_enter_manuscript") is not False
        or initial.get("decision", {}).get("successful_row_subset_selected") is not False
    ):
        fail("initial hosted policy-switch exclusion changed")

    expected_status = {
        "policy_switch_replacement": (
            "HOSTED_REPLACEMENT_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
        ),
        "policy_transition_graph": (
            "HOSTED_TRANSITION_GRAPH_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
        ),
    }
    for name in ("policy_switch_replacement", "policy_transition_graph"):
        receipt = receipts[name]
        classification = receipt.get("classification", {})
        decision = receipt.get("decision", {})
        if (
            receipt.get("status") != expected_status[name]
            or receipt.get("free_form_error_text_included") is not False
            or classification.get("eligible_for_model_efficacy_reporting") is not False
            or classification.get("explicit_resource_exhaustion_errors") != 240
            or classification.get("persistent_exhaustion_trigger_sequence") != 0
            or classification.get("transport_status_counts") != {"ERROR": 240}
            or classification.get("parse_status_counts") != {"TRANSPORT_ERROR": 240}
            or decision.get("all_240_terminal_outcomes_considered") is not True
            or decision.get("hosted_model_rows_enter_manuscript") is not False
            or decision.get("conditional_success_subset_selected") is not False
        ):
            fail(f"complete hosted exclusion changed: {name}")
    graph = receipts["policy_transition_graph"]
    if (
        graph.get("study_scope") != "REACHABLE_POLICY_TRANSITION_GRAPH"
        or graph.get("model_configuration_labels_included") is not False
    ):
        fail("hosted transition-graph exclusion scope changed")
    return {
        "status": "HOSTED_EXCLUSION_RECEIPTS_PASS",
        "receipt_count": len(receipts),
        "raw_terminal_records_included": False,
        "model_rows_included": False,
        "successful_subsets_selected": False,
    }


def validate_public_model_breadth() -> Json:
    root = EVIDENCE / "public-model-breadth"
    manifest = load_json(root / "MANIFEST.json")
    receipt = load_json(root / "privacy-receipt-review.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        fail("public model-breadth manifest is malformed")
    if not isinstance(receipt, dict):
        fail("public model-breadth privacy receipt is malformed")

    manifest_payload = deepcopy(manifest)
    observed_manifest_sha = manifest_payload.pop("manifest_sha256", None)
    if observed_manifest_sha != sha256_text(canonical_json(manifest_payload)):
        fail("public model-breadth manifest self-digest changed")
    actual_manifest_files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if (
        manifest.get("file_count") != len(actual_manifest_files)
        or manifest.get("files") != actual_manifest_files
    ):
        fail("public model-breadth manifest differs from the generated tree")
    scope = manifest.get("scope", {})
    if scope != {
        "breadth_dimension_added": "SERVICE_ROUTE_FAILURE_ONLY",
        "hidden_generalization_claimed": False,
        "hidden_reasoning_included": False,
        "naturalistic_cases": 0,
        "provider_response_identifiers_included": False,
        "public_known_challenge": True,
        "shared_quota_confound_present": True,
        "source_row_hashes_included": False,
    }:
        fail("public model-breadth anonymous scope changed")

    receipt_payload = deepcopy(receipt)
    observed_receipt_sha = receipt_payload.pop("privacy_receipt_sha256", None)
    if observed_receipt_sha != sha256_text(canonical_json(receipt_payload)):
        fail("public model-breadth privacy receipt self-digest changed")
    actual_review_files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"MANIFEST.json", "privacy-receipt-review.json"}
    }
    if receipt.get("review_files_sha256") != actual_review_files:
        fail("public model-breadth privacy receipt file map changed")
    if (
        receipt.get("status") != "ANONYMOUS_PUBLIC_MODEL_BREADTH_DERIVATIVE"
        or receipt.get("source_identity") != "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
        or receipt.get("terminal_records_validated") != 1260
        or receipt.get("raw_final_response_text_included") is not False
        or receipt.get("free_form_error_detail_included") is not False
        or receipt.get("provider_response_identifiers_included") is not False
        or receipt.get("system_fingerprints_included") is not False
        or receipt.get("hidden_reasoning_fields_included") is not False
        or receipt.get("credentials_included") is not False
        or receipt.get("source_row_hashes_included") is not False
        or receipt.get("scientific_fields_unchanged") is not True
        or receipt.get("model_calls_performed") != 0
    ):
        fail("public model-breadth privacy boundary changed")

    plan = load_json(root / "study-plan.json")
    schedule = load_json(root / "request-schedule.json")
    catalog = load_json(root / "catalog-snapshot.json")
    aggregate = load_json(root / "reported-aggregate.json")
    execution = load_json(root / "execution-receipt-review.json")
    failure_addendum = load_json(root / "failure-cause-addendum.json")
    if not all(
        isinstance(value, dict)
        for value in (plan, schedule, catalog, aggregate, execution, failure_addendum)
    ):
        fail("public model-breadth metadata is malformed")
    if (
        failure_addendum.get("status") != "POST_RUN_FROZEN_LOG_AUDIT_COMPLETE"
        or failure_addendum.get("transport_failures") != 630
        or failure_addendum.get("transport_failure_categories")
        != {
            "AUTHORIZATION": 76,
            "CONNECTION": 1,
            "QUOTA_RATE_LIMIT": 547,
            "SERVER": 5,
            "TIMEOUT": 1,
        }
        or failure_addendum.get("quota_cutoff")
        != {
            "cells": 547,
            "contiguous_schedule_tail": True,
            "first_zero_based_sequence": 713,
            "last_zero_based_sequence": 1259,
        }
        or failure_addendum.get("privacy", {}).get("raw_error_text_included") is not False
        or failure_addendum.get("privacy", {}).get("provider_response_identifiers_included")
        is not False
        or failure_addendum.get("interpretation_boundary", {}).get(
            "model_family_comparison_supported"
        )
        is not False
        or failure_addendum.get("interpretation_boundary", {}).get(
            "route_reliability_comparison_supported"
        )
        is not False
    ):
        fail("public model-breadth frozen-log failure audit changed")
    lane_order = plan.get("execution", {}).get("base_lane_order")
    expected_lanes = {str(value) for value in lane_order} if isinstance(lane_order, list) else set()
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("design", {}).get("planned_model_item_cells") != 1260
        or plan.get("design", {}).get("held_out_generalization_claim") is not False
        or plan.get("design", {}).get("naturalistic_case_count") != 0
        or len(expected_lanes) != 7
    ):
        fail("public model-breadth frozen plan boundary changed")
    schedule_payload = deepcopy(schedule)
    schedule_sha = schedule_payload.pop("schedule_sha256", None)
    if (
        schedule_sha != sha256_text(canonical_json(schedule_payload))
        or schedule.get("planned_cells") != 1260
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
        or schedule.get("contains_credentials") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_prompts") is not False
    ):
        fail("public model-breadth request schedule changed")
    catalog_model_ids = catalog.get("model_ids")
    selected_model_ids = catalog.get("selected_model_ids")
    if (
        catalog.get("status") != "CREDENTIAL_AUTHENTICATED_MODEL_CATALOG_SNAPSHOT"
        or not isinstance(catalog_model_ids, list)
        or catalog.get("model_count") != len(catalog_model_ids)
        or catalog.get("model_count") != 29
        or len(set(catalog_model_ids)) != 29
        or not isinstance(selected_model_ids, list)
        or len(selected_model_ids) != 7
        or len(set(selected_model_ids)) != 7
        or not set(selected_model_ids) <= set(catalog_model_ids)
        or catalog.get("account_identifiers_retained") is not False
        or catalog.get("credentials_retained") is not False
        or catalog.get("provider_response_identifiers_retained") is not False
    ):
        fail("public model-breadth catalog boundary changed")
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("planned_cells") != 1260
        or execution.get("durable_request_intents") != 1260
        or execution.get("durable_terminal_records") != 1260
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
        or execution.get("credentials_retained") is not False
        or execution.get("provider_response_identifiers_retained") is not False
        or execution.get("hidden_reasoning_blocks_retained") is not False
        or execution.get("source_journal_digests_included") is not False
    ):
        fail("public model-breadth execution receipt changed")

    lane_files = manifest.get("lane_files")
    receipt_lane_files = receipt.get("review_lane_files")
    lane_hashes = receipt.get("review_lane_files_sha256")
    if (
        not isinstance(lane_files, dict)
        or not isinstance(receipt_lane_files, dict)
        or not isinstance(lane_hashes, dict)
        or lane_files != receipt_lane_files
        or set(lane_files) != expected_lanes
        or set(lane_hashes) != expected_lanes
    ):
        fail("public model-breadth lane manifest changed")

    balanced_root = EVIDENCE / "balanced-public-challenge"
    gold = load_jsonl(balanced_root / "dataset" / "gold.jsonl")
    pairs = load_json(balanced_root / "dataset" / "pairs.json")
    if not isinstance(pairs, list):
        fail("public model-breadth pair index is malformed")
    expected_item_ids = {str(row["id"]) for row in gold}
    if len(expected_item_ids) != 180 or len(pairs) != 90:
        fail("public model-breadth dataset coverage changed")

    aggregate_lanes = {
        str(lane.get("lane_id")): lane
        for lane in aggregate.get("lanes", [])
        if isinstance(lane, dict)
    }
    if set(aggregate_lanes) != expected_lanes:
        fail("public model-breadth aggregate lane set changed")
    row_hash_rows = load_jsonl(root / "review-row-hashes.jsonl")
    row_hashes = {(str(row.get("lane_id")), str(row.get("item_id"))): row for row in row_hash_rows}
    if len(row_hash_rows) != 1260 or len(row_hashes) != 1260:
        fail("public model-breadth row-hash coverage changed")

    metrics_by_lane: list[Json] = []
    parseable_total = 0
    for lane_value in lane_order:
        lane_id = str(lane_value)
        run_path = root / str(lane_files[lane_id])
        if sha256_file(run_path) != lane_hashes[lane_id]:
            fail(f"public model-breadth run digest changed: {lane_id}")
        rows = load_jsonl(run_path)
        if (
            len(rows) != 180
            or {str(row.get("item_id")) for row in rows} != expected_item_ids
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
        ):
            fail(f"public model-breadth run coverage changed: {lane_id}")
        validate_prompt_binding(
            rows,
            balanced_root / "prompt-packet.json",
            f"public model-breadth {lane_id}",
        )
        for row in rows:
            item_id = str(row.get("item_id"))
            validate_with_schema(
                row,
                ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json",
                f"{lane_id}:{item_id}",
            )
            if any(
                row.get(field) is not None
                for field in ("raw_response_text", "transport_error", "parse_error_detail")
            ):
                fail(f"public model-breadth retained private text: {lane_id}:{item_id}")
            if (
                row.get("provider_response_id") is not None
                or row.get("system_fingerprint") is not None
            ):
                fail(f"public model-breadth retained a provider identifier: {lane_id}:{item_id}")
            reject_hidden_reasoning(row, f"public model-breadth {lane_id}:{item_id}")
            binding = row_hashes.get((lane_id, item_id))
            if (
                not isinstance(binding, dict)
                or binding.get("review_row_sha256") != sha256_text(canonical_json(row))
                or binding.get("scientific_fields_unchanged") is not True
            ):
                fail(f"public model-breadth row binding changed: {lane_id}:{item_id}")
        metrics = derive_balanced_metrics(gold, pairs, rows)
        if not equivalent_json(metrics, aggregate_lanes[lane_id].get("metrics")):
            fail(f"public model-breadth aggregate metrics changed: {lane_id}")
        if aggregate_lanes[lane_id].get("run_sha256") != sha256_file(run_path):
            fail(f"public model-breadth aggregate run binding changed: {lane_id}")
        metrics_by_lane.append(metrics)
        parseable_total += int(metrics["parseable_items"])

    if not equivalent_json(
        combine_lane_metrics(metrics_by_lane), aggregate.get("pooled_model_item_cells")
    ):
        fail("public model-breadth pooled metrics changed")
    if (
        aggregate.get("design") != "PUBLIC_PRECOMMITTED_MODEL_BREADTH_SUPPLEMENT"
        or aggregate.get("source_identity") != "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
        or aggregate.get("service_comparison", {}).get("causal_model_ablation_claimed") is not False
        or aggregate.get("service_comparison", {}).get("model_family_comparison_supported")
        is not False
        or aggregate.get("service_comparison", {}).get("route_reliability_comparison_supported")
        is not False
        or aggregate.get("service_comparison", {}).get("scope")
        != "QUOTA_CONFOUNDED_OPERATIONAL_RECORD"
        or aggregate.get("scope_limits")
        != {
            "breadth_dimension_added": "SERVICE_ROUTE_FAILURE_ONLY",
            "hidden_generalization_claimed": False,
            "naturalistic_cases": 0,
            "ontology_count": 1,
            "policy_count": 1,
            "public_known_challenge": True,
            "shared_quota_confound_present": True,
        }
        or aggregate.get("post_run_interpretation")
        != failure_addendum.get("interpretation_boundary")
        or aggregate.get("deterministic_policy_executor", {}).get("label")
        != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    ):
        fail("public model-breadth interpretation boundary changed")
    return {
        "status": "PUBLIC_MODEL_BREADTH_EVIDENCE_PASS",
        "lanes": 7,
        "items_per_lane": 180,
        "pairs_per_lane": 90,
        "terminal_records": 1260,
        "parseable_records": parseable_total,
        "quota_rate_limit_tail_records": failure_addendum["quota_cutoff"]["cells"],
        "privacy_receipt_sha256": observed_receipt_sha,
    }


def main() -> int:
    result = {
        "status": "PASS",
        "fresh_confirmatory": validate_fresh_confirmatory(),
        "balanced_public_challenge": validate_balanced_public_challenge(),
        "slsa_portability": validate_slsa_portability(),
        "policy_switch": validate_policy_switch(),
        "local_model_replications": validate_local_model_replications(),
        "hosted_exclusions": validate_hosted_exclusion_receipts(),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
