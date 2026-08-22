"""Build a privacy-minimized derivative of the public model-breadth study.

The source lane records remain private and immutable. This post-execution transform removes final
response text and free-form error detail while preserving every field used by the registered
analysis. Row hashes bind the derivative to its private source without copying private text into
the reviewer release.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, validate_with_schema  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]

RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
PRIVATE_TEXT_FIELDS = ("raw_response_text", "transport_error", "parse_error_detail")
HIDDEN_REASONING_KEYS = {
    "analysis",
    "reasoning_content",
    "thinking",
    "thinking_content",
    "thoughts",
}
CREDENTIAL_PATTERNS = {
    "private-key header": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "OpenAI-style secret": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "GitHub token": re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b"),
    "bearer credential": re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{24,}\b", re.IGNORECASE),
}
PROVIDER_RESPONSE_PATTERNS = {
    "Anthropic-style response ID": re.compile(r"\bmsg_[0-9a-f-]{16,}\b", re.IGNORECASE),
    "OpenAI-style response ID": re.compile(
        r"\b(?:chatcmpl-|resp_)[A-Za-z0-9_-]{10,}\b", re.IGNORECASE
    ),
}
PROVIDER_ACCOUNT_PATTERN = re.compile(
    r"\buser_(?=[A-Za-z0-9_-]{20,64}\b)"
    r"(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]+\b"
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def write_json(path: Path, value: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{canonical_json(row)}\n" for row in rows), encoding="utf-8")


def load_canonical_jsonl(path: Path) -> list[tuple[bytes, Json]]:
    loaded: list[tuple[bytes, Json]] = []
    for line_number, raw_line in enumerate(path.read_bytes().splitlines(), start=1):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            fail(f"{path.name}:{line_number} is not a JSON object")
        if raw_line != canonical_json(value).encode("utf-8"):
            fail(f"{path.name}:{line_number} is not canonical JSON")
        loaded.append((raw_line, value))
    return loaded


def _walk_hidden_reasoning_keys(value: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in HIDDEN_REASONING_KEYS:
                findings.append(child_path)
            findings.extend(_walk_hidden_reasoning_keys(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_walk_hidden_reasoning_keys(child, path=f"{path}[{index}]"))
    return findings


def _scan_text(value: str, *, api_key: str) -> list[str]:
    findings: list[str] = []
    if api_key and api_key in value:
        findings.append("exact study credential")
    findings.extend(name for name, pattern in CREDENTIAL_PATTERNS.items() if pattern.search(value))
    findings.extend(
        name for name, pattern in PROVIDER_RESPONSE_PATTERNS.items() if pattern.search(value)
    )
    if PROVIDER_ACCOUNT_PATTERN.search(value):
        findings.append("provider account identifier")
    if EMAIL_PATTERN.search(value):
        findings.append("email address")
    return findings


def validate_private_payload(value: Any, *, api_key: str, label: str) -> None:
    findings = _scan_text(canonical_json(value), api_key=api_key)
    if findings:
        fail(f"{label} contains privacy finding classes: {sorted(set(findings))}")
    if _walk_hidden_reasoning_keys(value):
        fail(f"{label} contains hidden-reasoning fields")


def validate_private_record(row: Json, *, api_key: str, label: str) -> None:
    validate_with_schema(row, RUN_SCHEMA, label)
    if row.get("provider_response_id") is not None:
        fail(f"{label} retains a provider response identifier")
    if row.get("system_fingerprint") is not None:
        fail(f"{label} retains a system fingerprint")
    validate_private_payload(row, api_key=api_key, label=label)
    for field in PRIVATE_TEXT_FIELDS:
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            fail(f"{label} has a non-text {field}")
    raw_text = row.get("raw_response_text")
    raw_digest = row.get("raw_response_sha256")
    if raw_text is None:
        if raw_digest is not None:
            fail(f"{label} has a response digest without response text")
    elif raw_digest != sha256_bytes(str(raw_text).encode("utf-8")):
        fail(f"{label} response digest differs from final response text")


def scoring_projection(row: Json) -> Json:
    projected = copy.deepcopy(row)
    for field in PRIVATE_TEXT_FIELDS:
        projected.pop(field, None)
    return projected


def derive_public_record(row: Json, *, api_key: str, label: str) -> tuple[Json, Json]:
    validate_private_record(row, api_key=api_key, label=label)
    derived = copy.deepcopy(row)
    redacted_fields = [field for field in PRIVATE_TEXT_FIELDS if row.get(field) is not None]
    for field in PRIVATE_TEXT_FIELDS:
        derived[field] = None
    validate_with_schema(derived, RUN_SCHEMA, f"public derivative {label}")
    if scoring_projection(row) != scoring_projection(derived):
        fail(f"{label} public transform changed a scoring field")
    return derived, {
        "item_id": row.get("item_id"),
        "lane_id": row.get("lane_id"),
        "private_text_fields_removed": redacted_fields,
        "scientific_fields_unchanged": True,
    }


def _file_map(root: Path, *, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def _transform_aggregate(aggregate: Json, lane_hashes: dict[str, str]) -> Json:
    derived = copy.deepcopy(aggregate)
    lanes = derived.get("lanes")
    if not isinstance(lanes, list):
        fail("aggregate lanes are malformed")
    seen: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            fail("aggregate lane is not an object")
        lane_id = str(lane.get("lane_id"))
        if lane_id not in lane_hashes or lane_id in seen:
            fail(f"aggregate contains an unexpected or duplicate lane: {lane_id}")
        seen.add(lane_id)
        lane["run_sha256"] = lane_hashes[lane_id]
    if seen != set(lane_hashes):
        fail("aggregate lane set differs from public lane records")
    return derived


def build_public_evidence(
    source_results: Path,
    plan_path: Path,
    aggregate_path: Path,
    out_root: Path,
    *,
    api_key: str,
) -> Json:
    source_results = source_results.resolve()
    plan_path = plan_path.resolve()
    aggregate_path = aggregate_path.resolve()
    out_root = out_root.resolve()
    if not api_key:
        fail("the study credential must be injected for exact-byte privacy scanning")
    if not source_results.is_dir():
        fail("source results directory does not exist")
    if out_root.exists():
        fail(f"refusing to overwrite public evidence: {out_root}")
    plan = load_json(plan_path)
    aggregate = load_json(aggregate_path)
    receipt = load_json(source_results / "execution-receipt.json")
    if not all(isinstance(value, dict) for value in (plan, aggregate, receipt)):
        fail("plan, aggregate, or execution receipt is malformed")
    validate_private_payload(aggregate, api_key=api_key, label="source aggregate")
    validate_private_payload(receipt, api_key=api_key, label="source execution receipt")
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("planned_cells") != 1260
        or receipt.get("durable_terminal_records") != 1260
        or receipt.get("application_posts_per_cell") != 1
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
    ):
        fail("execution receipt does not seal the complete zero-retry schedule")
    lane_order = plan.get("execution", {}).get("base_lane_order")
    if not isinstance(lane_order, list) or len(lane_order) != 7:
        fail("study plan does not declare seven ordered lanes")

    out_root.mkdir(parents=True)
    run_root = out_root / "runs"
    run_root.mkdir()
    row_map: list[Json] = []
    source_files: dict[str, str] = {}
    public_lane_files: dict[str, str] = {}
    lane_hashes: dict[str, str] = {}
    removed_field_count = 0
    for lane_id_value in lane_order:
        lane_id = str(lane_id_value)
        source = source_results / f"{lane_id}.jsonl"
        if not source.is_file():
            fail(f"source lane file is absent: {lane_id}")
        source_files[source.name] = sha256_file(source)
        loaded = load_canonical_jsonl(source)
        if len(loaded) != 180:
            fail(f"source lane does not contain 180 records: {lane_id}")
        output_rows: list[Json] = []
        item_ids: set[str] = set()
        for index, (raw_line, row) in enumerate(loaded):
            label = f"{lane_id}:{index + 1}"
            if row.get("lane_id") != lane_id:
                fail(f"{label} lane identity differs from its file")
            item_id = str(row.get("item_id"))
            if item_id in item_ids:
                fail(f"{label} duplicates item_id {item_id}")
            item_ids.add(item_id)
            derived, mapping = derive_public_record(row, api_key=api_key, label=label)
            derived_line = canonical_json(derived).encode("utf-8")
            mapping.update(
                {
                    "derived_row_sha256": sha256_bytes(derived_line),
                    "source_row_sha256": sha256_bytes(raw_line),
                }
            )
            removed_field_count += len(mapping["private_text_fields_removed"])
            row_map.append(mapping)
            output_rows.append(derived)
        target = run_root / source.name
        write_jsonl(target, output_rows)
        public_lane_files[lane_id] = target.relative_to(out_root).as_posix()
        lane_hashes[lane_id] = sha256_file(target)

    source_execution_receipt_hash = sha256_file(source_results / "execution-receipt.json")
    write_json(out_root / "execution-receipt.json", receipt)
    reported_aggregate = _transform_aggregate(aggregate, lane_hashes)
    write_json(out_root / "reported-aggregate.json", reported_aggregate)
    write_jsonl(out_root / "source-to-public-row-hashes.jsonl", row_map)

    for path in sorted(out_root.rglob("*")):
        if path.is_file():
            findings = _scan_text(path.read_text(encoding="utf-8"), api_key=api_key)
            if findings:
                fail(
                    f"public derivative {path.relative_to(out_root)} contains privacy "
                    f"finding classes: {sorted(set(findings))}"
                )

    derived_files = _file_map(out_root, exclude={"privacy-receipt.json"})
    public_receipt: Json = {
        "schema_version": "1.0.0",
        "status": "POST_EXECUTION_PUBLIC_SAFE_DERIVATIVE",
        "study_id": plan.get("study_id"),
        "source_aggregate_sha256": sha256_file(aggregate_path),
        "source_execution_receipt_sha256": source_execution_receipt_hash,
        "source_lane_files_sha256": source_files,
        "public_lane_files": public_lane_files,
        "public_lane_files_sha256": lane_hashes,
        "source_to_public_row_hashes": {
            "path": "source-to-public-row-hashes.jsonl",
            "rows": len(row_map),
            "sha256": sha256_file(out_root / "source-to-public-row-hashes.jsonl"),
        },
        "terminal_records_validated": len(row_map),
        "private_text_fields_removed": removed_field_count,
        "raw_final_response_text_included": False,
        "free_form_error_detail_included": False,
        "provider_response_identifiers_included": False,
        "system_fingerprints_included": False,
        "hidden_reasoning_fields_included": False,
        "credentials_included": False,
        "scientific_fields_unchanged": all(
            bool(mapping["scientific_fields_unchanged"]) for mapping in row_map
        ),
        "model_calls_performed": 0,
        "derived_files_sha256": derived_files,
    }
    public_receipt["privacy_receipt_sha256"] = sha256_bytes(
        canonical_json(public_receipt).encode("utf-8")
    )
    write_json(out_root / "privacy-receipt.json", public_receipt)
    return public_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-results", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_public_evidence(
        args.source_results,
        args.plan,
        args.aggregate,
        args.out,
        api_key=os.environ.get("OPENCODE_GO_API_KEY", ""),
    )
    print(
        canonical_json(
            {
                "privacy_receipt_sha256": receipt["privacy_receipt_sha256"],
                "status": receipt["status"],
                "terminal_records_validated": receipt["terminal_records_validated"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
