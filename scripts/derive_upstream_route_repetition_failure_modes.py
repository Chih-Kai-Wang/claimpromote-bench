#!/usr/bin/env python3
"""Derive a content-free diagnostic of repeated-route terminal failure modes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "upstream-policy-route-repetition-v1"
PRIVATE_ROOT = STUDY_ROOT / "private-results"
OUT_ROOT = STUDY_ROOT / "diagnostics"
STUDY_ID = "claimpromotebench-upstream-policy-route-repetition-2026-08-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "chih-kai")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-failure-modes: {message}")


def load_object(path: Path) -> Json:
    value = load_json(path)
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def classify(record: Json) -> str:
    if record.get("transport_status") == "ERROR":
        error = str(record.get("transport_error") or "")
        if error == "transport failure: The read operation timed out":
            return "READ_TIMEOUT"
        return "OTHER_TRANSPORT_ERROR"
    status = str(record.get("parse_status"))
    if status == "OK":
        return "CONTRACT_VALID"
    if status == "JSON_SYNTAX_ERROR":
        text = str(record.get("raw_response_text") or "")
        if not text:
            return "EMPTY_FINAL_TEXT"
        if text.lstrip().startswith("```"):
            return "MARKDOWN_CODE_FENCE"
        if record.get("finish_reason") == "length":
            return "LENGTH_TERMINATED_NON_JSON"
        return "NON_JSON_PREFIX_OR_ENVELOPE"
    if status == "SCHEMA_ERROR":
        return "SCHEMA_INVALID"
    if status == "SEMANTIC_ERROR":
        return "SEMANTIC_INVALID"
    fail(f"unknown terminal status: {status}")


def build(private_root: Path = PRIVATE_ROOT) -> Json:
    receipt_path = private_root / "execution-receipt.json"
    receipt = load_object(receipt_path)
    outputs = receipt.get("outputs")
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("planned_cells") != 144
        or receipt.get("application_posts") != 144
        or receipt.get("client_retry_count") != 0
        or not isinstance(outputs, list)
        or len(outputs) != 6
    ):
        fail("complete private execution receipt is required")
    grouped: dict[str, list[Json]] = defaultdict(list)
    input_hashes: Json = {"execution-receipt.json": sha256_file(receipt_path)}
    for output in outputs:
        path = private_root / str(output["file"])
        rows = load_jsonl(path)
        if len(rows) != 24 or output.get("sha256") != sha256_file(path):
            fail(f"private output differs from its execution receipt: {path.name}")
        input_hashes[path.name] = sha256_file(path)
        grouped[str(output["lane_id"])].extend(rows)
    lane_rows: list[Json] = []
    for lane_id in sorted(grouped):
        rows = grouped[lane_id]
        if len(rows) != 72:
            fail(f"lane does not contain 72 terminal records: {lane_id}")
        lane_rows.append(
            {
                "lane_id": lane_id,
                "model_requested": rows[0]["model_requested"],
                "scheduled_cells": len(rows),
                "failure_mode_counts": dict(sorted(Counter(classify(row) for row in rows).items())),
                "by_repetition": [
                    {
                        "repetition": repetition,
                        "scheduled_cells": 24,
                        "failure_mode_counts": dict(
                            sorted(
                                Counter(
                                    classify(row) for row in rows if row["repetition"] == repetition
                                ).items()
                            )
                        ),
                    }
                    for repetition in range(1, 4)
                ],
            }
        )
    report: Json = {
        "schema_version": "1.0.0",
        "status": "POSTHOC_CONTENT_FREE_OUTPUT_SHAPE_DIAGNOSTIC",
        "study_id": STUDY_ID,
        "derived_at_utc": receipt["completed_at_utc"],
        "scheduled_cells": 144,
        "lanes": lane_rows,
        "input_files_sha256": input_hashes,
        "gold_loaded": False,
        "correctness_fields_used": False,
        "response_repair_or_rescoring_performed": False,
        "raw_response_text_retained": False,
        "transport_error_text_retained": False,
        "provider_response_identifiers_retained": False,
        "hidden_reasoning_retained": False,
        "interpretation": (
            "Categories explain the terminal protocol status of frozen cells. They preserve the "
            "original endpoint and denominator and perform no response repair or rescoring."
        ),
    }
    report["self_digest"] = self_digest(report)
    return report


def write_outputs(out_root: Path, report: Json) -> None:
    if out_root.exists():
        fail("refusing to overwrite an existing diagnostic directory")
    out_root.mkdir(parents=True)
    report_path = out_root / "failure-modes.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    privacy: Json = {
        "schema_version": "1.0.0",
        "status": "CONTENT_FREE_DIAGNOSTIC_PRIVACY_PASS",
        "study_id": STUDY_ID,
        "scanned_file": "failure-modes.json",
        "scanned_file_sha256": sha256_file(report_path),
        "raw_response_text_retained": False,
        "transport_error_text_retained": False,
        "credentials_retained": False,
        "account_markers_retained": False,
        "provider_response_identifiers_retained": False,
        "hidden_reasoning_retained": False,
    }
    privacy_path = out_root / "privacy-receipt.json"
    privacy_path.write_text(json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest: Json = {
        "schema_version": "1.0.0",
        "status": "DYNAMIC_CONTENT_FREE_DIAGNOSTIC_MANIFEST",
        "study_id": STUDY_ID,
        "file_count": 3,
        "hashed_file_count": 2,
        "files_sha256": {
            "failure-modes.json": sha256_file(report_path),
            "privacy-receipt.json": sha256_file(privacy_path),
        },
    }
    manifest["self_digest"] = self_digest(manifest)
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate(out_root: Path = OUT_ROOT, private_root: Path = PRIVATE_ROOT) -> Json:
    report = load_object(out_root / "failure-modes.json")
    privacy = load_object(out_root / "privacy-receipt.json")
    manifest = load_object(out_root / "manifest.json")
    expected = build(private_root)
    actual_files = sorted(path.name for path in out_root.iterdir() if path.is_file())
    if report != expected or report.get("self_digest") != self_digest(report):
        fail("failure-mode report differs from a clean derivation")
    if (
        privacy.get("status") != "CONTENT_FREE_DIAGNOSTIC_PRIVACY_PASS"
        or privacy.get("scanned_file_sha256") != sha256_file(out_root / "failure-modes.json")
        or any(
            privacy.get(key) is not False
            for key in (
                "raw_response_text_retained",
                "transport_error_text_retained",
                "credentials_retained",
                "account_markers_retained",
                "provider_response_identifiers_retained",
                "hidden_reasoning_retained",
            )
        )
    ):
        fail("diagnostic privacy receipt differs")
    files = manifest.get("files_sha256")
    if (
        manifest.get("status") != "DYNAMIC_CONTENT_FREE_DIAGNOSTIC_MANIFEST"
        or manifest.get("file_count") != len(actual_files)
        or manifest.get("hashed_file_count") != len(actual_files) - 1
        or not isinstance(files, dict)
        or manifest.get("self_digest") != self_digest(manifest)
    ):
        fail("diagnostic manifest differs")
    for relative, expected_hash in files.items():
        if sha256_file(out_root / str(relative)) != expected_hash:
            fail(f"diagnostic file digest differs: {relative}")
    text = "\n".join((out_root / name).read_text(encoding="utf-8") for name in actual_files).lower()
    account_hits = [marker for marker in ACCOUNT_MARKERS if marker in text]
    forbidden = (
        'raw_response_text"',
        'transport_error"',
        'parse_error_detail"',
        'provider_response_id"',
    )
    if account_hits or any(marker in text for marker in forbidden):
        fail(f"diagnostic privacy scan failed: account_hits={account_hits}")
    return {
        "status": "UPSTREAM_ROUTE_REPETITION_FAILURE_MODES_VALID",
        "scheduled_cells": report["scheduled_cells"],
        "lanes": len(report["lanes"]),
        "credentials_loaded": False,
        "result_files": len(actual_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--private-root", type=Path, default=PRIVATE_ROOT)
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()
    if args.verify:
        result = validate(args.out_root.resolve(), args.private_root.resolve())
    else:
        report = build(args.private_root.resolve())
        write_outputs(args.out_root.resolve(), report)
        result = {
            "status": "UPSTREAM_ROUTE_REPETITION_FAILURE_MODES_WRITTEN",
            "scheduled_cells": report["scheduled_cells"],
            "lanes": len(report["lanes"]),
        }
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
