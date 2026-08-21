#!/usr/bin/env python3
"""Execute one C1-frozen service lane without dataset, gold, gate, pilot, or client retry."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.decision_validation import diagnose_decision  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
DECISION_SCHEMA = ROOT / "schemas" / "agent-decision.schema.json"
_REDACTED = "<REDACTED_HIDDEN_REASONING>"
_RESPONSE_HEADER_ALLOWLIST = {
    "content-type",
    "date",
    "request-id",
    "x-request-id",
    "cf-ray",
    "server",
}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"confirmatory-service-run: {message}")


def portable_decision_schema(schema: Json) -> Json:
    cleaned = deepcopy(schema)
    cleaned.pop("$schema", None)
    cleaned.pop("$id", None)
    cleaned.pop("title", None)
    definitions = cleaned.pop("$defs", {})
    state = definitions.get("state")
    proposed = cleaned.get("properties", {}).get("proposed_state")
    if not isinstance(state, dict) or not isinstance(proposed, dict):
        fail("decision schema state definition changed")
    cleaned["properties"]["proposed_state"] = deepcopy(state)

    def subset(value: Any) -> Any:
        unsupported = {"uniqueItems", "pattern", "minimum", "maximum"}
        if isinstance(value, dict):
            return {key: subset(child) for key, child in value.items() if key not in unsupported}
        if isinstance(value, list):
            return [subset(child) for child in value]
        return value

    return subset(cleaned)


def lane_by_id(plan: Json, lane_id: str) -> Json:
    for lane in plan.get("formal_lanes", []):
        if lane.get("lane_id") == lane_id:
            return lane
    fail(f"unknown confirmatory lane: {lane_id}")


def request_body_for_lane(lane: Json, prompt: str, schema: Json) -> Json:
    if lane["api_kind"] == "anthropic_messages":
        if lane.get("response_format") != "prompt_only_json":
            fail("confirmatory Messages lane must remain prompt-only JSON")
        return {
            "model": lane["model"],
            "max_tokens": int(lane["max_output_tokens"]),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
    if lane["api_kind"] == "openai_compatible":
        if lane.get("response_format") != "json_schema":
            fail("confirmatory chat-completions lane must retain strict JSON Schema")
        return {
            "model": lane["model"],
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                    "strict": True,
                    "schema": schema,
                },
            },
            "stream": False,
            "max_tokens": int(lane["max_output_tokens"]),
        }
    fail(f"unsupported confirmatory API kind: {lane['api_kind']}")


def request_headers_template(lane: Json) -> Json:
    base = {
        "Content-Type": "application/json",
        "User-Agent": "ClaimPromoteBench-Confirmatory/1",
        "Authorization": "<REDACTED_CREDENTIAL>",
    }
    if lane["api_kind"] == "anthropic_messages":
        base["x-api-key"] = "<REDACTED_CREDENTIAL>"
        base["anthropic-version"] = "2023-06-01"
    return base


def endpoint_for_lane(lane: Json) -> str:
    suffix = "/messages" if lane["api_kind"] == "anthropic_messages" else "/chat/completions"
    return str(lane["base_url"]).rstrip("/") + suffix


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _actual_headers(template: Json, api_key: str) -> dict[str, str]:
    return {
        str(key): api_key if value == "<REDACTED_CREDENTIAL>" else str(value)
        for key, value in template.items()
    }


def _safe_response_headers(headers: Any) -> Json:
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in _RESPONSE_HEADER_ALLOWLIST
    }


def post_once(
    url: str,
    body: Json,
    headers_template: Json,
    api_key: str,
    timeout_seconds: float,
) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers=_actual_headers(headers_template, api_key),
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read()
            return {
                "http_status": int(response.status),
                "response_headers": _safe_response_headers(response.headers),
                "raw_body": raw,
                "network_error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "http_status": int(exc.code),
            "response_headers": _safe_response_headers(exc.headers),
            "raw_body": exc.read(),
            "network_error": None,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "http_status": None,
            "response_headers": {},
            "raw_body": None,
            "network_error": f"{type(exc).__name__}: {exc}",
        }


def _sanitize_envelope(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("thought") is True:
            return {
                key: (_REDACTED if key == "text" else _sanitize_envelope(child))
                for key, child in value.items()
            }
        hidden = {"reasoning_content", "thinking_content", "thoughts"}
        return {
            key: (_REDACTED if key in hidden else _sanitize_envelope(child))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_envelope(child) for child in value]
    return value


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def extract_provider_result(lane: Json, envelope: Json) -> tuple[Json, str | None, Json]:
    if envelope.get("error") is not None:
        raise ValueError(f"provider error envelope: {envelope['error']}")
    if lane["api_kind"] == "anthropic_messages":
        blocks = envelope.get("content")
        if not isinstance(blocks, list):
            raise ValueError("provider envelope lacks Messages content blocks")
        text_blocks = [
            str(block["text"])
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
            and block.get("thought") is not True
        ]
        usage_raw = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
        input_tokens = _integer(usage_raw.get("input_tokens"))
        output_tokens = _integer(usage_raw.get("output_tokens"))
        usage = {
            "input_tokens": input_tokens,
            "cached_input_tokens": _integer(usage_raw.get("cache_read_input_tokens")),
            "output_tokens": output_tokens,
            "reasoning_tokens": None,
            "total_tokens": (
                input_tokens + output_tokens
                if isinstance(input_tokens, int) and isinstance(output_tokens, int)
                else None
            ),
        }
        metadata = {
            "provider_response_id": envelope.get("id"),
            "model_returned": envelope.get("model"),
            "finish_reason": envelope.get("stop_reason"),
            "routed_provider": envelope.get("provider"),
            "system_fingerprint": envelope.get("system_fingerprint"),
        }
        return metadata, "".join(text_blocks) or None, usage
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("provider envelope lacks chat-completions choices[0]")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("provider envelope lacks chat-completions message")
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise ValueError("provider final content is not text")
    usage_raw = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
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
        "provider_response_id": envelope.get("id"),
        "model_returned": envelope.get("model"),
        "finish_reason": choice.get("finish_reason"),
        "routed_provider": envelope.get("provider"),
        "system_fingerprint": envelope.get("system_fingerprint"),
    }
    return metadata, content, usage


def _single_json_object(content: str) -> str | None:
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, character in enumerate(content):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(content[start : index + 1])
                start = None
    return candidates[0] if len(candidates) == 1 and depth == 0 else None


def diagnose_content(
    content: str, item: Json, allow_extraction: bool
) -> tuple[str, Json | None, str | None]:
    status, decision, detail = diagnose_decision(content, item, schema_path=DECISION_SCHEMA)
    if status != "JSON_SYNTAX_ERROR" or not allow_extraction:
        return status, decision, detail
    extracted = _single_json_object(content)
    if extracted is None:
        return status, decision, detail
    status, decision, detail = diagnose_decision(extracted, item, schema_path=DECISION_SCHEMA)
    marker = "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
    return status, decision, marker if detail is None else f"{marker}: {detail}"


def _actual_cost(usage: Json, lane: Json) -> float | None:
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    cached = usage.get("cached_input_tokens")
    cached = min(cached, input_tokens) if isinstance(cached, int) else 0
    return (
        (input_tokens - cached) * float(lane["input_usd_per_million"])
        + cached * float(lane["cached_input_usd_per_million"])
        + output_tokens * float(lane["output_usd_per_million"])
    ) / 1_000_000


def _append_durable(path: Path, record: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _verify_frozen_plan(plan_path: Path, commit: str) -> None:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        fail("frozen plan commit must be a full lowercase Git SHA")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if exists.returncode != 0:
        fail("frozen source commit is absent from checkout history")
    relative = plan_path.resolve().relative_to(ROOT).as_posix()
    shown = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0 or shown.stdout != plan_path.read_bytes():
        fail("current plan bytes differ from the supplied frozen commit")


def _verify_c1_and_source(
    commitment_path: Path,
    plan_path: Path,
    plan: Json,
    packet: Json,
    schedule: Json,
    source_commit: str,
    baselines_path: Path | None,
) -> None:
    commitment = load_json(commitment_path)
    commitment_payload = deepcopy(commitment)
    observed_commitment_sha = commitment_payload.pop("commitment_sha256", None)
    if observed_commitment_sha != sha256_bytes(canonical_json(commitment_payload).encode("utf-8")):
        fail("public C1 commitment self-digest mismatch")
    if (
        commitment.get("study_id") != plan.get("study_id")
        or commitment.get("source_commit") != source_commit
    ):
        fail("public C1 commitment differs from the frozen study or source commit")
    c1 = commitment.get("c1_receipt")
    if not isinstance(c1, dict):
        fail("public C1 commitment lacks its receipt")
    c1_payload = deepcopy(c1)
    observed_c1_sha = c1_payload.pop("c1_receipt_sha256", None)
    if observed_c1_sha != sha256_bytes(canonical_json(c1_payload).encode("utf-8")):
        fail("public C1 receipt self-digest mismatch")
    packet_payload = deepcopy(packet)
    observed_packet_sha = packet_payload.pop("packet_sha256", None)
    if observed_packet_sha != sha256_bytes(canonical_json(packet_payload).encode("utf-8")):
        fail("C1 packet self-digest mismatch")
    schedule_payload = deepcopy(schedule)
    observed_schedule_sha = schedule_payload.pop("schedule_sha256", None)
    if observed_schedule_sha != sha256_bytes(canonical_json(schedule_payload).encode("utf-8")):
        fail("C1 request schedule self-digest mismatch")
    if (
        c1.get("plan_file_sha256") != sha256_file(plan_path)
        or c1.get("packet_sha256") != observed_packet_sha
        or c1.get("schedule_sha256") != observed_schedule_sha
        or c1.get("planned_cells") != 600
        or schedule.get("planned_cells") != 600
        or schedule.get("study_id") != plan.get("study_id")
        or schedule.get("packet_sha256") != observed_packet_sha
    ):
        fail("C1 receipt, packet, schedule, or plan binding mismatch")
    records = packet.get("records")
    cells = schedule.get("cells")
    if not isinstance(records, list) or len(records) != 300:
        fail("C1 packet does not contain exactly 300 records")
    if not isinstance(cells, list) or len(cells) != 600:
        fail("C1 schedule does not contain exactly 600 cells")
    packet_by_id = {str(row["item_id"]): row for row in records}
    if len(packet_by_id) != 300:
        fail("C1 packet item identifiers are not unique")
    request_hashes: list[str] = []
    cell_ids: set[str] = set()
    for cell in cells:
        item_id = str(cell.get("item_id"))
        lane_id = str(cell.get("lane_id"))
        cell_id = f"{lane_id}/{item_id}"
        record = packet_by_id.get(item_id)
        if cell_id in cell_ids or record is None:
            fail("C1 schedule has a duplicate cell or unknown packet item")
        cell_ids.add(cell_id)
        if (
            cell.get("prompt_sha256") != record.get("prompt_sha256")
            or cell.get("pair_id") != record.get("pair_id")
            or cell.get("request_body_sha256")
            != sha256_bytes(canonical_json(cell.get("request_body")).encode("utf-8"))
        ):
            fail(f"C1 request binding mismatch: {cell_id}")
        request_hashes.append(str(cell["request_body_sha256"]))
    if c1.get("request_body_hash_set_sha256") != sha256_bytes(
        canonical_json(sorted(request_hashes)).encode("utf-8")
    ):
        fail("C1 request-body hash-set binding mismatch")
    if baselines_path is not None:
        baselines = load_json(baselines_path)
        baseline_payload = deepcopy(baselines)
        observed_baseline_sha = baseline_payload.pop("predictions_sha256", None)
        if observed_baseline_sha != sha256_bytes(canonical_json(baseline_payload).encode("utf-8")):
            fail("C1 baseline prediction self-digest mismatch")
        if (
            observed_baseline_sha != c1.get("baseline_predictions_sha256")
            or baselines.get("packet_sha256") != observed_packet_sha
            or baselines.get("contains_test_gold") is not False
        ):
            fail("C1 baseline prediction binding mismatch")
    source_files = commitment.get("source_files_sha256")
    if not isinstance(source_files, dict) or not source_files:
        fail("public C1 commitment lacks source-file bindings")
    for relative, expected in source_files.items():
        shown = subprocess.run(
            ["git", "show", f"{source_commit}:{relative}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        current = ROOT / str(relative)
        if (
            shown.returncode != 0
            or sha256_bytes(shown.stdout) != expected
            or not current.is_file()
            or sha256_file(current) != expected
        ):
            fail(f"C1 source-file binding mismatch: {relative}")


def _validate_key(value: str | None, env_name: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(ord(char) < 33 or ord(char) > 126 for char in value)
    ):
        fail(f"credential is missing or malformed: {env_name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--baselines", type=Path)
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    plan_path = args.plan.resolve()
    plan = load_json(plan_path)
    _verify_frozen_plan(plan_path, args.frozen_plan_commit.lower())
    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("confirmatory plan is not frozen")
    if plan.get("design", {}).get("full_requires_pilot") is not False:
        fail("confirmatory plan unexpectedly enables a pilot")
    lane = lane_by_id(plan, args.lane_id)
    packet = load_json(args.packet.resolve())
    schedule = load_json(args.schedule.resolve())
    if args.preflight_only and args.baselines is None:
        fail("preflight requires the C1 baseline predictions")
    _verify_c1_and_source(
        args.commitment.resolve(),
        plan_path,
        plan,
        packet,
        schedule,
        args.frozen_plan_commit.lower(),
        args.baselines.resolve() if args.baselines is not None else None,
    )
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    cells = [row for row in schedule["cells"] if row["lane_id"] == lane["lane_id"]]
    if len(cells) != 300 or len({str(row["item_id"]) for row in cells}) != 300:
        fail("C1 schedule does not contain exactly 300 unique lane cells")
    if (
        args.journal.exists()
        or args.out.exists()
        or args.out.with_suffix(args.out.suffix + ".partial").exists()
    ):
        fail("refusing a retry, resume, or output overwrite")
    if args.preflight_only:
        print(
            json.dumps(
                {
                    "status": "GOLD_FREE_CREDENTIAL_FREE_PREFLIGHT_PASS",
                    "study_id": plan["study_id"],
                    "source_commit": args.frozen_plan_commit.lower(),
                    "lane_id": lane["lane_id"],
                    "planned_lane_cells": len(cells),
                    "application_posts": 0,
                },
                sort_keys=True,
            )
        )
        return 0
    auth_env = str(lane["auth_env"])
    api_key = _validate_key(os.environ.get(auth_env), auth_env)
    timeout_seconds = float(lane["timeout_seconds"])
    minimum_interval = float(lane["minimum_request_interval_seconds"])
    if timeout_seconds <= 0 or minimum_interval < 0:
        fail("invalid frozen timeout or pacing")
    partial = args.out.with_suffix(args.out.suffix + ".partial")
    previous_start: float | None = None
    for sequence, cell in enumerate(cells):
        if previous_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_start)
            if remaining > 0:
                time.sleep(remaining)
        item_id = str(cell["item_id"])
        packet_record = packet_by_id.get(item_id)
        if packet_record is None or not isinstance(packet_record.get("input_item"), dict):
            fail(f"inference-only packet lacks the registered input: {item_id}")
        body = cell["request_body"]
        if cell["request_body_sha256"] != sha256_bytes(canonical_json(body).encode("utf-8")):
            fail(f"C1 request-body digest mismatch: {item_id}")
        intent_time = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _append_durable(
            args.journal,
            {
                "schema_version": "1.0.0",
                "event": "POST_INTENT",
                "study_id": plan["study_id"],
                "frozen_plan_commit": args.frozen_plan_commit.lower(),
                "schedule_sha256": schedule["schedule_sha256"],
                "lane_id": lane["lane_id"],
                "sequence": sequence,
                "item_id": item_id,
                "pair_id": cell["pair_id"],
                "request_body_sha256": cell["request_body_sha256"],
                "intent_at_utc": intent_time,
            },
        )
        start = time.perf_counter()
        previous_start = start
        response = post_once(
            endpoint_for_lane(lane),
            body,
            cell["request_headers_template"],
            api_key,
            timeout_seconds,
        )
        received = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        raw_body = response["raw_body"]
        raw_body_sha = sha256_bytes(raw_body) if isinstance(raw_body, bytes) else None
        envelope: Json | None = None
        sanitized_envelope: Json | None = None
        metadata: Json = {
            "provider_response_id": None,
            "model_returned": None,
            "finish_reason": None,
            "routed_provider": None,
            "system_fingerprint": None,
        }
        content: str | None = None
        usage: Json = {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        http_status = response["http_status"]
        if response["network_error"] is not None:
            parse_status = "TRANSPORT_ERROR"
            parse_detail = response["network_error"]
            raw_decision = None
        elif not isinstance(http_status, int) or not 200 <= http_status < 300:
            parse_status = (
                "REDIRECT_ERROR"
                if isinstance(http_status, int) and 300 <= http_status < 400
                else "HTTP_ERROR"
            )
            parse_detail = f"HTTP {http_status}"
            raw_decision = None
        else:
            try:
                decoded = json.loads(raw_body)
                if not isinstance(decoded, dict):
                    raise ValueError("provider envelope is not a JSON object")
                envelope = decoded
                sanitized_envelope = _sanitize_envelope(envelope)
                metadata, content, usage = extract_provider_result(lane, envelope)
                if content is None:
                    parse_status, raw_decision, parse_detail = (
                        "SCHEMA_ERROR",
                        None,
                        "provider returned no final response text",
                    )
                else:
                    parse_status, raw_decision, parse_detail = diagnose_content(
                        content,
                        packet_record["input_item"],
                        bool(lane.get("allow_single_json_object_extraction", False)),
                    )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                parse_status = "PROVIDER_ENVELOPE_ERROR"
                parse_detail = f"{type(exc).__name__}: {exc}"
                raw_decision = None
        cost = _actual_cost(usage, lane)
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": args.frozen_plan_commit.lower(),
            "schedule_sha256": schedule["schedule_sha256"],
            "packet_sha256": packet["packet_sha256"],
            "lane_id": lane["lane_id"],
            "provider_service": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "sequence": sequence,
            "item_id": item_id,
            "pair_id": cell["pair_id"],
            "prompt_sha256": packet_record["prompt_sha256"],
            "request_body": body,
            "request_body_sha256": cell["request_body_sha256"],
            "request_headers_template": cell["request_headers_template"],
            "endpoint": endpoint_for_lane(lane),
            "application_post_count": 1,
            "client_retry_count": 0,
            "redirect_followed": False,
            "request_intent_at_utc": intent_time,
            "response_received_at_utc": received,
            "latency_ms": (time.perf_counter() - start) * 1000.0,
            "http_status": http_status,
            "response_headers": response["response_headers"],
            "network_error": response["network_error"],
            "raw_http_body_sha256": raw_body_sha,
            "sanitized_provider_envelope": sanitized_envelope,
            "sanitized_provider_envelope_sha256": (
                sha256_bytes(canonical_json(sanitized_envelope).encode("utf-8"))
                if sanitized_envelope is not None
                else None
            ),
            "raw_final_text": content,
            "raw_final_text_sha256": (
                sha256_bytes(content.encode("utf-8")) if content is not None else None
            ),
            "provider_response_id": metadata["provider_response_id"],
            "routed_provider": metadata["routed_provider"],
            "system_fingerprint": metadata["system_fingerprint"],
            "finish_reason": metadata["finish_reason"],
            "parse_status": parse_status,
            "parse_detail": parse_detail,
            "raw_decision": raw_decision,
            "usage": usage,
            "actual_cost_usd": cost,
            "evidence_ceiling": "COMPUTATIONAL_SERVICE_CONFIGURATION",
            "contains_gold": False,
            "deterministic_gate_applied": False,
        }
        _append_durable(partial, record)
    partial.replace(args.out)
    print(
        json.dumps(
            {
                "status": "CONFIRMATORY_LANE_COMPLETE",
                "lane_id": lane["lane_id"],
                "planned_cells": 300,
                "application_posts": 300,
                "client_retries": 0,
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
