#!/usr/bin/env python3
"""Recompute and validate sanitized upstream route-repetition results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_upstream_policy_route_repetition import (  # noqa: E402
    ACCOUNT_MARKERS,
    FORBIDDEN_RESULT_KEYS,
    _walk_keys,
    build_analysis,
)
from upstream_route_repetition import STUDY_ID, STUDY_ROOT  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-results-validate: {message}")


def load_object(path: Path) -> Json:
    value = load_json(path)
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate_results(
    plan_path: Path = STUDY_ROOT / "study-plan.json",
    schedule_path: Path = STUDY_ROOT / "request-schedule.json",
    private_root: Path = STUDY_ROOT / "private-results",
    journal_root: Path = STUDY_ROOT / "journal",
    results_root: Path = STUDY_ROOT / "results",
) -> Json:
    expected_aggregate, expected_records = build_analysis(
        plan_path.resolve(),
        schedule_path.resolve(),
        private_root.resolve(),
        journal_root.resolve(),
    )
    results_root = results_root.resolve()
    manifest_path = results_root / "manifest.json"
    aggregate_path = results_root / "aggregate.json"
    privacy_path = results_root / "privacy-receipt.json"
    manifest = load_object(manifest_path)
    aggregate = load_object(aggregate_path)
    privacy = load_object(privacy_path)
    payload = {key: value for key, value in manifest.items() if key != "self_digest"}
    actual_files = sorted(path for path in results_root.rglob("*") if path.is_file())
    files_sha = manifest.get("files_sha256")
    if (
        manifest.get("status") != "DYNAMIC_SANITIZED_RESULTS_MANIFEST"
        or manifest.get("study_id") != STUDY_ID
        or manifest.get("file_count") != len(actual_files)
        or manifest.get("hashed_file_count") != len(actual_files) - 1
        or not isinstance(files_sha, dict)
        or len(files_sha) != len(actual_files) - 1
        or "manifest.json" in files_sha
        or manifest.get("self_digest") != sha256_bytes(canonical_json(payload).encode("utf-8"))
        or manifest.get("contains_private_run_records") is not False
        or manifest.get("contains_raw_model_responses") is not False
    ):
        fail("dynamic sanitized-results manifest is malformed")
    for relative, expected in files_sha.items():
        path = results_root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"sanitized result digest differs: {relative}")
    if aggregate != expected_aggregate:
        fail("committed aggregate differs from a clean recomputation")
    for filename, expected_rows in sorted(expected_records.items()):
        path = results_root / "records" / filename
        if load_jsonl(path) != expected_rows:
            fail(f"sanitized record file differs from a clean recomputation: {filename}")

    scanned_relatives = [
        "aggregate.json",
        *[f"records/{name}" for name in sorted(expected_records)],
    ]
    if (
        privacy.get("status") != "SANITIZED_RESULTS_PRIVACY_PASS"
        or privacy.get("study_id") != STUDY_ID
        or privacy.get("scanned_file_count") != len(scanned_relatives)
        or privacy.get("forbidden_result_keys") != sorted(FORBIDDEN_RESULT_KEYS)
        or privacy.get("forbidden_result_keys_observed") != []
        or privacy.get("account_markers_observed") != []
        or privacy.get("raw_model_response_content_retained") is not False
        or privacy.get("provider_response_identifiers_retained") is not False
        or privacy.get("hidden_reasoning_retained") is not False
        or privacy.get("invalid_response_contents_entered_results") is not False
        or privacy.get("credentials_loaded_for_analysis") is not False
    ):
        fail("privacy receipt changed")
    expected_scanned_hashes = {
        relative: sha256_file(results_root / relative) for relative in scanned_relatives
    }
    if privacy.get("scanned_files_sha256") != expected_scanned_hashes:
        fail("privacy receipt file inventory differs")
    values: list[Any] = [aggregate]
    values.extend(
        row
        for filename in expected_records
        for row in load_jsonl(results_root / "records" / filename)
    )
    forbidden_observed = FORBIDDEN_RESULT_KEYS & {
        key for value in values for key in _walk_keys(value)
    }
    release_text = "\n".join(
        (results_root / relative).read_text(encoding="utf-8")
        for relative in [*scanned_relatives, "privacy-receipt.json", "manifest.json"]
    ).lower()
    account_hits = [marker for marker in ACCOUNT_MARKERS if marker in release_text]
    if forbidden_observed or account_hits:
        fail(f"live privacy scan failed: keys={sorted(forbidden_observed)} accounts={account_hits}")
    return {
        "status": "UPSTREAM_ROUTE_REPETITION_RESULTS_VALID",
        "credentials_loaded": False,
        "scheduled_cells": aggregate["scheduled_cells"],
        "lanes": len(aggregate["lanes"]),
        "result_files": len(actual_files),
        "manifest_sha256": sha256_file(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=STUDY_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=STUDY_ROOT / "request-schedule.json")
    parser.add_argument("--private-root", type=Path, default=STUDY_ROOT / "private-results")
    parser.add_argument("--journal-root", type=Path, default=STUDY_ROOT / "journal")
    parser.add_argument("--results-root", type=Path, default=STUDY_ROOT / "results")
    args = parser.parse_args()
    print(
        canonical_json(
            validate_results(
                args.plan,
                args.schedule,
                args.private_root,
                args.journal_root,
                args.results_root,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
