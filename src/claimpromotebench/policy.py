"""Loading and primitive checks for the versioned transition policy."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import DatasetIntegrityError

POLICY_SCHEMA = "transition-policy.schema.json"


def _policy_schema_path(path: Path) -> Path:
    return path.resolve().parents[1] / "schemas" / POLICY_SCHEMA


def _validate_policy(value: dict[str, Any], path: Path) -> None:
    schema_path = _policy_schema_path(path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetIntegrityError(f"cannot load policy schema {schema_path}: {exc}") from exc
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise DatasetIntegrityError(f"policy violates schema at {location}: {first.message}")


def load_policy(path: Path) -> dict[str, Any]:
    """Load and validate a complete, machine-readable policy contract."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetIntegrityError(f"cannot load policy {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DatasetIntegrityError("policy root must be an object")
    _validate_policy(value, path)
    return value


def parse_timestamp(value: str) -> datetime:
    """Parse an RFC 3339 timestamp and require an explicit UTC offset."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DatasetIntegrityError(f"invalid RFC 3339 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise DatasetIntegrityError(f"timestamp has no timezone: {value}")
    return parsed.astimezone(UTC)


def interval_covers(evidence_domain: dict[str, Any], required_domain: dict[str, Any]) -> bool:
    """Check decimal interval coverage, including open and closed endpoints."""

    evidence_variables = {str(v["name"]): v for v in evidence_domain.get("variables", [])}
    required_variables = {str(v["name"]): v for v in required_domain.get("variables", [])}
    if set(evidence_variables) != set(required_variables):
        return False
    try:
        for name, required in required_variables.items():
            evidence = evidence_variables[name]
            evidence_lower = Decimal(str(evidence["lower"]))
            evidence_upper = Decimal(str(evidence["upper"]))
            required_lower = Decimal(str(required["lower"]))
            required_upper = Decimal(str(required["upper"]))
            if evidence_lower > required_lower or evidence_upper < required_upper:
                return False
            if (
                evidence_lower == required_lower
                and bool(required["lower_inclusive"])
                and not bool(evidence["lower_inclusive"])
            ):
                return False
            if (
                evidence_upper == required_upper
                and bool(required["upper_inclusive"])
                and not bool(evidence["upper_inclusive"])
            ):
                return False
    except (InvalidOperation, KeyError, TypeError):
        return False
    return True
