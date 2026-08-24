"""Shared contract for repeated model routes on upstream policy revisions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, NoReturn

from upstream_policy_revision import validate_decision_semantics

from claimpromotebench.dataset import validate_with_schema
from claimpromotebench.errors import DatasetIntegrityError

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "upstream-policy-route-repetition-v1"
SOURCE_ROOT = ROOT / "v2" / "upstream-policy-revisions-v1"
PACKET_PATH = SOURCE_ROOT / "dataset" / "evaluation-prompt-packet.json"
GOLD_PATH = SOURCE_ROOT / "dataset" / "evaluation-gold.jsonl"
PAIRS_PATH = SOURCE_ROOT / "dataset" / "evaluation-pairs.json"
SOURCE_MANIFEST_PATH = SOURCE_ROOT / "artifact-manifest.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "upstream-policy-decision.schema.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "upstream-policy-route-repetition-record.schema.json"
CATALOG_URL = "https://opencode.ai/zen/go/v1/models"
DOCS_URL = "https://dev.opencode.ai/docs/go/"
STUDY_ID = "claimpromotebench-upstream-policy-route-repetition-2026-08-v1"
REPETITIONS = 3
ACTIONS = ("ALLOW", "HOLD")
ACCOUNT_REFERENCE = re.compile(r"(?i)(workspace[/\"':= ]+)(?:wrk_)?[A-Za-z0-9_-]+")
PROVIDER_ID_REFERENCE = re.compile(
    r"(?i)(request[_ -]?id|response[_ -]?id|trace[_ -]?id)([\"':= ]+)[A-Za-z0-9._-]+"
)

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition: {message}")


def lanes() -> tuple[Json, Json]:
    shared: Json = {
        "provider": "OpenCode Go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_kind": "openai_compatible",
        "auth_env": "OPENCODE_GO_API_KEY",
        "response_format": "prompt_only_exact_json",
        "allow_single_json_object_extraction": False,
        "max_output_tokens": 512,
        "sampling_parameters_sent": [],
        "billing_mode": "PREEXISTING_OPENCODE_GO_ALLOWANCE",
    }
    return (
        {
            **shared,
            "lane_id": "opencode-go-qwen3.7-max-upstream-repeat-v1",
            "model": "qwen3.7-max",
            "model_family": "Qwen",
        },
        {
            **shared,
            "lane_id": "opencode-go-deepseek-v4-flash-upstream-repeat-v1",
            "model": "deepseek-v4-flash",
            "model_family": "DeepSeek",
        },
    )


def request_body(lane: Json, prompt: str) -> Json:
    return {
        "model": lane["model"],
        "max_tokens": int(lane["max_output_tokens"]),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> Json:
    value: Json = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def diagnose_response(text: str) -> tuple[str, str | None, Json | None, str | None]:
    """Return parse status, exact action, full decision, and a bounded diagnostic."""

    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return "JSON_SYNTAX_ERROR", None, None, str(exc)[:500]
    if not isinstance(value, dict):
        return "SCHEMA_ERROR", None, None, "top-level JSON value must be an object"
    raw_action = value.get("action")
    action = raw_action if isinstance(raw_action, str) and raw_action in ACTIONS else None
    try:
        validate_with_schema(value, DECISION_SCHEMA, "route response")
    except DatasetIntegrityError as exc:
        return "SCHEMA_ERROR", action, None, str(exc)[:500]
    try:
        validate_decision_semantics(value)
    except ValueError as exc:
        return "SEMANTIC_ERROR", action, None, str(exc)[:500]
    return "OK", action, value, None


def sanitize_response_text(text: str | None, api_key: str) -> str | None:
    if text is None:
        return None
    cleaned = text.replace(api_key, "<REDACTED_CREDENTIAL>")
    cleaned = ACCOUNT_REFERENCE.sub(r"\1<REDACTED_ACCOUNT>", cleaned)
    cleaned = PROVIDER_ID_REFERENCE.sub(r"\1\2<REDACTED_PROVIDER_ID>", cleaned)
    return cleaned


def sanitize_error(text: str | None, api_key: str) -> str | None:
    cleaned = sanitize_response_text(text, api_key)
    return cleaned[:2000] if cleaned is not None else None


def canonical_decision(decision: Json) -> Json:
    """Normalize witness order while preserving every contract field."""

    value = dict(decision)
    witnesses = value.get("witnesses")
    if isinstance(witnesses, list):
        value["witnesses"] = sorted(
            witnesses,
            key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")),
        )
    return value
