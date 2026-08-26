#!/usr/bin/env python3
"""Run one frozen local-model replacement study once, without retries or resume."""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import mlx.core as mx  # noqa: E402
from frozen_run_io import (  # noqa: E402
    append_durable,
    atomic_output_directory,
    verify_frozen_plan,
    write_durable_json,
)
from huggingface_hub import snapshot_download  # noqa: E402
from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    DATASETS,
    REPLACEMENT_VERSION,
    VOID_RECEIPT_PATH,
    format_chat_prompt,
    generation_request,
    lane_id,
    load_catalog,
    tokenizer_config,
)
from mlx_lm import load, stream_generate  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402
from synthetic_policy_output import diagnose_content, utc_now  # noqa: E402
from validate_local_model_replications import validate_all  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "local-model-run-record.schema.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"
BASE_POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"


def fail(message: str) -> None:
    raise SystemExit(f"local-model-run: {message}")


def sanitized_exception(exc: Exception) -> str:
    value = f"{type(exc).__name__}: {str(exc)[:1000]}"
    for private_path in (str(ROOT), str(Path.home())):
        value = value.replace(private_path, "<LOCAL_PATH>")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-key", choices=tuple(DATASETS), required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    parser.add_argument("--void-receipt", type=Path, default=VOID_RECEIPT_PATH)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    os.umask(0o077)
    dataset_key = args.dataset_key
    freeze_root = args.freeze_root.resolve()
    study_root = freeze_root / dataset_key
    plan_path = study_root / "study-plan.json"
    schedule_path = study_root / "request-schedule.json"
    catalog_path = args.catalog.resolve()
    snapshot_receipt = args.snapshot_receipt.resolve()
    qualification_receipt = args.qualification_receipt.resolve()
    void_receipt = args.void_receipt.resolve()
    frozen_commit = args.frozen_plan_commit.lower()
    verify_frozen_plan(plan_path, frozen_commit)
    verify_frozen_plan(schedule_path, frozen_commit)
    validate_all(
        freeze_root,
        catalog_path,
        snapshot_receipt,
        qualification_receipt,
        void_receipt,
    )

    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    catalog = load_catalog(catalog_path)
    spec = DATASETS[dataset_key]
    dataset_root = Path(spec["dataset_root"])
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    item_rows = load_jsonl(dataset_root / "evaluation-items.jsonl")
    items = {str(row["id"]): row["model_visible"] for row in item_rows}
    packet_rows = {str(row["item_id"]): row for row in packet["records"]}
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    catalog_lanes = {lane_id(lane, dataset_key): lane for lane in catalog["lanes"]}
    planned_lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    if set(catalog_lanes) != set(planned_lanes):
        fail("catalog and frozen plan lane sets differ")

    journal_dir = args.journal_dir.resolve()
    out_dir = args.out_dir.resolve()
    if journal_dir.exists() or out_dir.exists():
        fail("journal or output directory already exists; resume and overwrite are forbidden")
    journal_dir.mkdir(parents=True, mode=0o700)
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    started_at = utc_now()
    write_durable_json(
        journal_dir / "run-start.json",
        {
            "schema_version": "1.0.0",
            "status": "EXECUTION_STARTED",
            "replacement_version": REPLACEMENT_VERSION,
            "prior_ineligible_application_invocations": 1,
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "planned_cells": 240,
            "credentials_retained": False,
        },
    )

    sampler = make_sampler(temp=0.0, top_p=0.0)
    shared = catalog["shared_generation"]
    schema_hash = sha256_file(DECISION_SCHEMA)
    manifest_hash = sha256_file(dataset_root / "manifest.json")
    completed: list[Json] = []
    lane_records: dict[str, list[Json]] = defaultdict(list)
    schedule_by_lane: dict[str, list[Json]] = defaultdict(list)
    for cell in schedule["cells"]:
        schedule_by_lane[str(cell["lane_id"])].append(cell)

    for current_lane_id in plan["execution"]["base_lane_order"]:
        lane = catalog_lanes[str(current_lane_id)]
        snapshot = snapshot_download(
            repo_id=lane["model_repo"],
            revision=lane["model_revision"],
            local_files_only=True,
        )
        try:
            model, tokenizer = load(
                snapshot,
                tokenizer_config=tokenizer_config(lane),
                lazy=False,
            )
        except Exception as exc:  # pragma: no cover - hardware/runtime boundary
            fail(f"frozen model failed to load; study is ineligible: {sanitized_exception(exc)}")
        for cell in schedule_by_lane[str(current_lane_id)]:
            sequence = int(cell["sequence"])
            item_id = str(cell["item_id"])
            packet_row = packet_rows[item_id]
            formatted = format_chat_prompt(tokenizer, str(packet_row["prompt"]))
            request = generation_request(lane, formatted, shared)
            request_hash = sha256_bytes(canonical_json(request).encode("utf-8"))
            if (
                request_hash != cell["request_body_sha256"]
                or sha256_bytes(formatted.encode("utf-8")) != cell["formatted_prompt_sha256"]
            ):
                fail(f"rendered request differs from frozen schedule: {cell['cell_id']}")

            requested_at = utc_now()
            append_durable(
                intents_path,
                {
                    "schema_version": "1.0.0",
                    "study_id": plan["study_id"],
                    "frozen_plan_commit": frozen_commit,
                    "sequence": sequence,
                    "cell_id": cell["cell_id"],
                    "lane_id": current_lane_id,
                    "item_id": item_id,
                    "request_body_sha256": request_hash,
                    "intent_at_utc": requested_at,
                    "application_posts_authorized_for_cell": 1,
                    "client_retries_authorized": 0,
                },
            )
            started = time.perf_counter()
            transport_status = "OK"
            transport_error: str | None = None
            content: str | None = None
            finish_reason: str | None = None
            prompt_tokens: int | None = None
            output_tokens: int | None = None
            peak_memory_gb: float | None = None
            try:
                chunks: list[str] = []
                last_response: Any = None
                for response in stream_generate(
                    model,
                    tokenizer,
                    prompt=formatted,
                    max_tokens=int(shared["max_output_tokens"]),
                    sampler=sampler,
                ):
                    chunks.append(response.text)
                    last_response = response
                content = "".join(chunks)
                if last_response is not None:
                    finish_reason = last_response.finish_reason
                    prompt_tokens = int(last_response.prompt_tokens)
                    output_tokens = int(last_response.generation_tokens)
                    peak_memory_gb = float(last_response.peak_memory)
            except Exception as exc:  # pragma: no cover - hardware/runtime boundary
                transport_status = "ERROR"
                transport_error = sanitized_exception(exc)
            latency_ms = (time.perf_counter() - started) * 1000.0
            response_at = utc_now()
            raw_response_hash = (
                sha256_bytes(content.encode("utf-8")) if content is not None else None
            )
            if transport_status == "ERROR":
                parse_status = "TRANSPORT_ERROR"
                parse_detail = transport_error
                raw_decision = None
            elif content is None or not content.strip():
                parse_status = "SCHEMA_ERROR"
                parse_detail = "local model returned no final response text"
                raw_decision = None
            else:
                parse_status, raw_decision, parse_detail = diagnose_content(
                    content, items[item_id], base_policy, schema_path=DECISION_SCHEMA
                )
                if parse_detail is not None:
                    parse_detail = parse_detail.replace(str(ROOT), "<LOCAL_PATH>").replace(
                        str(Path.home()), "<LOCAL_PATH>"
                    )
            usage: Json = {
                "input_tokens": prompt_tokens,
                "cached_input_tokens": 0 if prompt_tokens is not None else None,
                "output_tokens": output_tokens,
                "reasoning_tokens": None,
                "total_tokens": (
                    prompt_tokens + output_tokens
                    if prompt_tokens is not None and output_tokens is not None
                    else None
                ),
            }
            record: Json = {
                "schema_version": "1.0.0",
                "study_id": plan["study_id"],
                "frozen_plan_commit": frozen_commit,
                "packet_sha256": packet["packet_sha256"],
                "dataset_manifest_sha256": manifest_hash,
                "phase": "full",
                "lane_id": current_lane_id,
                "provider": "Local MLX",
                "model_requested": lane["model_repo"],
                "model_returned": f"{lane['model_repo']}@{lane['model_revision']}",
                "model_family": lane["model_family"],
                "item_id": item_id,
                "pair_id": packet_row["pair_id"],
                "request_sha256": request_hash,
                "prompt_sha256": packet_row["prompt_sha256"],
                "response_format_sha256": schema_hash,
                "provider_response_id": None,
                "routed_provider": "LOCAL_MLX",
                "system_fingerprint": None,
                "finish_reason": finish_reason,
                "request_started_at_utc": requested_at,
                "response_received_at_utc": response_at,
                "transport_status": transport_status,
                "transport_error": transport_error,
                "raw_response_text": content,
                "raw_response_sha256": raw_response_hash,
                "parse_status": parse_status,
                "parse_error_detail": parse_detail,
                "raw_decision": raw_decision,
                "postgate_decision": None,
                "latency_ms": latency_ms,
                "usage": usage,
                "actual_cost_usd": None,
                "cost_status": "UNKNOWN",
                "evidence_ceiling": "COMPUTATIONAL",
            }
            validate_with_schema(record, RUN_SCHEMA, str(cell["cell_id"]))
            terminal: Json = {
                "schema_version": "1.0.0",
                "sequence": sequence,
                "cell_id": cell["cell_id"],
                "record": record,
            }
            if peak_memory_gb is not None:
                terminal["local_peak_memory_gb"] = peak_memory_gb
            append_durable(terminals_path, terminal)
            completed.append(record)
            lane_records[str(current_lane_id)].append(record)
            if len(completed) % 20 == 0 or len(completed) == 240:
                print(
                    canonical_json(
                        {
                            "status": "RUNNING",
                            "completed_cells": len(completed),
                            "planned_cells": 240,
                            "valid_decisions": sum(
                                row["parse_status"] == "OK" for row in completed
                            ),
                            "runtime_errors": sum(
                                row["transport_status"] == "ERROR" for row in completed
                            ),
                        }
                    ),
                    flush=True,
                )
        del model, tokenizer
        gc.collect()
        mx.clear_cache()

    if len(completed) != 240:
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging:
        output_hashes: Json = {}
        summaries: list[Json] = []
        for current_lane_id in plan["execution"]["base_lane_order"]:
            path = staging / f"{current_lane_id}.jsonl"
            records = lane_records[str(current_lane_id)]
            if len(records) != 120:
                fail(f"lane does not contain 120 terminal records: {current_lane_id}")
            write_jsonl(path, records)
            output_hashes[path.name] = sha256_file(path)
            summaries.append(
                {
                    "lane_id": current_lane_id,
                    "records": 120,
                    "valid_decisions": sum(row["parse_status"] == "OK" for row in records),
                    "runtime_errors": sum(row["transport_status"] == "ERROR" for row in records),
                }
            )
        receipt: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "replacement_version": REPLACEMENT_VERSION,
            "prior_ineligible_application_invocations": 1,
            "void_attempt_receipt_sha256": sha256_file(void_receipt),
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "planned_cells": 240,
            "durable_request_intents": 240,
            "durable_terminal_records": 240,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "credentials_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_blocks_retained": False,
            "request_intent_journal_sha256": sha256_file(intents_path),
            "terminal_journal_sha256": sha256_file(terminals_path),
            "lane_output_sha256": output_hashes,
            "lanes": summaries,
        }
        write_durable_json(staging / "execution-receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "out_dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
