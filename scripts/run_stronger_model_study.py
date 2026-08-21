#!/usr/bin/env python3
"""Run one frozen stronger-model lane with no retries and complete final-response retention."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_dataset,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.v2 import diagnose_decision, postgate_decision  # noqa: E402

Json = dict[str, Any]
DEFAULT_PLAN = ROOT / "v2" / "stronger-model-study-plan.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
DECISION_SCHEMA = ROOT / "schemas" / "agent-decision.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"stronger-model-run: {message}")


def provider_decision_schema(schema: Json) -> Json:
    """Return a self-contained schema accepted by strict structured-output implementations."""

    cleaned = deepcopy(schema)
    cleaned.pop("$schema", None)
    cleaned.pop("$id", None)
    cleaned.pop("title", None)
    definitions = cleaned.pop("$defs", {})
    state = definitions.get("state")
    if not isinstance(state, dict):
        fail("decision schema lacks $defs.state")
    proposed = cleaned.get("properties", {}).get("proposed_state")
    if not isinstance(proposed, dict) or proposed.get("$ref") != "#/$defs/state":
        fail("decision schema proposed_state reference changed")
    cleaned["properties"]["proposed_state"] = deepcopy(state)
    return _portable_schema_subset(cleaned)


def _portable_schema_subset(value: Any) -> Any:
    """Keep the common provider-supported shape subset; full validation remains local."""

    unsupported = {"uniqueItems", "pattern", "minimum", "maximum"}
    if isinstance(value, dict):
        return {
            key: _portable_schema_subset(child)
            for key, child in value.items()
            if key not in unsupported
        }
    if isinstance(value, list):
        return [_portable_schema_subset(child) for child in value]
    return value


def find_lane(plan: Json, lane_id: str) -> tuple[Json, bool]:
    for key, formal in (("formal_lanes", True), ("exploratory_lanes", False)):
        for lane in plan.get(key, []):
            if lane.get("lane_id") == lane_id:
                return lane, formal
    fail(f"unknown lane_id: {lane_id}")


def full_requires_pilot(plan: Json) -> bool:
    """Return the registered pilot rule, preserving legacy plans by default."""

    value = plan.get("design", {}).get("full_requires_pilot", True)
    if not isinstance(value, bool):
        fail("plan.design.full_requires_pilot must be Boolean")
    return value


def verify_frozen_plan(plan_path: Path, commit: str, plan: Json) -> None:
    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("study plan is not frozen")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        fail("--frozen-plan-commit must be a full 40-character Git SHA")
    relative = plan_path.resolve().relative_to(ROOT).as_posix()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        fail("frozen plan commit is not an ancestor of HEAD")
    shown = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0:
        fail("frozen plan file is absent from the supplied commit")
    if shown.stdout != plan_path.read_bytes():
        fail("current study plan bytes differ from the frozen commit")


def response_format(lane: Json, schema: Json) -> Json:
    if lane["api_kind"] == "anthropic_messages":
        if lane["response_format"] == "prompt_only_json":
            return {}
        if lane["response_format"] != "forced_tool_schema":
            fail("Anthropic Messages lane must use forced_tool_schema or prompt_only_json")
        return {
            "tool_choice": {"type": "tool", "name": "submit_decision"},
            "tools": [
                {
                    "name": "submit_decision",
                    "description": "Return the final ClaimPromoteBench decision.",
                    "input_schema": schema,
                }
            ],
        }
    if lane["api_kind"] == "openai_responses":
        if lane["response_format"] != "json_schema":
            fail("OpenAI Responses lane must use json_schema")
        return {
            "type": "json_schema",
            "name": "agent_decision",
            "strict": True,
            "schema": schema,
        }
    if lane["api_kind"] == "gemini_generate_content":
        if lane["response_format"] != "json_schema":
            fail("Gemini lane must use json_schema")
        return {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        }
    if lane["response_format"] == "json_object":
        return {"type": "json_object"}
    if lane["response_format"] == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {"name": "agent_decision", "strict": True, "schema": schema},
        }
    fail(f"unsupported response format: {lane['response_format']}")


def conservative_upper_bound_usd(records: list[Json], lane: Json) -> float | None:
    """Bound tokens conservatively at one token per two UTF-8 bytes plus max output."""

    required = ("input_usd_per_million", "output_usd_per_million")
    if any(not isinstance(lane.get(key), (int, float)) for key in required):
        return None
    input_tokens = sum(math.ceil(int(row["utf8_bytes"]) / 2) for row in records)
    output_tokens = len(records) * int(lane["max_output_tokens"])
    return (
        input_tokens * float(lane["input_usd_per_million"])
        + output_tokens * float(lane["output_usd_per_million"])
    ) / 1_000_000


def _http_json(url: str, body: Json, headers: dict[str, str], timeout: float) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ClaimPromoteBench/1",
            **headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"transport failure: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("provider returned non-JSON HTTP content") from exc
    if not isinstance(value, dict):
        raise RuntimeError("provider response must be a JSON object")
    if value.get("error") is not None:
        raise RuntimeError(f"provider returned an error: {value['error']}")
    return value


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def validate_api_key(value: str | None, env_name: str) -> str:
    if not value:
        fail(f"required API credential is not set: {env_name}")
    if value != value.strip() or any(ord(char) < 33 or ord(char) > 126 for char in value):
        fail(f"API credential contains whitespace or control bytes: {env_name}")
    return value


def extract_single_json_object(content: str) -> str | None:
    """Extract one balanced JSON object from an otherwise textual response."""

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


def diagnose_provider_content(
    content: str,
    item: Json,
    *,
    schema_path: Path,
    allow_single_object_extraction: bool,
) -> tuple[str, Json | None, str | None]:
    status, decision, detail = diagnose_decision(content, item, schema_path=schema_path)
    if status != "JSON_SYNTAX_ERROR" or not allow_single_object_extraction:
        return status, decision, detail
    extracted = extract_single_json_object(content)
    if extracted is None:
        return status, decision, detail
    status, decision, detail = diagnose_decision(extracted, item, schema_path=schema_path)
    marker = "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
    return status, decision, marker if detail is None else f"{marker}: {detail}"


def openai_request_body(lane: Json, prompt: str, schema: Json) -> Json:
    body: Json = {
        "model": lane["model"],
        "messages": [{"role": "user", "content": prompt}],
        "response_format": response_format(lane, schema),
        "stream": False,
    }
    if lane.get("send_reasoning_effort", True) and isinstance(lane.get("reasoning_effort"), str):
        body["reasoning_effort"] = lane["reasoning_effort"]
    max_output_parameter = lane.get("max_output_parameter")
    if max_output_parameter is None:
        max_output_parameter = (
            "max_completion_tokens"
            if str(lane["base_url"]).startswith("https://api.openai.com")
            else "max_tokens"
        )
    if max_output_parameter not in {"max_completion_tokens", "max_tokens"}:
        fail(f"unsupported max-output parameter: {max_output_parameter}")
    body[str(max_output_parameter)] = int(lane["max_output_tokens"])
    provider_routing = lane.get("provider_routing")
    if provider_routing is not None:
        if not isinstance(provider_routing, dict):
            fail("provider_routing must be an object")
        body["provider"] = deepcopy(provider_routing)
    if lane["provider"] == "DeepSeek" and str(lane["base_url"]).startswith(
        "https://api.deepseek.com"
    ):
        body["thinking"] = {"type": "enabled"}
    return body


def call_openai_compatible(
    lane: Json, body: Json, api_key: str | None, timeout: float
) -> tuple[Json, str | None, Json]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    response = _http_json(
        str(lane["base_url"]).rstrip("/") + "/chat/completions",
        body,
        headers,
        timeout,
    )
    try:
        choice = response["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("provider response lacks choices[0].message") from exc
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise RuntimeError("provider final content is not text")
    usage_raw = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    prompt_details = usage_raw.get("prompt_tokens_details")
    completion_details = usage_raw.get("completion_tokens_details")
    usage = {
        "input_tokens": _integer(usage_raw.get("prompt_tokens")),
        "cached_input_tokens": _integer(
            prompt_details.get("cached_tokens") if isinstance(prompt_details, dict) else None
        ),
        "output_tokens": _integer(usage_raw.get("completion_tokens")),
        "reasoning_tokens": _integer(
            completion_details.get("reasoning_tokens")
            if isinstance(completion_details, dict)
            else None
        ),
        "total_tokens": _integer(usage_raw.get("total_tokens")),
    }
    metadata = {
        "provider_response_id": _optional_text(response.get("id")),
        "model_returned": _optional_text(response.get("model")),
        "routed_provider": _optional_text(response.get("provider")),
        "system_fingerprint": _optional_text(response.get("system_fingerprint")),
        "finish_reason": _optional_text(choice.get("finish_reason")),
    }
    return metadata, content, usage


def anthropic_request_body(lane: Json, prompt: str, schema: Json) -> Json:
    constraint = response_format(lane, schema)
    return {
        "model": lane["model"],
        "max_tokens": int(lane["max_output_tokens"]),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        **constraint,
    }


def call_anthropic_messages(
    lane: Json, body: Json, api_key: str, timeout: float
) -> tuple[Json, str | None, Json]:
    response = _http_json(
        str(lane["base_url"]).rstrip("/") + "/messages",
        body,
        {
            "Authorization": f"Bearer {api_key}",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout,
    )
    blocks = response.get("content")
    if not isinstance(blocks, list):
        raise RuntimeError("provider response lacks Anthropic content blocks")
    tool_inputs = [
        block.get("input")
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") == "tool_use"
        and block.get("name") == "submit_decision"
        and isinstance(block.get("input"), dict)
    ]
    if len(tool_inputs) > 1:
        raise RuntimeError("provider returned multiple submit_decision tool calls")
    if tool_inputs:
        content = json.dumps(tool_inputs[0], ensure_ascii=False, sort_keys=True)
    else:
        text_blocks = [
            str(block["text"])
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]
        content = "".join(text_blocks) or None
    usage_raw = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_tokens = _integer(usage_raw.get("input_tokens"))
    cache_read = _integer(usage_raw.get("cache_read_input_tokens"))
    output_tokens = _integer(usage_raw.get("output_tokens"))
    usage = {
        "input_tokens": input_tokens,
        "cached_input_tokens": cache_read,
        "output_tokens": output_tokens,
        "reasoning_tokens": None,
        "total_tokens": (
            input_tokens + output_tokens
            if isinstance(input_tokens, int) and isinstance(output_tokens, int)
            else None
        ),
    }
    metadata = {
        "provider_response_id": _optional_text(response.get("id")),
        "model_returned": _optional_text(response.get("model")),
        "routed_provider": None,
        "system_fingerprint": None,
        "finish_reason": _optional_text(response.get("stop_reason")),
    }
    return metadata, content, usage


def responses_request_body(lane: Json, prompt: str, schema: Json) -> Json:
    return {
        "model": lane["model"],
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "text": {"format": response_format(lane, schema)},
        "max_output_tokens": int(lane["max_output_tokens"]),
        "stream": False,
    }


def call_openai_responses(
    lane: Json, body: Json, api_key: str, timeout: float
) -> tuple[Json, str | None, Json]:
    response = _http_json(
        str(lane["base_url"]).rstrip("/") + "/responses",
        body,
        {"Authorization": f"Bearer {api_key}"},
        timeout,
    )
    output = response.get("output")
    if not isinstance(output, list):
        raise RuntimeError("provider response lacks Responses API output")
    final_text: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        blocks = item.get("content")
        if not isinstance(blocks, list):
            continue
        final_text.extend(
            str(block["text"])
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "output_text"
            and isinstance(block.get("text"), str)
        )
    content = "".join(final_text) or None
    usage_raw = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_details = usage_raw.get("input_tokens_details")
    output_details = usage_raw.get("output_tokens_details")
    usage = {
        "input_tokens": _integer(usage_raw.get("input_tokens")),
        "cached_input_tokens": _integer(
            input_details.get("cached_tokens") if isinstance(input_details, dict) else None
        ),
        "output_tokens": _integer(usage_raw.get("output_tokens")),
        "reasoning_tokens": _integer(
            output_details.get("reasoning_tokens") if isinstance(output_details, dict) else None
        ),
        "total_tokens": _integer(usage_raw.get("total_tokens")),
    }
    incomplete = response.get("incomplete_details")
    finish_reason = (
        _optional_text(incomplete.get("reason")) if isinstance(incomplete, dict) else None
    )
    if finish_reason is None:
        finish_reason = _optional_text(response.get("status"))
    metadata = {
        "provider_response_id": _optional_text(response.get("id")),
        "model_returned": _optional_text(response.get("model")),
        "routed_provider": None,
        "system_fingerprint": None,
        "finish_reason": finish_reason,
    }
    return metadata, content, usage


def gemini_request_body(lane: Json, prompt: str, schema: Json) -> Json:
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            **response_format(lane, schema),
            "maxOutputTokens": int(lane["max_output_tokens"]),
            "thinkingConfig": {"thinkingLevel": str(lane["reasoning_effort"]).lower()},
        },
    }


def call_gemini(
    lane: Json, body: Json, api_key: str, timeout: float
) -> tuple[Json, str | None, Json]:
    url = str(lane["base_url"]).rstrip("/") + f"/models/{lane['model']}:generateContent"
    response = _http_json(url, body, {"x-goog-api-key": api_key}, timeout)
    try:
        candidate = response["candidates"][0]
        parts = candidate["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini response lacks candidates[0].content.parts") from exc
    content = "".join(
        str(part["text"])
        for part in parts
        if isinstance(part, dict)
        and part.get("thought") is not True
        and isinstance(part.get("text"), str)
    )
    usage_raw = response.get("usageMetadata")
    usage_raw = usage_raw if isinstance(usage_raw, dict) else {}
    output_tokens = _integer(usage_raw.get("candidatesTokenCount"))
    reasoning_tokens = _integer(usage_raw.get("thoughtsTokenCount"))
    usage = {
        "input_tokens": _integer(usage_raw.get("promptTokenCount")),
        "cached_input_tokens": _integer(usage_raw.get("cachedContentTokenCount")),
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": _integer(usage_raw.get("totalTokenCount")),
    }
    metadata = {
        "provider_response_id": _optional_text(response.get("responseId")),
        "model_returned": _optional_text(response.get("modelVersion")),
        "routed_provider": None,
        "system_fingerprint": None,
        "finish_reason": _optional_text(candidate.get("finishReason")),
    }
    return metadata, content or None, usage


def actual_cost_usd(usage: Json, lane: Json) -> float | None:
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    rates = ("input_usd_per_million", "cached_input_usd_per_million", "output_usd_per_million")
    if any(not isinstance(lane.get(key), (int, float)) for key in rates):
        return None
    cached = usage.get("cached_input_tokens")
    cached = cached if isinstance(cached, int) else 0
    cached = min(cached, input_tokens)
    billable_output = output_tokens
    if lane["api_kind"] == "gemini_generate_content":
        reasoning = usage.get("reasoning_tokens")
        if isinstance(reasoning, int):
            billable_output += reasoning
    return (
        (input_tokens - cached) * float(lane["input_usd_per_million"])
        + cached * float(lane["cached_input_usd_per_million"])
        + billable_output * float(lane["output_usd_per_million"])
    ) / 1_000_000


def verify_packet(packet: Json, plan: Json, dataset_dir: Path) -> list[Json]:
    expected = plan["prompt"]["expected_packet_sha256"]
    observed = packet.get("packet_sha256")
    if expected is not None:
        if observed != expected:
            fail("packet digest is not bound by the frozen plan")
    elif plan["prompt"].get("packet_binding") not in {
        "FROZEN_DATASET_PLUS_DETERMINISTIC_RENDERER",
        "FROZEN_GENERATOR_PLUS_FUTURE_BEACON_SEED_PLUS_DETERMINISTIC_RENDERER_PLUS_C1_RECEIPT",
    }:
        fail("packet lacks a registered deterministic binding rule")
    digest_payload = deepcopy(packet)
    digest_payload.pop("packet_sha256", None)
    recomputed = sha256_bytes(canonical_json(digest_payload).encode("utf-8"))
    if recomputed != observed:
        fail("packet content does not match its packet_sha256")
    if packet.get("selection_uses_model_outputs") is not False:
        fail("packet selection boundary changed")
    expected_dataset_manifest = plan["dataset"].get("dataset_manifest_sha256")
    if isinstance(expected_dataset_manifest, str):
        if packet.get("dataset_manifest_sha256") != expected_dataset_manifest:
            fail("packet dataset digest differs from the frozen plan")
    elif not (
        expected_dataset_manifest is None
        and plan.get("design", {}).get("dataset_manifest_bound_at_c1") is True
    ):
        fail("frozen plan lacks a dataset digest or registered C1 binding")
    for key in ("policy_sha256", "renderer_sha256", "decision_schema_sha256"):
        if packet.get(key) != plan["prompt"].get(key):
            fail(f"packet {key} differs from the frozen plan")
    records = packet.get("records")
    if not isinstance(records, list):
        fail("packet records must be a list")
    item_ids: set[str] = set()
    confirmatory_packet = plan.get("design", {}).get("confirmatory_inference_packet", False)
    for row in records:
        if not isinstance(row, dict):
            fail("packet record must be an object")
        item_id = str(row.get("item_id"))
        prompt = row.get("prompt")
        if item_id in item_ids:
            fail(f"duplicate packet item_id: {item_id}")
        if not isinstance(prompt, str):
            fail(f"packet prompt must be text: {item_id}")
        item_ids.add(item_id)
        encoded = prompt.encode("utf-8")
        if row.get("prompt_sha256") != sha256_bytes(encoded):
            fail(f"packet prompt hash mismatch: {item_id}")
        if row.get("utf8_bytes") != len(encoded):
            fail(f"packet prompt byte count mismatch: {item_id}")
        if confirmatory_packet:
            item = row.get("input_item")
            if not isinstance(item, dict) or str(item.get("id")) != item_id or "gold" in item:
                fail(f"confirmatory packet input boundary is malformed: {item_id}")
            if row.get("input_sha256") != sha256_bytes(canonical_json(item).encode("utf-8")):
                fail(f"confirmatory packet input digest mismatch: {item_id}")
    dataset_ids = {str(row["id"]) for row in load_jsonl(dataset_dir / "inputs.jsonl")}
    if item_ids != dataset_ids:
        fail("packet and dataset item IDs differ")
    return records


def verify_pilot_go(
    path: Path,
    lane: Json,
    packet: Json,
    frozen_plan_commit: str,
) -> None:
    rows = load_jsonl(path)
    expected_ids = {str(value) for value in packet["pilot_item_ids"]}
    packet_by_id = {str(value["item_id"]): value for value in packet["records"]}
    observed_ids: set[str] = set()
    for row in rows:
        item_id = str(row.get("item_id"))
        if item_id in observed_ids:
            fail(f"duplicate pilot item_id: {item_id}")
        observed_ids.add(item_id)
        validate_with_schema(row, RUN_SCHEMA, item_id)
        if row.get("lane_id") != lane["lane_id"] or row.get("phase") != "pilot":
            fail("full-run pilot evidence has the wrong lane or phase")
        if item_id not in packet_by_id:
            fail(f"full-run pilot item is absent from the packet: {item_id}")
        if row.get("prompt_sha256") != packet_by_id[item_id]["prompt_sha256"]:
            fail(f"full-run pilot prompt digest mismatch: {item_id}")
        if row.get("frozen_plan_commit") != frozen_plan_commit:
            fail(f"full-run pilot frozen-plan commit mismatch: {item_id}")
    if observed_ids != expected_ids:
        fail("full-run pilot evidence does not cover the frozen pilot IDs")
    transport_errors = sum(row["transport_status"] == "ERROR" for row in rows)
    parseable = sum(row["parse_status"] == "OK" for row in rows)
    if transport_errors != 0 or parseable < 10:
        fail(
            "formal full run is STOP-gated: pilot requires zero transport errors "
            "and at least 10 parseable decisions"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--phase", choices=("pilot", "full"), required=True)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--pilot-run", type=Path)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dataset_dir = args.dataset.resolve()
    plan_path = args.plan.resolve()
    plan = load_json(plan_path)
    verify_frozen_plan(plan_path, args.frozen_plan_commit.lower(), plan)
    lane, formal = find_lane(plan, args.lane_id)
    if args.phase == "full" and not formal:
        fail("exploratory subscription lanes cannot execute a full scored run")
    validate_dataset(dataset_dir, ROOT)
    expected_dataset_manifest = plan["dataset"].get("dataset_manifest_sha256")
    if isinstance(expected_dataset_manifest, str):
        if sha256_file(dataset_dir / "manifest.json") != expected_dataset_manifest:
            fail("dataset manifest differs from the frozen plan")
    elif not (
        expected_dataset_manifest is None
        and plan.get("design", {}).get("dataset_manifest_bound_at_c1") is True
    ):
        fail("frozen plan lacks a dataset digest or registered C1 binding")
    packet = load_json(args.packet.resolve())
    records = verify_packet(packet, plan, dataset_dir)
    requires_pilot = full_requires_pilot(plan)
    if args.phase == "pilot" and not requires_pilot:
        fail("the frozen plan disables pilot execution")
    if args.phase == "full" and formal:
        if requires_pilot:
            if args.pilot_run is None:
                fail("formal full run requires --pilot-run as GO-gate evidence")
            verify_pilot_go(args.pilot_run.resolve(), lane, packet, args.frozen_plan_commit.lower())
        elif args.pilot_run is not None:
            fail("the frozen no-pilot plan rejects --pilot-run evidence")
    selected_ids = set(packet["pilot_item_ids"]) if args.phase == "pilot" else None
    selected = [row for row in records if selected_ids is None or row["item_id"] in selected_ids]
    expected_count = (
        int(plan["pilot"]["instances"])
        if args.phase == "pilot"
        else int(plan["dataset"]["instances"])
    )
    if len(selected) != expected_count:
        fail(f"selected {len(selected)} records, expected {expected_count}")

    upper = conservative_upper_bound_usd(selected, lane)
    projected_lane_upper = upper
    cap = lane.get("spend_cap_usd")
    if formal:
        if upper is None or not isinstance(cap, (int, float)):
            fail("formal lane requires known prices and a numeric spend cap")
        if args.phase == "full" and requires_pilot:
            pilot_ids = {str(value) for value in packet["pilot_item_ids"]}
            pilot_packet = [row for row in records if str(row["item_id"]) in pilot_ids]
            pilot_upper = conservative_upper_bound_usd(pilot_packet, lane)
            if pilot_upper is None:
                fail("cannot bound cumulative pilot plus full-run cost")
            projected_lane_upper = upper + pilot_upper
        if projected_lane_upper > float(cap):
            fail(
                f"projected lane upper bound ${projected_lane_upper:.6f} exceeds "
                f"lane cap ${float(cap):.6f}"
            )

    auth_env = lane.get("auth_env")
    api_key = None
    if isinstance(auth_env, str):
        api_key = validate_api_key(os.environ.get(auth_env), auth_env)

    output_path = args.out.resolve()
    if output_path.exists():
        fail(f"refusing to overwrite existing output: {output_path}")
    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    if partial_path.exists():
        fail(f"partial output already exists: {partial_path}")

    decision_schema = provider_decision_schema(load_json(DECISION_SCHEMA))
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    policy = load_policy(ROOT / "policies" / str(dataset_manifest["policy_file"]))
    evaluation_time = str(dataset_manifest["evaluation_time"])
    items = {str(item["id"]): item for item in load_jsonl(dataset_dir / "inputs.jsonl")}
    completed: list[Json] = []
    accrued = 0.0
    initial_delay = float(lane.get("initial_request_delay_seconds", 0.0))
    minimum_interval = float(lane.get("minimum_request_interval_seconds", 0.0))
    if initial_delay < 0.0 or minimum_interval < 0.0:
        fail("request pacing values must be non-negative")
    if initial_delay:
        time.sleep(initial_delay)
    previous_request_start: float | None = None
    for packet_record in selected:
        if previous_request_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_request_start)
            if remaining > 0.0:
                time.sleep(remaining)
        item_id = str(packet_record["item_id"])
        item = items[item_id]
        request_started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        start = time.perf_counter()
        previous_request_start = start
        transport_status = "OK"
        transport_error = None
        content: str | None = None
        metadata: Json = {
            "provider_response_id": None,
            "model_returned": None,
            "routed_provider": None,
            "system_fingerprint": None,
            "finish_reason": None,
        }
        usage: Json = {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        if lane["api_kind"] == "openai_compatible":
            body = openai_request_body(lane, str(packet_record["prompt"]), decision_schema)
        elif lane["api_kind"] == "anthropic_messages":
            body = anthropic_request_body(lane, str(packet_record["prompt"]), decision_schema)
        elif lane["api_kind"] == "openai_responses":
            body = responses_request_body(lane, str(packet_record["prompt"]), decision_schema)
        elif lane["api_kind"] == "gemini_generate_content":
            body = gemini_request_body(lane, str(packet_record["prompt"]), decision_schema)
        else:
            fail(f"unsupported api_kind: {lane['api_kind']}")
        try:
            if lane["api_kind"] == "openai_compatible":
                metadata, content, usage = call_openai_compatible(lane, body, api_key, args.timeout)
            elif lane["api_kind"] == "anthropic_messages":
                if api_key is None:
                    fail("Anthropic Messages lane requires an API key")
                metadata, content, usage = call_anthropic_messages(
                    lane, body, api_key, args.timeout
                )
            elif lane["api_kind"] == "openai_responses":
                if api_key is None:
                    fail("OpenAI Responses lane requires an API key")
                metadata, content, usage = call_openai_responses(lane, body, api_key, args.timeout)
            elif lane["api_kind"] == "gemini_generate_content":
                if api_key is None:
                    fail("Gemini formal lane requires an API key")
                metadata, content, usage = call_gemini(lane, body, api_key, args.timeout)
        except RuntimeError as exc:
            transport_status = "ERROR"
            transport_error = str(exc)
        latency_ms = (time.perf_counter() - start) * 1000.0
        response_received = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        raw_response_sha = sha256_bytes(content.encode("utf-8")) if content is not None else None
        if transport_status == "ERROR":
            parse_status = "TRANSPORT_ERROR"
            raw_decision = None
            postgate = None
            parse_detail = transport_error
        elif content is None:
            parse_status = "SCHEMA_ERROR"
            raw_decision = None
            postgate = None
            parse_detail = "provider returned no final response text"
        else:
            parse_status, raw_decision, parse_detail = diagnose_provider_content(
                content,
                item,
                schema_path=DECISION_SCHEMA,
                allow_single_object_extraction=bool(
                    lane.get("allow_single_json_object_extraction", False)
                ),
            )
            postgate = (
                postgate_decision(raw_decision, item, policy, evaluation_time)
                if raw_decision is not None
                else None
            )

        cost = actual_cost_usd(usage, lane) if formal else None
        if cost is not None:
            accrued += cost
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": args.frozen_plan_commit.lower(),
            "packet_sha256": packet["packet_sha256"],
            "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
            "phase": args.phase,
            "lane_id": lane["lane_id"],
            "provider": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "model_family": lane["model_family"],
            "item_id": item_id,
            "pair_id": packet_record["pair_id"],
            "request_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
            "prompt_sha256": packet_record["prompt_sha256"],
            "response_format_sha256": sha256_bytes(
                canonical_json(response_format(lane, decision_schema)).encode("utf-8")
            ),
            "provider_response_id": metadata["provider_response_id"],
            "routed_provider": metadata["routed_provider"],
            "system_fingerprint": metadata["system_fingerprint"],
            "finish_reason": metadata["finish_reason"],
            "request_started_at_utc": request_started,
            "response_received_at_utc": response_received,
            "transport_status": transport_status,
            "transport_error": transport_error,
            "raw_response_text": content,
            "raw_response_sha256": raw_response_sha,
            "parse_status": parse_status,
            "parse_error_detail": parse_detail,
            "raw_decision": raw_decision,
            "postgate_decision": postgate,
            "latency_ms": latency_ms,
            "usage": usage,
            "actual_cost_usd": cost,
            "cost_status": "COMPUTED_FROM_HOST_USAGE" if cost is not None else "UNKNOWN",
            "evidence_ceiling": "COMPUTATIONAL" if formal else lane["evidence_ceiling"],
        }
        validate_with_schema(record, RUN_SCHEMA, item_id)
        completed.append(record)
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(partial_path, completed)
        if formal and isinstance(cap, (int, float)) and accrued > float(cap):
            fail(
                f"actual accrued cost ${accrued:.6f} exceeded lane cap after {item_id}; "
                f"partial evidence is at {partial_path}"
            )

    partial_path.replace(output_path)
    ok = sum(row["parse_status"] == "OK" for row in completed)
    errors = sum(row["transport_status"] == "ERROR" for row in completed)
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "lane_id": lane["lane_id"],
                "phase": args.phase,
                "records": len(completed),
                "parseable": ok,
                "transport_errors": errors,
                "conservative_upper_bound_usd": upper,
                "projected_cumulative_lane_upper_bound_usd": projected_lane_upper,
                "actual_cost_usd": accrued if formal else None,
                "cost_status": "COMPUTED_FROM_HOST_USAGE" if formal else "UNKNOWN",
                "out": str(output_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
