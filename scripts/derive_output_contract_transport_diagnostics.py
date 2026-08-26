#!/usr/bin/env python3
"""Derive a content-free transport diagnostic for the output-contract study."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "output-contract-ablation-v1"
PRIVATE_ROOT = STUDY_ROOT / "private-results"
OUT_ROOT = STUDY_ROOT / "diagnostics"
STUDY_ID = "claimpromotebench-output-contract-ablation-2026-08-v1"
PRIMARY_CONDITIONS = ("prompt-4096", "prompt-12288")
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "chih-kai")
FORBIDDEN_PUBLIC_KEYS = (
    'raw_response_text"',
    'transport_error"',
    'parse_error_detail"',
    'provider_response_id"',
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"output-contract-transport-diagnostics: {message}")


def load_object(path: Path) -> Json:
    value = load_json(path)
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def classify_transport(error: object) -> str:
    text = str(error or "").lower()
    if re.search(
        r"weekly|quota|usage.?limit|spending|billing|credit|payment|"
        r"http\D*402|status\D*402",
        text,
    ):
        return "QUOTA_OR_BILLING_REJECTION"
    if re.search(r"\b429\b|rate.?limit|too many requests", text):
        return "RATE_LIMIT"
    if re.search(r"\b(?:401|403)\b|unauthor|forbidden|auth", text):
        return "AUTHENTICATION_OR_PERMISSION"
    if re.search(r"timed?.?out|timeout", text):
        return "TIMEOUT"
    if re.search(r"\b(?:500|502|503|504)\b|internal server|bad gateway|service unavailable", text):
        return "SERVER_5XX"
    if re.search(r"network|connection|dns|socket|tls", text):
        return "NETWORK"
    return "OTHER_TRANSPORT_ERROR"


def build(private_root: Path = PRIVATE_ROOT, study_root: Path = STUDY_ROOT) -> Json:
    receipt_path = private_root / "execution-receipt.json"
    receipt = load_object(receipt_path)
    lane_hashes = receipt.get("lane_output_sha256")
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("planned_cells") != 360
        or receipt.get("application_posts") != 360
        or receipt.get("client_retry_count") != 0
        or not isinstance(lane_hashes, dict)
        or len(lane_hashes) != 12
    ):
        fail("complete zero-retry private execution receipt is required")

    schedule_path = study_root / "request-schedule.json"
    schedule = load_object(schedule_path)
    if schedule.get("study_id") != STUDY_ID or schedule.get("planned_cells") != 360:
        fail("frozen request schedule differs from the completed study")
    lane_conditions: dict[str, str] = {}
    for cell in schedule.get("cells", []):
        if not isinstance(cell, dict):
            fail("request schedule contains a non-object cell")
        lane_id = str(cell["lane_id"])
        condition_id = str(cell["condition_id"])
        previous = lane_conditions.setdefault(lane_id, condition_id)
        if previous != condition_id:
            fail(f"lane maps to multiple conditions: {lane_id}")

    input_hashes: Json = {
        "execution-receipt.json": sha256_file(receipt_path),
        "request-schedule.json": sha256_file(schedule_path),
    }
    rows_by_lane: dict[str, list[Json]] = {}
    all_failures: list[tuple[str, Json, str]] = []
    for filename, expected_hash in sorted(lane_hashes.items()):
        path = private_root / str(filename)
        if sha256_file(path) != expected_hash:
            fail(f"private lane differs from its execution receipt: {path.name}")
        rows = load_jsonl(path)
        if len(rows) != 30:
            fail(f"private lane does not contain 30 terminal records: {path.name}")
        lane_id = str(rows[0]["lane_id"])
        if lane_id in rows_by_lane or any(str(row.get("lane_id")) != lane_id for row in rows):
            fail(f"private lane identity is inconsistent: {path.name}")
        rows_by_lane[lane_id] = rows
        input_hashes[path.name] = sha256_file(path)
        for row in rows:
            if row.get("transport_status") == "ERROR":
                category = classify_transport(row.get("transport_error"))
                all_failures.append((lane_id, row, category))

    if set(rows_by_lane) != set(lane_conditions):
        fail("private lanes differ from the frozen schedule")

    lane_reports: list[Json] = []
    quota_items: dict[tuple[str, str], set[str]] = defaultdict(set)
    for lane_id in sorted(rows_by_lane):
        rows = rows_by_lane[lane_id]
        counts = Counter(
            classify_transport(row.get("transport_error"))
            for row in rows
            if row.get("transport_status") == "ERROR"
        )
        condition_id = lane_conditions[lane_id]
        model_requested = str(rows[0]["model_requested"])
        for row in rows:
            if (
                row.get("transport_status") == "ERROR"
                and classify_transport(row.get("transport_error")) == "QUOTA_OR_BILLING_REJECTION"
            ):
                quota_items[(model_requested, condition_id)].add(str(row["item_id"]))
        lane_reports.append(
            {
                "lane_id": lane_id,
                "model_requested": model_requested,
                "condition_id": condition_id,
                "scheduled_cells": len(rows),
                "transport_failure_categories": dict(sorted(counts.items())),
            }
        )

    category_counts = Counter(category for _, _, category in all_failures)
    category_windows: Json = {}
    for category in sorted(category_counts):
        timestamps = sorted(
            str(row["request_started_at_utc"])
            for _, row, child_category in all_failures
            if child_category == category
        )
        category_windows[category] = {
            "count": len(timestamps),
            "first_request_started_at_utc": timestamps[0],
            "last_request_started_at_utc": timestamps[-1],
        }

    primary_balance: list[Json] = []
    models = sorted({str(rows[0]["model_requested"]) for rows in rows_by_lane.values()})
    for model in models:
        base = quota_items[(model, PRIMARY_CONDITIONS[0])]
        longer = quota_items[(model, PRIMARY_CONDITIONS[1])]
        primary_balance.append(
            {
                "model_requested": model,
                "conditions": list(PRIMARY_CONDITIONS),
                "quota_rejections_per_condition": [len(base), len(longer)],
                "rejected_item_sets_equal": base == longer,
            }
        )

    report: Json = {
        "schema_version": "1.0.0",
        "status": "POSTHOC_CONTENT_FREE_TRANSPORT_DIAGNOSTIC",
        "study_id": STUDY_ID,
        "derived_at_utc": receipt["completed_at_utc"],
        "scheduled_cells": 360,
        "application_posts": 360,
        "client_retry_count": 0,
        "transport_failures": len(all_failures),
        "transport_failure_categories": dict(sorted(category_counts.items())),
        "category_windows": category_windows,
        "lanes": lane_reports,
        "registered_primary_contrast_quota_balance": primary_balance,
        "input_files_sha256": input_hashes,
        "gold_loaded": False,
        "correctness_fields_used": False,
        "response_repair_or_rescoring_performed": False,
        "raw_response_text_retained": False,
        "free_form_transport_text_retained": False,
        "provider_response_identifiers_retained": False,
        "hidden_reasoning_retained": False,
        "interpretation": (
            "These posthoc categories describe transport outcomes for frozen cells. They preserve "
            "the endpoint, schedule, and end-to-end denominator and do not repair or rescore "
            "a response."
        ),
    }
    report["self_digest"] = self_digest(report)
    return report


def write_outputs(out_root: Path, report: Json) -> None:
    if out_root.exists():
        fail("refusing to overwrite an existing diagnostic directory")
    out_root.mkdir(parents=True)
    report_path = out_root / "transport-diagnostics.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    privacy: Json = {
        "schema_version": "1.0.0",
        "status": "CONTENT_FREE_TRANSPORT_DIAGNOSTIC_PRIVACY_PASS",
        "study_id": STUDY_ID,
        "scanned_file": report_path.name,
        "scanned_file_sha256": sha256_file(report_path),
        "raw_response_text_retained": False,
        "free_form_transport_text_retained": False,
        "credentials_retained": False,
        "account_markers_retained": False,
        "provider_response_identifiers_retained": False,
        "hidden_reasoning_retained": False,
    }
    privacy_path = out_root / "privacy-receipt.json"
    privacy_path.write_text(json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest: Json = {
        "schema_version": "1.0.0",
        "status": "DYNAMIC_CONTENT_FREE_TRANSPORT_DIAGNOSTIC_MANIFEST",
        "study_id": STUDY_ID,
        "file_count": 3,
        "hashed_file_count": 2,
        "files_sha256": {
            report_path.name: sha256_file(report_path),
            privacy_path.name: sha256_file(privacy_path),
        },
    }
    manifest["self_digest"] = self_digest(manifest)
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate(
    out_root: Path = OUT_ROOT,
    private_root: Path = PRIVATE_ROOT,
    study_root: Path = STUDY_ROOT,
) -> Json:
    report = load_object(out_root / "transport-diagnostics.json")
    privacy = load_object(out_root / "privacy-receipt.json")
    manifest = load_object(out_root / "manifest.json")
    expected = build(private_root, study_root)
    actual_files = sorted(path.name for path in out_root.iterdir() if path.is_file())
    if report != expected or report.get("self_digest") != self_digest(report):
        fail("transport diagnostic differs from a clean derivation")
    if (
        privacy.get("status") != "CONTENT_FREE_TRANSPORT_DIAGNOSTIC_PRIVACY_PASS"
        or privacy.get("scanned_file_sha256")
        != sha256_file(out_root / "transport-diagnostics.json")
        or any(
            privacy.get(key) is not False
            for key in (
                "raw_response_text_retained",
                "free_form_transport_text_retained",
                "credentials_retained",
                "account_markers_retained",
                "provider_response_identifiers_retained",
                "hidden_reasoning_retained",
            )
        )
    ):
        fail("transport diagnostic privacy receipt differs")
    files = manifest.get("files_sha256")
    if (
        manifest.get("status") != "DYNAMIC_CONTENT_FREE_TRANSPORT_DIAGNOSTIC_MANIFEST"
        or manifest.get("file_count") != len(actual_files)
        or manifest.get("hashed_file_count") != len(actual_files) - 1
        or not isinstance(files, dict)
        or manifest.get("self_digest") != self_digest(manifest)
    ):
        fail("transport diagnostic manifest differs")
    for relative, expected_hash in files.items():
        if sha256_file(out_root / str(relative)) != expected_hash:
            fail(f"transport diagnostic digest differs: {relative}")
    text = "\n".join((out_root / name).read_text(encoding="utf-8") for name in actual_files).lower()
    account_hits = [marker for marker in ACCOUNT_MARKERS if marker in text]
    if account_hits or any(marker in text for marker in FORBIDDEN_PUBLIC_KEYS):
        fail(f"transport diagnostic privacy scan failed: account_hits={account_hits}")
    return {
        "status": "OUTPUT_CONTRACT_TRANSPORT_DIAGNOSTICS_VALID",
        "scheduled_cells": report["scheduled_cells"],
        "transport_failures": report["transport_failures"],
        "result_files": len(actual_files),
        "credentials_loaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--private-root", type=Path, default=PRIVATE_ROOT)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT)
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()
    if args.verify:
        result = validate(
            args.out_root.resolve(), args.private_root.resolve(), args.study_root.resolve()
        )
    else:
        report = build(args.private_root.resolve(), args.study_root.resolve())
        write_outputs(args.out_root.resolve(), report)
        result = {
            "status": "OUTPUT_CONTRACT_TRANSPORT_DIAGNOSTICS_WRITTEN",
            "scheduled_cells": report["scheduled_cells"],
            "transport_failures": report["transport_failures"],
        }
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
