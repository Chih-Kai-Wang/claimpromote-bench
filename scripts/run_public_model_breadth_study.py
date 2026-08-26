#!/usr/bin/env python3
"""Execute the frozen public model-breadth schedule exactly once with durable intents."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_public_model_breadth_study import request_body  # noqa: E402
from run_stronger_model_study import (  # noqa: E402
    actual_cost_usd,
    diagnose_provider_content,
    sanitize_durable_provider_text,
    validate_api_key,
)
from validate_public_model_breadth_study import validate_study  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.v2 import postgate_decision  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
DECISION_SCHEMA = ROOT / "schemas" / "agent-decision.schema.json"
RESPONSE_ID = re.compile(
    r"(?i)(request[_ -]?id|response[_ -]?id|trace[_ -]?id)([\"':= ]+)[A-Za-z0-9._-]+"
)


def fail(message: str) -> None:
    raise SystemExit(f"public-model-breadth-run: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def append_durable(path: Path, payload: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (canonical_json(payload) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_durable_json(path: Path, payload: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def atomic_output_directory(out_dir: Path) -> Iterator[Path]:
    """Publish completed outputs with one directory rename.

    A failure leaves only a uniquely named staging directory. The requested output
    path therefore remains available to the credential-free interruption finalizer.
    """

    if out_dir.exists():
        fail(f"output directory already exists: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.building-", dir=out_dir.parent))
    try:
        yield staging
    except BaseException:
        raise
    else:
        os.replace(staging, out_dir)


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


def _http_json(url: str, body: Json, headers: dict[str, str], timeout: float) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ClaimPromoteBench-PublicBreadth/1",
            **headers,
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except (OSError, http.client.HTTPException) as exc:
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


def call_openai_compatible(
    lane: Json, body: Json, api_key: str, timeout: float
) -> tuple[Json, str | None, Json]:
    response = _http_json(
        str(lane["base_url"]).rstrip("/") + "/chat/completions",
        body,
        {"Authorization": f"Bearer {api_key}"},
        timeout,
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("provider response lacks choices[0].message")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("provider response lacks choices[0].message")
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
        "model_returned": response.get("model") if isinstance(response.get("model"), str) else None,
        "routed_provider": (
            response.get("provider") if isinstance(response.get("provider"), str) else None
        ),
        "finish_reason": (
            choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None
        ),
    }
    return metadata, content, usage


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
    content = (
        "".join(
            str(block["text"])
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        or None
    )
    usage_raw = response.get("usage") if isinstance(response.get("usage"), dict) else {}
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
        "model_returned": response.get("model") if isinstance(response.get("model"), str) else None,
        "routed_provider": None,
        "finish_reason": (
            response.get("stop_reason") if isinstance(response.get("stop_reason"), str) else None
        ),
    }
    return metadata, content, usage


def sanitize_text(value: str | None, api_key: str) -> str | None:
    if value is None:
        return None
    cleaned = sanitize_durable_provider_text(value.replace(api_key, "<REDACTED_CREDENTIAL>"))
    if cleaned is None:
        return None
    return RESPONSE_ID.sub(r"\1\2<REDACTED_PROVIDER_ID>", cleaned)


def verify_frozen_plan(plan_path: Path, frozen_commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", frozen_commit):
        fail("frozen plan commit must be a full lowercase Git SHA")
    try:
        relative = plan_path.relative_to(ROOT).as_posix()
    except ValueError:
        fail("study plan must be inside the repository")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", frozen_commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        fail("frozen plan commit is not an ancestor of HEAD")
    shown = subprocess.run(
        ["git", "show", f"{frozen_commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0 or shown.stdout != plan_path.read_bytes():
        fail("current study plan bytes differ from the frozen commit")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()

    os.umask(0o077)
    plan_path = args.plan.resolve()
    schedule_path = args.schedule.resolve()
    packet_path = args.packet.resolve()
    dataset_dir = args.dataset.resolve()
    frozen_commit = args.frozen_plan_commit.lower()
    verify_frozen_plan(plan_path, frozen_commit)
    validate_study(plan_path, schedule_path, packet_path)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(packet_path)
    api_key = validate_api_key(os.environ.get("OPENCODE_GO_API_KEY"), "OPENCODE_GO_API_KEY")

    journal_dir = args.journal_dir.resolve()
    out_dir = args.out_dir.resolve()
    if journal_dir.exists() or out_dir.exists():
        fail("journal or output directory already exists; partial resume is forbidden")
    journal_dir.mkdir(parents=True, mode=0o700)
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    started_at = utc_now()
    write_durable_json(
        journal_dir / "run-start.json",
        {
            "schema_version": "1.0.0",
            "status": "EXECUTION_STARTED",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "planned_cells": schedule["planned_cells"],
            "credentials_retained": False,
        },
    )

    records_by_id = {str(row["item_id"]): row for row in packet["records"]}
    items = {str(row["id"]): row for row in load_jsonl(dataset_dir / "inputs.jsonl")}
    manifest = load_json(dataset_dir / "manifest.json")
    policy = load_policy(ROOT / "policies" / str(manifest["policy_file"]))
    evaluation_time = str(manifest["evaluation_time"])
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    schema_hash = sha256_bytes(canonical_json({}).encode("utf-8"))
    timeout = float(
        args.timeout if args.timeout is not None else plan["execution"]["default_timeout_seconds"]
    )
    minimum_interval = float(plan["execution"]["minimum_global_request_interval_seconds"])
    previous_request_start: float | None = None
    completed: list[Json] = []
    lane_records: dict[str, list[Json]] = defaultdict(list)

    for cell in schedule["cells"]:
        if previous_request_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_request_start)
            if remaining > 0:
                time.sleep(remaining)
        sequence = int(cell["sequence"])
        cell_id = str(cell["cell_id"])
        lane_id = str(cell["lane_id"])
        item_id = str(cell["item_id"])
        lane = lanes[lane_id]
        packet_record = records_by_id[item_id]
        body = request_body(lane, str(packet_record["prompt"]))
        request_sha = sha256_bytes(canonical_json(body).encode("utf-8"))
        if request_sha != cell["request_body_sha256"]:
            fail(f"request body differs from frozen schedule: {cell_id}")

        intent_at = utc_now()
        append_durable(
            intents_path,
            {
                "schema_version": "1.0.0",
                "study_id": plan["study_id"],
                "frozen_plan_commit": frozen_commit,
                "sequence": sequence,
                "cell_id": cell_id,
                "lane_id": lane_id,
                "item_id": item_id,
                "request_body_sha256": request_sha,
                "intent_at_utc": intent_at,
                "application_posts_authorized_for_cell": 1,
                "client_retries_authorized": 0,
            },
        )
        previous_request_start = time.perf_counter()
        transport_status = "OK"
        transport_error: str | None = None
        content: str | None = None
        metadata: Json = {"model_returned": None, "routed_provider": None, "finish_reason": None}
        usage: Json = {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        try:
            if lane["api_kind"] == "openai_compatible":
                metadata, content, usage = call_openai_compatible(lane, body, api_key, timeout)
            elif lane["api_kind"] == "anthropic_messages":
                metadata, content, usage = call_anthropic_messages(lane, body, api_key, timeout)
            else:
                fail(f"unsupported adapter after validation: {lane['api_kind']}")
        except RuntimeError as exc:
            transport_status = "ERROR"
            transport_error = sanitize_text(str(exc), api_key)
        latency_ms = (time.perf_counter() - previous_request_start) * 1000.0
        response_at = utc_now()
        content = sanitize_text(content, api_key)
        raw_response_sha = sha256_bytes(content.encode("utf-8")) if content is not None else None
        item = items[item_id]
        if transport_status == "ERROR":
            parse_status = "TRANSPORT_ERROR"
            parse_detail = transport_error
            raw_decision = None
            postgate = None
        elif content is None:
            parse_status = "SCHEMA_ERROR"
            parse_detail = "provider returned no final response text"
            raw_decision = None
            postgate = None
        else:
            parse_status, raw_decision, parse_detail = diagnose_provider_content(
                content,
                item,
                schema_path=DECISION_SCHEMA,
                allow_single_object_extraction=True,
            )
            parse_detail = sanitize_text(parse_detail, api_key)
            postgate = (
                postgate_decision(raw_decision, item, policy, evaluation_time)
                if raw_decision is not None
                else None
            )
        quota_value = actual_cost_usd(usage, lane)
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "packet_sha256": packet["packet_sha256"],
            "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
            "phase": "full",
            "lane_id": lane_id,
            "provider": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "model_family": lane["model_family"],
            "item_id": item_id,
            "pair_id": packet_record["pair_id"],
            "request_sha256": request_sha,
            "prompt_sha256": packet_record["prompt_sha256"],
            "response_format_sha256": schema_hash,
            "provider_response_id": None,
            "routed_provider": metadata["routed_provider"],
            "system_fingerprint": None,
            "finish_reason": metadata["finish_reason"],
            "request_started_at_utc": intent_at,
            "response_received_at_utc": response_at,
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
            "actual_cost_usd": quota_value,
            "cost_status": "COMPUTED_FROM_HOST_USAGE" if quota_value is not None else "UNKNOWN",
            "evidence_ceiling": "COMPUTATIONAL",
        }
        validate_with_schema(record, RUN_SCHEMA, cell_id)
        append_durable(
            terminals_path,
            {
                "schema_version": "1.0.0",
                "sequence": sequence,
                "cell_id": cell_id,
                "record": record,
            },
        )
        completed.append(record)
        lane_records[lane_id].append(record)
        if (sequence + 1) % 20 == 0 or sequence + 1 == int(schedule["planned_cells"]):
            print(
                canonical_json(
                    {
                        "status": "RUNNING",
                        "completed_cells": sequence + 1,
                        "planned_cells": schedule["planned_cells"],
                        "parseable_cells": sum(row["parse_status"] == "OK" for row in completed),
                        "transport_error_cells": sum(
                            row["transport_status"] == "ERROR" for row in completed
                        ),
                    }
                ),
                flush=True,
            )

    if len(completed) != int(schedule["planned_cells"]):
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging_dir:
        output_hashes: Json = {}
        lane_summaries: list[Json] = []
        for lane_id in plan["execution"]["base_lane_order"]:
            path = staging_dir / f"{lane_id}.jsonl"
            records = lane_records[str(lane_id)]
            if len(records) != 180:
                fail(f"lane does not contain 180 terminal records: {lane_id}")
            write_jsonl(path, records)
            output_hashes[path.name] = sha256_file(path)
            lane_summaries.append(
                {
                    "lane_id": lane_id,
                    "records": len(records),
                    "parseable": sum(row["parse_status"] == "OK" for row in records),
                    "transport_errors": sum(row["transport_status"] == "ERROR" for row in records),
                }
            )
        receipt = {
            "schema_version": "1.0.0",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "planned_cells": schedule["planned_cells"],
            "durable_request_intents": len(completed),
            "durable_terminal_records": len(completed),
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "credentials_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_blocks_retained": False,
            "request_intent_journal_sha256": sha256_file(intents_path),
            "terminal_journal_sha256": sha256_file(terminals_path),
            "lane_output_sha256": output_hashes,
            "lanes": lane_summaries,
        }
        write_durable_json(staging_dir / "execution-receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "out_dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
