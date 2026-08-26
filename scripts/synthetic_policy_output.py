#!/usr/bin/env python3
"""Minimal output parsing shared by local synthetic-policy replications."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from slsa_policy import diagnose_slsa_decision

Json = dict[str, Any]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


def diagnose_content(
    content: str,
    item: Json,
    policy: Json,
    *,
    schema_path: Path,
) -> tuple[str, Json | None, str | None]:
    status, decision, detail = diagnose_slsa_decision(
        content, item, policy, schema_path=schema_path
    )
    if status != "JSON_SYNTAX_ERROR":
        return status, decision, detail
    extracted = extract_single_json_object(content)
    if extracted is None:
        return status, decision, detail
    status, decision, detail = diagnose_slsa_decision(
        extracted, item, policy, schema_path=schema_path
    )
    marker = "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
    return status, decision, marker if detail is None else f"{marker}: {detail}"
