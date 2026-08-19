#!/usr/bin/env python3
"""Run one frozen ClaimPromoteBench arm against a local llama.cpp server."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.gate import apply_gate  # noqa: E402
from claimpromotebench.hashing import sha256_bytes  # noqa: E402
from claimpromotebench.oracle import evaluate  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.prompts import ARMS, render_prompt  # noqa: E402
from claimpromotebench.state import validate_decision_semantics  # noqa: E402

Json = dict[str, Any]


def model_hash(config: Json) -> str:
    value = str(config["artifact_sha256"])
    return value if value.startswith("sha256:") else f"sha256:{value}"


def request_completion(base_url: str, payload: Json, timeout: float) -> Json:
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"llama.cpp request failed: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("llama.cpp returned non-JSON HTTP content") from exc
    if not isinstance(value, dict):
        raise RuntimeError("llama.cpp response must be a JSON object")
    return value


def extract_content(response: Json) -> tuple[str, int]:
    try:
        choices = response["choices"]
        first = choices[0]
        content = first["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("llama.cpp response lacks choices[0].message.content") from exc
    if not isinstance(content, str):
        raise RuntimeError("llama.cpp message content must be text")
    usage = response.get("usage")
    tokens = 0
    if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
        tokens = int(usage["completion_tokens"])
    return content, tokens


def parse_decision(content: str, item: Json) -> Json | None:
    """Parse one model decision, treating schema or semantic violations as format errors."""

    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    try:
        validate_with_schema(
            value,
            ROOT / "schemas" / "agent-decision.schema.json",
            "model decision",
        )
        validate_decision_semantics(item, value)
    except Exception:
        return None
    return value


def load_preflight(path: Path, config: Json) -> str:
    report = load_json(path)
    if report.get("status") != "PASS":
        raise RuntimeError("model preflight is not PASS")
    expected = model_hash(config).removeprefix("sha256:")
    models = report.get("models")
    if not isinstance(models, list):
        raise RuntimeError("preflight lacks model records")
    matched = [
        model
        for model in models
        if isinstance(model, dict)
        and model.get("model_id") == config["model_id"]
        and model.get("observed_sha256") == expected
    ]
    if len(matched) != 1:
        raise RuntimeError("preflight does not bind the selected model artifact")
    hardware = report.get("hardware")
    if not isinstance(hardware, dict):
        raise RuntimeError("preflight lacks hardware summary")
    return json.dumps(hardware, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verifier_calls(item: Json, arm: str) -> int:
    if arm == "ledger_verifier":
        return len(item["evidence"])
    if arm == "ledger_verifier_gate":
        return len(item["evidence"]) + 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--decoding", type=Path, default=ROOT / "configs" / "decoding-v1.json")
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dataset_dir = args.dataset.resolve()
    manifest = load_json(dataset_dir / "manifest.json")
    policy_path = ROOT / "policies" / str(manifest["policy_file"])
    policy = load_policy(policy_path)
    evaluation_time = str(manifest["evaluation_time"])
    config = load_json(args.model_config)
    decoding = load_json(args.decoding)
    hardware = load_preflight(args.preflight, config)
    if config.get("status") != "FROZEN_UNEXECUTED":
        raise RuntimeError("selected model config is not in the frozen-unexecuted state")

    control = str(decoding["control_instruction"])
    records: list[Json] = []
    for item in load_jsonl(dataset_dir / "inputs.jsonl"):
        rendered = render_prompt(
            item,
            args.arm,
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        )
        prompt = f"{rendered.rstrip()}\n\n{control}\n"
        payload: Json = {
            "model": config["model_id"],
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": decoding["temperature"],
            "top_p": decoding["top_p"],
            "top_k": decoding["top_k"],
            "min_p": decoding["min_p"],
            "repeat_penalty": decoding["repeat_penalty"],
            "presence_penalty": decoding["presence_penalty"],
            "max_tokens": decoding["max_output_tokens"],
            "seed": args.seed,
        }
        start = time.perf_counter()
        response = request_completion(args.base_url, payload, args.timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        content, output_tokens = extract_content(response)
        raw = parse_decision(content, item)
        if raw is None:
            record: Json = {
                "item_id": item["id"],
                "model_id": config["model_id"],
                "model_artifact_sha256": model_hash(config),
                "quantization": config["quantization"],
                "runtime_commit": config["backend_commit"],
                "arm": args.arm,
                "seed": args.seed,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "parse_status": "FORMAT_ERROR",
                "raw_decision": None,
                "final_decision": None,
                "latency_ms": latency_ms,
                "output_tokens": output_tokens,
                "verifier_calls": verifier_calls(item, args.arm),
                "hardware": hardware,
            }
        else:
            final = deepcopy(raw)
            if args.arm == "ledger_verifier_gate":
                oracle_result = evaluate(item, policy, evaluation_time)
                final = apply_gate(raw, oracle_result)["final_decision"]
            record = {
                "item_id": item["id"],
                "model_id": config["model_id"],
                "model_artifact_sha256": model_hash(config),
                "quantization": config["quantization"],
                "runtime_commit": config["backend_commit"],
                "arm": args.arm,
                "seed": args.seed,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "parse_status": "OK",
                "raw_decision": raw,
                "final_decision": final,
                "latency_ms": latency_ms,
                "output_tokens": output_tokens,
                "verifier_calls": verifier_calls(item, args.arm),
                "hardware": hardware,
            }
        validate_with_schema(record, ROOT / "schemas" / "run-record.schema.json", item["id"])
        records.append(record)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out, records)
    format_errors = sum(record["parse_status"] == "FORMAT_ERROR" for record in records)
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "records": len(records),
                "format_errors": format_errors,
                "output": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
