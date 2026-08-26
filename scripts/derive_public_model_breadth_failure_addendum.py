#!/usr/bin/env python3
"""Derive privacy-safe failure categories from the frozen breadth terminal journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOURNAL = (
    ROOT
    / "v2"
    / "public-model-breadth-v1"
    / "private-results"
    / "journal"
    / "terminal-records.jsonl"
)
EXPECTED_COUNTS = {
    "AUTHORIZATION": 76,
    "CONNECTION": 1,
    "QUOTA_RATE_LIMIT": 547,
    "SERVER": 5,
    "TIMEOUT": 1,
}

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"breadth-failure-addendum: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def classify_transport_error(value: Any) -> str:
    text = str(value or "")
    ordered_patterns = (
        (
            "QUOTA_RATE_LIMIT",
            r"quota|weekly|usage.?limit|insufficient|exhaust|allowance|"
            r"weighted tokens|\b429\b|rate.?limit|too many requests",
        ),
        ("AUTHORIZATION", r"\b(?:401|403)\b|unauthor|forbidden"),
        ("SERVER", r"\b5\d\d\b|internal server|bad gateway|unavailable"),
        ("TIMEOUT", r"time.?out|timed out|deadline"),
        ("CONNECTION", r"connect|network|socket|tls|\beof\b|reset|broken pipe"),
    )
    for category, pattern in ordered_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return category
    return "UNCLASSIFIED"


def derive(journal: Path) -> tuple[Json, Json]:
    rows = [
        json.loads(line)
        for line in journal.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1260:
        fail(f"expected 1,260 terminal records, observed {len(rows)}")
    sequences = [row.get("sequence") for row in rows]
    if sequences != list(range(1260)):
        fail("terminal journal sequence is not the frozen 0..1259 schedule")

    categories: Counter[str] = Counter()
    quota_sequences: list[int] = []
    transport_records = 0
    for row in rows:
        record = row.get("record")
        if not isinstance(record, dict):
            fail("terminal journal contains a malformed record")
        error = record.get("transport_error")
        if error is None:
            continue
        transport_records += 1
        category = classify_transport_error(error)
        categories[category] += 1
        if category == "QUOTA_RATE_LIMIT":
            quota_sequences.append(int(row["sequence"]))

    if transport_records != 630 or dict(sorted(categories.items())) != EXPECTED_COUNTS:
        fail(
            "frozen failure categories changed: "
            f"transport={transport_records}, categories={dict(sorted(categories.items()))}"
        )
    expected_quota_tail = list(range(713, 1260))
    if quota_sequences != expected_quota_tail:
        fail("quota/rate-limit failures no longer form the final 547-cell schedule tail")

    common = {
        "schema_version": "1.0.0",
        "status": "POST_RUN_FROZEN_LOG_AUDIT_COMPLETE",
        "study_id": "public-model-breadth-v1",
        "analysis_timing": "POST_RUN_NO_NEW_MODEL_CALLS",
        "scheduled_cells": 1260,
        "transport_failures": transport_records,
        "transport_failure_categories": dict(sorted(categories.items())),
        "quota_cutoff": {
            "cells": len(quota_sequences),
            "contiguous_schedule_tail": True,
            "first_zero_based_sequence": quota_sequences[0],
            "last_zero_based_sequence": quota_sequences[-1],
        },
        "interpretation_boundary": {
            "registered_denominators_changed": False,
            "completed_study_rerun": False,
            "model_calls_performed": 0,
            "model_family_comparison_supported": False,
            "route_reliability_comparison_supported": False,
            "shared_account_quota_confound_present": True,
        },
        "privacy": {
            "raw_error_text_included": False,
            "provider_response_identifiers_included": False,
            "credentials_included": False,
        },
    }
    private = {
        **common,
        "source": {
            "path": str(journal.relative_to(ROOT)),
            "sha256": sha256_file(journal),
            "records": len(rows),
        },
    }
    public = {
        **common,
        "source": {
            "identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
            "records": len(rows),
            "private_source_digest_included": False,
        },
    }
    return private, public


def write_json(path: Path, value: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--public-out", type=Path, required=True)
    args = parser.parse_args()
    private, public = derive(args.journal.resolve())
    write_json(args.private_out.resolve(), private)
    write_json(args.public_out.resolve(), public)
    print(
        json.dumps(
            {
                "status": public["status"],
                "transport_failures": public["transport_failures"],
                "transport_failure_categories": public["transport_failure_categories"],
                "quota_cutoff": public["quota_cutoff"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
