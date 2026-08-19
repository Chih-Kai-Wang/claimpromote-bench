#!/usr/bin/env python3
"""Run the low-cost ClaimPromoteBench v2 pilot against a local llama.cpp server."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
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
from claimpromotebench.hashing import canonical_json, sha256_bytes  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402
from claimpromotebench.prompts import render_prompt  # noqa: E402
from claimpromotebench.v2 import (  # noqa: E402
    diagnose_decision,
    llama_response_format,
    postgate_decision,
)

Json = dict[str, Any]
PROMPT_ARM = "ledger_verifier"


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
    if "error" in value:
        raise RuntimeError(f"llama.cpp returned an error: {value['error']}")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--decoding", type=Path, default=ROOT / "configs" / "decoding-v1.json")
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--decoding-mode", choices=("free", "json_schema"), required=True)
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

    decision_schema_path = ROOT / "schemas" / "agent-decision.schema.json"
    run_schema_path = ROOT / "v2" / "schemas" / "run-record-v2.schema.json"
    decision_schema = load_json(decision_schema_path)
    response_format: Json | None = None
    response_format_sha256: str | None = None
    if args.decoding_mode == "json_schema":
        response_format = llama_response_format(decision_schema)
        response_format_sha256 = sha256_bytes(canonical_json(response_format).encode("utf-8"))

    control = str(decoding["control_instruction"])
    records: list[Json] = []
    for item in load_jsonl(dataset_dir / "inputs.jsonl"):
        rendered = render_prompt(
            item,
            PROMPT_ARM,
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
        if response_format is not None:
            payload["response_format"] = response_format

        start = time.perf_counter()
        response = request_completion(args.base_url, payload, args.timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        content, output_tokens = extract_content(response)
        parse_status, raw_decision, parse_error_detail = diagnose_decision(
            content,
            item,
            schema_path=decision_schema_path,
        )
        postgate = None
        if raw_decision is not None:
            postgate = postgate_decision(raw_decision, item, policy, evaluation_time)

        record: Json = {
            "item_id": item["id"],
            "model_id": config["model_id"],
            "model_artifact_sha256": model_hash(config),
            "quantization": config.get("quantization"),
            "runtime_commit": config.get("backend_commit"),
            "prompt_arm": PROMPT_ARM,
            "decoding_mode": args.decoding_mode,
            "seed": args.seed,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "response_format_sha256": response_format_sha256,
            "raw_response_text": content,
            "raw_response_sha256": sha256_bytes(content.encode("utf-8")),
            "parse_status": parse_status,
            "parse_error_detail": parse_error_detail,
            "raw_decision": raw_decision,
            "postgate_decision": postgate,
            "latency_ms": latency_ms,
            "output_tokens": output_tokens,
            "verifier_calls": len(item["evidence"]),
            "hardware": hardware,
        }
        validate_with_schema(record, run_schema_path, str(item["id"]))
        records.append(record)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out, records)
    status_counts = {
        status: sum(record["parse_status"] == status for record in records)
        for status in ("OK", "JSON_SYNTAX_ERROR", "SCHEMA_ERROR", "SEMANTIC_ERROR")
    }
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "records": len(records),
                "decoding_mode": args.decoding_mode,
                "status_counts": status_counts,
                "output": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
