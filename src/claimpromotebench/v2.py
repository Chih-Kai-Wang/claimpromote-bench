"""Helpers for the low-cost ICLR v2 pilot.

The v2 pilot is deliberately separate from the frozen v1 study. It retains raw model text,
separates syntax/schema/semantic failures, supports schema-constrained decoding, and computes a
pure post-processing gate result from the same model response.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from .dataset import validate_with_schema
from .gate import apply_gate
from .oracle import evaluate
from .state import validate_decision_semantics

Json = dict[str, Any]
ParseStatus = Literal["OK", "JSON_SYNTAX_ERROR", "SCHEMA_ERROR", "SEMANTIC_ERROR"]
DecodingMode = Literal["free", "json_schema"]


def llama_response_format(schema: Json) -> Json:
    """Return the schema-constrained response format supported by the frozen llama.cpp runtime."""

    cleaned = deepcopy(schema)
    cleaned.pop("$schema", None)
    cleaned.pop("$id", None)
    return {"type": "json_object", "schema": cleaned}


def diagnose_decision(
    content: str,
    item: Json,
    *,
    schema_path: Any,
) -> tuple[ParseStatus, Json | None, str | None]:
    """Parse one response and preserve which validation layer failed."""

    import json

    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return "JSON_SYNTAX_ERROR", None, f"{exc.msg} at line {exc.lineno} column {exc.colno}"
    if not isinstance(value, dict):
        return "SCHEMA_ERROR", None, "top-level JSON value is not an object"
    try:
        validate_with_schema(value, schema_path, "v2 model decision")
    except Exception as exc:  # validation library supplies the actionable detail
        return "SCHEMA_ERROR", None, str(exc)
    try:
        validate_decision_semantics(item, value)
    except Exception as exc:
        return "SEMANTIC_ERROR", None, str(exc)
    return "OK", value, None


def postgate_decision(raw_decision: Json, item: Json, policy: Json, evaluation_time: str) -> Json:
    """Apply the deterministic gate after generation without changing the model-facing prompt."""

    oracle_result = evaluate(item, policy, evaluation_time)
    gate_result = apply_gate(raw_decision, oracle_result)
    final_decision = gate_result.get("final_decision")
    if not isinstance(final_decision, dict):
        raise RuntimeError("gate result lacks a final_decision object")
    return final_decision


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize_pilot(gold: list[Json], pairs: list[Json], records: list[Json]) -> Json:
    """Summarize one model/decoding-mode pilot run with coverage-aware pair metrics."""

    gold_by_id = {str(row["id"]): row for row in gold}
    record_by_id = {str(row["item_id"]): row for row in records}
    if len(record_by_id) != len(records):
        raise ValueError("duplicate item_id in v2 pilot records")
    missing = sorted(set(gold_by_id) - set(record_by_id))
    extra = sorted(set(record_by_id) - set(gold_by_id))
    if missing or extra:
        raise ValueError(f"v2 pilot record coverage mismatch: missing={missing}, extra={extra}")

    status_counts = {
        status: sum(row["parse_status"] == status for row in records)
        for status in ("OK", "JSON_SYNTAX_ERROR", "SCHEMA_ERROR", "SEMANTIC_ERROR")
    }
    ok_records = [row for row in records if row["parse_status"] == "OK"]
    raw_correct = 0
    postgate_correct = 0
    raw_false_promotions = 0
    raw_invalid = 0
    raw_valid = 0
    raw_valid_allows = 0
    for row in ok_records:
        gold_action = gold_by_id[str(row["item_id"])]["decision"]["action"]
        raw_action = row["raw_decision"]["action"]
        postgate_action = row["postgate_decision"]["action"]
        raw_correct += raw_action == gold_action
        postgate_correct += postgate_action == gold_action
        if gold_action == "ALLOW":
            raw_valid += 1
            raw_valid_allows += raw_action == "ALLOW"
        else:
            raw_invalid += 1
            raw_false_promotions += raw_action == "ALLOW"

    pair_rows: list[Json] = []
    factor_rows: dict[str, Json] = {}
    covered_pairs = 0
    raw_pair_correct = 0
    postgate_pair_correct = 0
    raw_flip_pairs = 0
    for pair in pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        member_records = [record_by_id[item_id] for item_id in member_ids]
        covered = all(row["parse_status"] == "OK" for row in member_records)
        factor_id = str(pair["factor_id"])
        factor = factor_rows.setdefault(
            factor_id,
            {
                "factor_id": factor_id,
                "family": pair.get("family"),
                "pairs": 0,
                "covered_pairs": 0,
                "raw_pair_correct": 0,
                "postgate_pair_correct": 0,
                "raw_flip_pairs": 0,
            },
        )
        factor["pairs"] += 1
        pair_summary: Json = {
            "pair_id": pair["pair_id"],
            "factor_id": factor_id,
            "family": pair.get("family"),
            "covered": covered,
        }
        if covered:
            covered_pairs += 1
            factor["covered_pairs"] += 1
            gold_actions = [gold_by_id[item_id]["decision"]["action"] for item_id in member_ids]
            raw_actions = [row["raw_decision"]["action"] for row in member_records]
            postgate_actions = [row["postgate_decision"]["action"] for row in member_records]
            raw_pair_ok = raw_actions == gold_actions
            postgate_pair_ok = postgate_actions == gold_actions
            raw_flip = len(set(raw_actions)) > 1
            raw_pair_correct += raw_pair_ok
            postgate_pair_correct += postgate_pair_ok
            raw_flip_pairs += raw_flip
            factor["raw_pair_correct"] += raw_pair_ok
            factor["postgate_pair_correct"] += postgate_pair_ok
            factor["raw_flip_pairs"] += raw_flip
            pair_summary.update(
                {
                    "gold_actions": gold_actions,
                    "raw_actions": raw_actions,
                    "postgate_actions": postgate_actions,
                    "raw_pair_correct": raw_pair_ok,
                    "postgate_pair_correct": postgate_pair_ok,
                    "raw_flip": raw_flip,
                }
            )
        pair_rows.append(pair_summary)

    for factor in factor_rows.values():
        factor["pair_coverage"] = _safe_rate(factor["covered_pairs"], factor["pairs"])
        factor["raw_pair_accuracy"] = _safe_rate(
            factor["raw_pair_correct"], factor["covered_pairs"]
        )
        factor["postgate_pair_accuracy"] = _safe_rate(
            factor["postgate_pair_correct"], factor["covered_pairs"]
        )
        factor["raw_flip_rate"] = _safe_rate(factor["raw_flip_pairs"], factor["covered_pairs"])

    return {
        "records": len(records),
        "status_counts": status_counts,
        "decision_coverage": _safe_rate(len(ok_records), len(records)),
        "raw_action_accuracy": _safe_rate(raw_correct, len(ok_records)),
        "postgate_action_accuracy": _safe_rate(postgate_correct, len(ok_records)),
        "raw_fpr": _safe_rate(raw_false_promotions, raw_invalid),
        "raw_vpr": _safe_rate(raw_valid_allows, raw_valid),
        "pairs": len(pairs),
        "covered_pairs": covered_pairs,
        "pair_coverage": _safe_rate(covered_pairs, len(pairs)),
        "raw_pair_accuracy": _safe_rate(raw_pair_correct, covered_pairs),
        "postgate_pair_accuracy": _safe_rate(postgate_pair_correct, covered_pairs),
        "raw_flip_rate": _safe_rate(raw_flip_pairs, covered_pairs),
        "factor_metrics": [factor_rows[key] for key in sorted(factor_rows)],
        "pair_metrics": pair_rows,
    }
