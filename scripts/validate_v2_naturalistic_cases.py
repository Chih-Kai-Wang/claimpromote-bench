#!/usr/bin/env python3
"""Validate curated v2 naturalistic cases against provenance and leakage boundaries."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "v2" / "schemas" / "naturalistic-case.schema.json"
CANDIDATES = ROOT / "v2" / "naturalistic-candidates.json"
DEFAULT_CASE_ROOT = ROOT / "v2" / "naturalistic-cases"

Json = dict[str, Any]
FORBIDDEN_MODEL_VIEW_KEYS = {
    "action",
    "decision",
    "gold",
    "gold_action",
    "label_rationale",
    "reason_codes",
    "score",
    "success",
}


def fail(message: str) -> None:
    raise SystemExit(f"v2-naturalistic-cases: {message}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path}: {exc}")


def object_at(path: Path, label: str) -> Json:
    value = load_json(path)
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def parse_time(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"{label} is not a valid RFC 3339 timestamp: {value}")
        raise AssertionError from exc


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_MODEL_VIEW_KEYS:
                findings.append(child_path)
            findings.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def candidate_map(candidate_pool: Json) -> dict[str, Json]:
    candidates = candidate_pool.get("candidates")
    if not isinstance(candidates, list):
        fail("naturalistic candidate pool lacks candidates")
    mapped: dict[str, Json] = {}
    for index, value in enumerate(candidates):
        if not isinstance(value, dict):
            fail(f"candidate {index} is not an object")
        candidate_id = value.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            fail(f"candidate {index} lacks candidate_id")
        if candidate_id in mapped:
            fail(f"duplicate candidate_id in pool: {candidate_id}")
        mapped[candidate_id] = value
    return mapped


def validate_case(
    case: Json,
    *,
    path: Path,
    validator: Draft202012Validator,
    candidates: dict[str, Json],
) -> Json:
    errors = sorted(
        validator.iter_errors(case),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        fail(f"{path}: schema violation at {location}: {first.message}")

    candidate_id = str(case["candidate_id"])
    candidate = candidates.get(candidate_id)
    if candidate is None:
        fail(f"{path}: candidate_id is not in the frozen candidate pool: {candidate_id}")

    source = case["source"]
    selection = case["selection"]
    expected_bindings = {
        "repository": candidate["source_repository"],
        "commit": candidate["source_commit"],
        "path": candidate["source_path"],
    }
    for key, expected in expected_bindings.items():
        if source.get(key) != expected:
            fail(f"{path}: source.{key} does not match frozen candidate {candidate_id}")
    if selection.get("sampling_rank_sha256") != candidate["sampling_rank_sha256"]:
        fail(f"{path}: sampling rank does not match frozen candidate {candidate_id}")

    stable_url = str(source["stable_url"])
    if str(source["commit"]) not in stable_url:
        fail(f"{path}: stable_url must contain the pinned source commit")

    model_visible = case["model_visible"]
    leakage = find_forbidden_keys(model_visible, "$.model_visible")
    if leakage:
        fail(f"{path}: evaluator-only/result keys leak into model-visible data: {leakage}")

    evaluation_time = parse_time(str(source["evaluation_time"]), f"{path}: source.evaluation_time")
    evidence_snapshot = model_visible["evidence_snapshot"]
    evidence_ids: set[str] = set()
    for index, evidence in enumerate(evidence_snapshot):
        evidence_id = str(evidence["evidence_id"])
        if evidence_id in evidence_ids:
            fail(f"{path}: duplicate evidence_id: {evidence_id}")
        evidence_ids.add(evidence_id)
        observed_at = parse_time(
            str(evidence["observed_at"]),
            f"{path}: evidence_snapshot[{index}].observed_at",
        )
        if observed_at > evaluation_time:
            fail(f"{path}: evidence {evidence_id} was observed after evaluation_time")

    release = case["release"]
    copied_evidence = any(bool(evidence["copied_source_bytes"]) for evidence in evidence_snapshot)
    if bool(release["copied_source_bytes"]) != copied_evidence:
        fail(f"{path}: release.copied_source_bytes disagrees with evidence pointers")
    if release["pointer_only"] and copied_evidence:
        fail(f"{path}: pointer-only case contains copied source bytes")
    if copied_evidence and source["license_review"] != "VERIFIED":
        fail(f"{path}: copied source bytes require verified licensing")

    label_status = str(case["label_status"])
    evaluator = case["evaluator_only"]
    if label_status == "LABELED" and not evaluator["source_checks"]:
        fail(f"{path}: labeled case requires at least one recorded source check")
    if label_status == "LABELED" and not evidence_snapshot:
        fail(f"{path}: labeled case requires an evidence snapshot")
    if label_status == "UNLABELED" and selection["inclusion_status"] == "INCLUDED":
        fail(f"{path}: unlabeled case cannot yet be INCLUDED")

    return {
        "case_id": case["case_id"],
        "candidate_id": candidate_id,
        "label_status": label_status,
        "inclusion_status": selection["inclusion_status"],
        "evidence_count": len(evidence_snapshot),
        "pointer_only": release["pointer_only"],
    }


def validate_root(
    case_root: Path,
    *,
    schema_path: Path = SCHEMA,
    candidate_path: Path = CANDIDATES,
    allow_empty: bool = False,
) -> Json:
    schema = object_at(schema_path, "naturalistic case schema")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    candidates = candidate_map(object_at(candidate_path, "naturalistic candidate pool"))

    files = sorted(case_root.glob("*.json")) if case_root.exists() else []
    if not files and not allow_empty:
        fail(f"no naturalistic case files found in {case_root}")

    case_ids: set[str] = set()
    candidate_ids: set[str] = set()
    records: list[Json] = []
    for path in files:
        case = object_at(path, str(path))
        record = validate_case(case, path=path, validator=validator, candidates=candidates)
        case_id = str(record["case_id"])
        candidate_id = str(record["candidate_id"])
        if case_id in case_ids:
            fail(f"duplicate case_id across files: {case_id}")
        if candidate_id in candidate_ids:
            fail(f"candidate curated more than once: {candidate_id}")
        case_ids.add(case_id)
        candidate_ids.add(candidate_id)
        records.append(record)

    counts = {
        status: sum(record["label_status"] == status for record in records)
        for status in ("UNLABELED", "LABELED", "EXCLUDED")
    }
    return {
        "status": "PASS",
        "case_root": str(case_root),
        "case_count": len(records),
        "label_status_counts": counts,
        "cases": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate_root(
        args.root.resolve(),
        schema_path=args.schema.resolve(),
        candidate_path=args.candidates.resolve(),
        allow_empty=args.allow_empty,
    )
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
