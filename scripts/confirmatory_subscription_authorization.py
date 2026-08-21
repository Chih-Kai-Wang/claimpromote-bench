#!/usr/bin/env python3
"""Validate the fixed client-side subscription authorization before any credential."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from claimpromotebench.dataset import load_json
from claimpromotebench.hashing import canonical_json, sha256_bytes

Json = dict[str, Any]

MODE = "PREEXISTING_SUBSCRIPTION_QUOTA_ONLY"
STATUS = "SUBSCRIPTION_AUTHORIZATION_GATE_PASS"
LANES = (
    "opencode-go-qwen3.7-max",
    "opencode-go-deepseek-v4-flash-matched",
)
PLANNED_POSTS = 600
POSTS_PER_LANE = 300
MAX_OUTPUT_TOKENS = 1536
BASE_URL = "https://opencode.ai/zen/go/v1"
AUTH_ENV = "OPENCODE_GO_API_KEY"
AUTHORIZATION_SCOPE = (
    "USER_AUTHORIZED_FULL_EXISTING_OPENCODE_GO_SUBSCRIPTION_QUOTA_FOR_THIS_FIXED_600_CELL_STUDY"
)
ROOT = Path(__file__).resolve().parents[1]


def _portable_decision_schema() -> Json:
    schema = deepcopy(load_json(ROOT / "schemas" / "agent-decision.schema.json"))
    schema.pop("$schema", None)
    schema.pop("$id", None)
    schema.pop("title", None)
    definitions = schema.pop("$defs", {})
    state = definitions.get("state")
    proposed = schema.get("properties", {}).get("proposed_state")
    _require(isinstance(state, dict) and isinstance(proposed, dict), "decision schema changed")
    schema["properties"]["proposed_state"] = deepcopy(state)

    def subset(value: Any) -> Any:
        unsupported = {"uniqueItems", "pattern", "minimum", "maximum"}
        if isinstance(value, dict):
            return {key: subset(child) for key, child in value.items() if key not in unsupported}
        if isinstance(value, list):
            return [subset(child) for child in value]
        return value

    return subset(schema)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"subscription authorization: {message}")


def _formal_lanes(plan: Json) -> dict[str, Json]:
    rows = plan.get("formal_lanes")
    _require(isinstance(rows, list) and len(rows) == 2, "exactly two formal lanes are required")
    lanes = {
        str(row.get("lane_id")): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("lane_id"), str)
    }
    _require(tuple(plan.get("execution", {}).get("lane_order", [])) == LANES, "lane order changed")
    _require(set(lanes) == set(LANES), "authorized lane set changed")
    expected = {
        "opencode-go-qwen3.7-max": {
            "model": "qwen3.7-max",
            "api_kind": "anthropic_messages",
            "response_format": "prompt_only_json",
        },
        "opencode-go-deepseek-v4-flash-matched": {
            "model": "deepseek-v4-flash",
            "api_kind": "openai_compatible",
            "response_format": "json_schema",
        },
    }
    for lane_id, fields in expected.items():
        _require(
            all(lanes[lane_id].get(key) == value for key, value in fields.items()),
            f"{lane_id} adapter configuration changed",
        )
    return lanes


def validate_plan_authorization(plan: Json) -> Json:
    """Validate only public C0 authorization terms, without a hidden schedule."""

    budget = plan.get("budget")
    _require(isinstance(budget, dict), "budget object is missing")
    expected = {
        "mode": MODE,
        "planned_application_posts": PLANNED_POSTS,
        "planned_posts_per_lane": POSTS_PER_LANE,
        "max_output_tokens_per_post": MAX_OUTPUT_TOKENS,
        "incremental_cash_cap_usd": 0.0,
        "workflow_initiated_purchase_or_recharge": False,
        "cash_balance_fallback": False,
        "alternate_provider_fallback": False,
        "per_lane_token_usd_cap": None,
        "pre_post_token_cost_gate": "NOT_APPLICABLE",
        "quota_exhaustion": "CELL_INCORRECT_NO_RETRY",
        "provider_reported_usage_and_quota_value": "POSTHOC_DESCRIPTIVE_ONLY",
        "adaptive_stop_on_usage_or_results": False,
    }
    for key, value in expected.items():
        _require(budget.get(key) == value, f"budget.{key} changed")
    _require(
        budget.get("authorization_scope") == AUTHORIZATION_SCOPE,
        "subscription authorization scope changed",
    )

    design = plan.get("design", {})
    _require(design.get("planned_lanes") == 2, "planned lane count changed")
    _require(design.get("planned_instances") == 300, "planned item count changed")
    _require(design.get("planned_model_item_cells") == PLANNED_POSTS, "planned cell count changed")
    execution = plan.get("execution", {})
    _require(execution.get("application_posts_per_cell") == 1, "posts per cell changed")
    _require(execution.get("client_retry_count") == 0, "client retry became possible")
    _require(execution.get("redirect_following") is False, "redirect following became possible")
    _require(execution.get("partial_resume") == "FORBIDDEN", "partial resume became possible")
    _require(
        execution.get("workflow_job_rerun")
        == (
            "FORBIDDEN; ANY_R6_SCORED_WORKFLOW_DISPATCH_CONSUMES_THE_VERSION_"
            "REGARDLESS_OF_CONFIRM_VALUE_POST_COUNT_OR_JOB_OUTCOME"
        ),
        "workflow rerun rule changed",
    )

    lanes = _formal_lanes(plan)
    for lane_id, lane in lanes.items():
        _require(lane.get("base_url") == BASE_URL, f"{lane_id} left the subscription endpoint")
        _require(lane.get("auth_env") == AUTH_ENV, f"{lane_id} uses another credential")
        _require(
            lane.get("billing_mode") == "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
            f"{lane_id} billing mode changed",
        )
        _require(lane.get("spend_cap_usd") is None, f"{lane_id} reintroduced a token-USD cap")
        _require(
            lane.get("quota_value_rates_use") == "POSTHOC_DESCRIPTIVE_ONLY",
            f"{lane_id} quota-value rates became operational",
        )
        _require(
            lane.get("max_output_tokens") == MAX_OUTPUT_TOKENS,
            f"{lane_id} max output changed",
        )
        _require("provider_routing" not in lane, f"{lane_id} gained provider fallback routing")

    summary: Json = {
        "schema_version": "1.0.0",
        "status": STATUS,
        "budget_mode": MODE,
        "authorized_lane_ids": list(LANES),
        "planned_application_posts": PLANNED_POSTS,
        "planned_posts_per_lane": POSTS_PER_LANE,
        "max_output_tokens_per_post": MAX_OUTPUT_TOKENS,
        "incremental_cash_cap_usd": 0.0,
        "workflow_initiated_purchase_or_recharge": False,
        "cash_balance_fallback": False,
        "alternate_provider_fallback": False,
        "per_lane_token_usd_cap": None,
        "pre_post_token_cost_gate": "NOT_APPLICABLE",
        "quota_exhaustion": "CELL_INCORRECT_NO_RETRY",
        "provider_reported_usage_and_quota_value": "POSTHOC_DESCRIPTIVE_ONLY",
        "adaptive_stop_on_usage_or_results": False,
        "contains_request_bodies": False,
        "contains_prompts": False,
        "contains_credentials": False,
    }
    summary["authorization_contract_sha256"] = sha256_bytes(canonical_json(summary).encode("utf-8"))
    return summary


def validate_schedule_authorization(plan: Json, schedule: Json) -> Json:
    """Recompute the authorization gate from all exact C1 request bodies."""

    summary = validate_plan_authorization(plan)
    lanes = _formal_lanes(plan)
    _require(schedule.get("study_id") == plan.get("study_id"), "schedule study changed")
    _require(schedule.get("planned_cells") == PLANNED_POSTS, "schedule cell count changed")
    _require(schedule.get("application_posts_per_cell") == 1, "schedule posts per cell changed")
    _require(schedule.get("client_retry_count") == 0, "schedule retry count changed")
    _require(tuple(schedule.get("lane_order", [])) == LANES, "schedule lane order changed")
    cells = schedule.get("cells")
    _require(
        isinstance(cells, list) and len(cells) == PLANNED_POSTS, "schedule cells are incomplete"
    )

    counts: Counter[str] = Counter()
    cell_ids: set[str] = set()
    sequences: dict[str, set[int]] = {lane_id: set() for lane_id in LANES}
    ordered_items: dict[str, dict[int, str]] = {lane_id: {} for lane_id in LANES}
    portable_schema = _portable_decision_schema()
    for position, cell in enumerate(cells):
        _require(isinstance(cell, dict), "schedule contains a non-object cell")
        lane_id = str(cell.get("lane_id"))
        _require(lane_id in LANES, "schedule contains an unauthorized lane")
        item_id = cell.get("item_id")
        _require(isinstance(item_id, str) and item_id, "schedule item ID is malformed")
        cell_id = f"{lane_id}/{item_id}"
        _require(cell.get("cell_id") == cell_id, "schedule cell ID changed")
        _require(cell_id not in cell_ids, "schedule contains a duplicate cell")
        cell_ids.add(cell_id)
        counts[lane_id] += 1
        sequence = cell.get("sequence")
        _require(
            isinstance(sequence, int) and 0 <= sequence < POSTS_PER_LANE,
            "schedule sequence is malformed",
        )
        _require(
            lane_id == LANES[position // POSTS_PER_LANE] and sequence == position % POSTS_PER_LANE,
            "schedule cell order changed",
        )
        _require(sequence not in sequences[lane_id], "schedule sequence is duplicated")
        sequences[lane_id].add(sequence)
        ordered_items[lane_id][sequence] = item_id
        body = cell.get("request_body")
        _require(isinstance(body, dict), "schedule request body is missing")
        _require(body.get("model") == lanes[lane_id].get("model"), "request model changed")
        _require(body.get("max_tokens") == MAX_OUTPUT_TOKENS, "request max_tokens changed")
        for alternate in ("max_output_tokens", "max_completion_tokens"):
            _require(alternate not in body, f"request contains alternate output limit {alternate}")
        _require(body.get("stream") is False, "streaming became possible")
        messages = body.get("messages")
        _require(isinstance(messages, list) and len(messages) == 1, "message count changed")
        message = messages[0]
        _require(
            isinstance(message, dict)
            and set(message) == {"role", "content"}
            and message.get("role") == "user"
            and isinstance(message.get("content"), str),
            "request is not exactly one user-text message",
        )
        prompt = str(message["content"])
        _require(
            cell.get("prompt_sha256") == sha256_bytes(prompt.encode("utf-8")),
            "request prompt digest changed",
        )
        _require(isinstance(cell.get("pair_id"), str) and cell["pair_id"], "pair ID changed")
        expected_body_keys = (
            {"model", "max_tokens", "messages", "stream"}
            if lane_id == "opencode-go-qwen3.7-max"
            else {"model", "max_tokens", "messages", "response_format", "stream"}
        )
        _require(set(body) == expected_body_keys, "request body gained an unregistered field")
        _require(
            cell.get("request_body_sha256") == sha256_bytes(canonical_json(body).encode("utf-8")),
            "request body digest changed",
        )
        if lane_id == "opencode-go-deepseek-v4-flash-matched":
            _require(
                body.get("response_format")
                == {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent_decision",
                        "strict": True,
                        "schema": portable_schema,
                    },
                },
                "request response schema changed",
            )
        headers = cell.get("request_headers_template")
        _require(isinstance(headers, dict), "request header template is missing")
        expected_headers = {
            "Content-Type": "application/json",
            "User-Agent": "ClaimPromoteBench-Confirmatory/1",
            "Authorization": "<REDACTED_CREDENTIAL>",
        }
        if lane_id == "opencode-go-qwen3.7-max":
            expected_headers.update(
                {
                    "x-api-key": "<REDACTED_CREDENTIAL>",
                    "anthropic-version": "2023-06-01",
                }
            )
        _require(headers == expected_headers, "request header template changed")
    _require(
        counts == Counter({lane_id: POSTS_PER_LANE for lane_id in LANES}),
        "schedule is not exactly 300 posts per lane",
    )
    _require(
        all(sequences[lane_id] == set(range(POSTS_PER_LANE)) for lane_id in LANES),
        "schedule sequence coverage changed",
    )
    _require(
        ordered_items[LANES[0]] == ordered_items[LANES[1]]
        and [ordered_items[LANES[0]][index] for index in range(POSTS_PER_LANE)]
        == sorted(ordered_items[LANES[0]].values()),
        "schedule item order changed",
    )

    payload = deepcopy(summary)
    payload.pop("authorization_contract_sha256")
    payload.update(
        {
            "status": STATUS,
            "schedule_recomputed_from_exact_request_bodies": True,
            "schedule_cells_verified": len(cells),
            "per_lane_cells_verified": {lane_id: counts[lane_id] for lane_id in LANES},
        }
    )
    payload["authorization_contract_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return payload
