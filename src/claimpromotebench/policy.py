"""Loading and primitive checks for the versioned transition policy."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .errors import DatasetIntegrityError


def load_policy(path: Path) -> dict[str, Any]:
    """Load a policy JSON object."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetIntegrityError(f"cannot load policy {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DatasetIntegrityError("policy root must be an object")
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
