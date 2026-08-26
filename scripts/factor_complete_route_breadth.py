#!/usr/bin/env python3
"""Shared definitions for the factor-complete OpenCode Go route-breadth study."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "factor-complete-route-breadth-v2"
DATASET_ROOT = ROOT / "v2" / "balanced-public-challenge" / "dataset"
PACKET_PATH = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
DECISION_SCHEMA = ROOT / "schemas" / "agent-decision.schema.json"
CATALOG_URL = "https://opencode.ai/zen/go/v1/models"
BASE_URL = "https://opencode.ai/zen/go/v1"
STUDY_ID = "claimpromotebench-v2-factor-complete-route-breadth-2026-08-v2"
REPLICATIONS = 3
MAX_OUTPUT_TOKENS = 4096
CONSERVATIVE_INPUT_TOKENS = 5000

Json = dict[str, Any]


CONFIGURATIONS: tuple[Json, ...] = (
    {
        "configuration_id": "opencode-go-glm-5.3-factor-v2",
        "model": "glm-5.3",
        "model_family": "GLM",
        "api_kind": "openai_compatible",
        "input_usd_per_million": 1.4,
        "cached_input_usd_per_million": 0.26,
        "output_usd_per_million": 4.4,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-kimi-k2.7-code-factor-v2",
        "model": "kimi-k2.7-code",
        "model_family": "Kimi",
        "api_kind": "openai_compatible",
        "input_usd_per_million": 0.95,
        "cached_input_usd_per_million": 0.19,
        "output_usd_per_million": 4.0,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-mimo-v2.5-pro-factor-v2",
        "model": "mimo-v2.5-pro",
        "model_family": "MiMo",
        "api_kind": "openai_compatible",
        "input_usd_per_million": 0.435,
        "cached_input_usd_per_million": 0.003625,
        "output_usd_per_million": 0.87,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-minimax-m2.7-factor-v2",
        "model": "minimax-m2.7",
        "model_family": "MiniMax",
        "api_kind": "anthropic_messages",
        "input_usd_per_million": 0.3,
        "cached_input_usd_per_million": 0.06,
        "output_usd_per_million": 1.2,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-qwen3.7-plus-factor-v2",
        "model": "qwen3.7-plus",
        "model_family": "Qwen",
        "api_kind": "anthropic_messages",
        "input_usd_per_million": 0.4,
        "cached_input_usd_per_million": 0.04,
        "output_usd_per_million": 1.6,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-hy3-factor-v2",
        "model": "hy3",
        "model_family": "Tencent Hunyuan",
        "api_kind": "openai_compatible",
        "input_usd_per_million": 0.14,
        "cached_input_usd_per_million": 0.035,
        "output_usd_per_million": 0.58,
        "data_training": False,
        "data_retention_days": 0,
    },
    {
        "configuration_id": "opencode-go-gpt-5.6-luna-factor-v2",
        "model": "gpt-5.6-luna",
        "model_family": "OpenAI",
        "api_kind": "openai_responses",
        "input_usd_per_million": 0.2,
        "cached_input_usd_per_million": 0.02,
        "output_usd_per_million": 1.2,
        "data_training": False,
        "data_retention_days": 30,
    },
)


def lane_id(configuration_id: str, replication: int) -> str:
    return f"{configuration_id}-r{replication}"


def expanded_lanes() -> list[Json]:
    lanes: list[Json] = []
    for replication in range(1, REPLICATIONS + 1):
        for configuration in CONFIGURATIONS:
            lane = deepcopy(configuration)
            lane.update(
                {
                    "lane_id": lane_id(str(configuration["configuration_id"]), replication),
                    "replication": replication,
                    "provider": "OpenCode Go",
                    "base_url": BASE_URL,
                    "auth_env": "OPENCODE_GO_API_KEY",
                    "response_format": "prompt_only_json",
                    "allow_single_json_object_extraction": True,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
                }
            )
            lanes.append(lane)
    return lanes


def selected_pairs(all_pairs: list[Json]) -> list[Json]:
    """Choose the lexicographically first pair for every registered factor."""

    ordered = sorted(all_pairs, key=lambda row: (str(row["factor_id"]), str(row["pair_id"])))
    selected: list[Json] = []
    seen: set[str] = set()
    for row in ordered:
        factor_id = str(row["factor_id"])
        if factor_id not in seen:
            selected.append(row)
            seen.add(factor_id)
    if len(selected) != 15 or len(seen) != 15:
        raise ValueError("factor-complete selection must contain exactly 15 factors and pairs")
    return selected


def selected_item_ids(all_pairs: list[Json]) -> list[str]:
    return sorted(
        str(item_id) for row in selected_pairs(all_pairs) for item_id in row["member_ids"]
    )


def selected_action_counts(gold: list[Json], item_ids: list[str]) -> Counter[str]:
    wanted = set(item_ids)
    return Counter(str(row["decision"]["action"]) for row in gold if str(row["id"]) in wanted)


def request_body(lane: Json, prompt: str) -> Json:
    if lane["response_format"] != "prompt_only_json":
        raise ValueError("factor-complete study requires prompt-only JSON")
    if lane["api_kind"] in {"openai_compatible", "anthropic_messages"}:
        return {
            "model": lane["model"],
            "max_tokens": int(lane["max_output_tokens"]),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    if lane["api_kind"] == "openai_responses":
        return {
            "model": lane["model"],
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "max_output_tokens": int(lane["max_output_tokens"]),
            "stream": False,
        }
    raise ValueError(f"unsupported API adapter: {lane['api_kind']}")


def conservative_cost_upper_bound_usd() -> float:
    calls_per_configuration = 30 * REPLICATIONS
    return sum(
        calls_per_configuration
        * (
            CONSERVATIVE_INPUT_TOKENS * float(configuration["input_usd_per_million"])
            + MAX_OUTPUT_TOKENS * float(configuration["output_usd_per_million"])
        )
        / 1_000_000
        for configuration in CONFIGURATIONS
    )


def schedule_payload(plan: Json, packet: Json, all_pairs: list[Json]) -> Json:
    from claimpromotebench.hashing import canonical_json, sha256_bytes

    item_ids = selected_item_ids(all_pairs)
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    if set(item_ids) - set(packet_by_id):
        raise ValueError("selected factor-complete items are absent from the prompt packet")
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    configuration_order = [str(row["configuration_id"]) for row in CONFIGURATIONS]
    cells: list[Json] = []
    group_index = 0
    for replication in range(1, REPLICATIONS + 1):
        for item_index, item_id in enumerate(item_ids):
            rotation = group_index % len(configuration_order)
            rotated = configuration_order[rotation:] + configuration_order[:rotation]
            for within_group_position, configuration_id in enumerate(rotated):
                current_lane_id = lane_id(configuration_id, replication)
                lane = lanes[current_lane_id]
                packet_row = packet_by_id[item_id]
                body = request_body(lane, str(packet_row["prompt"]))
                cells.append(
                    {
                        "sequence": len(cells),
                        "group_index": group_index,
                        "replication": replication,
                        "item_index": item_index,
                        "within_group_position": within_group_position,
                        "cell_id": f"{current_lane_id}/{item_id}",
                        "configuration_id": configuration_id,
                        "lane_id": current_lane_id,
                        "item_id": item_id,
                        "pair_id": str(packet_row["pair_id"]),
                        "prompt_sha256": str(packet_row["prompt_sha256"]),
                        "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
                    }
                )
            group_index += 1
    payload: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "status": "FROZEN_BEFORE_MODEL_CALLS",
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "packet_sha256": packet["packet_sha256"],
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "selection_rule": "LEXICOGRAPHICALLY_FIRST_PAIR_PER_REGISTERED_FACTOR",
        "selected_pair_ids": [str(row["pair_id"]) for row in selected_pairs(all_pairs)],
        "selected_item_ids": item_ids,
        "configuration_order": configuration_order,
        "replications": REPLICATIONS,
        "planned_configurations": len(CONFIGURATIONS),
        "planned_lanes": len(plan["formal_lanes"]),
        "planned_items_per_lane": len(item_ids),
        "planned_groups": group_index,
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    payload["schedule_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return payload
