"""Gold-free parsing and schema/semantic validation for model decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from .dataset import validate_with_schema
from .state import validate_decision_semantics

Json = dict[str, Any]
ParseStatus = Literal["OK", "JSON_SYNTAX_ERROR", "SCHEMA_ERROR", "SEMANTIC_ERROR"]


def diagnose_decision(
    content: str,
    item: Json,
    *,
    schema_path: Path,
) -> tuple[ParseStatus, Json | None, str | None]:
    """Parse one response without importing or applying an oracle or gate."""

    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return "JSON_SYNTAX_ERROR", None, f"{exc.msg} at line {exc.lineno} column {exc.colno}"
    if not isinstance(value, dict):
        return "SCHEMA_ERROR", None, "top-level JSON value is not an object"
    try:
        validate_with_schema(value, schema_path, "v2 model decision")
    except Exception as exc:  # validation library supplies the actionable detail
        return "SCHEMA_ERROR", None, str(exc)
    try:
        validate_decision_semantics(item, value)
    except Exception as exc:
        return "SEMANTIC_ERROR", None, str(exc)
    return "OK", value, None
